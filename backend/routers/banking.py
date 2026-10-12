from datetime import datetime, timedelta
import logging
import os
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from auth import forbid_demo, get_current_user, is_demo_user
from config import ALGORITHM, FRONTEND_URL, SECRET_KEY
from database import get_db
from models import Account, Transaction, User
from token_crypto import TokenEncryptionNotConfigured, decrypt_token, encrypt_token

logger = logging.getLogger("finsight.banking")

router = APIRouter(prefix="/banking")

TRUELAYER_CLIENT_ID = os.getenv("TRUELAYER_CLIENT_ID")
TRUELAYER_CLIENT_SECRET = os.getenv("TRUELAYER_CLIENT_SECRET")
TRUELAYER_REDIRECT_URI = os.getenv("TRUELAYER_REDIRECT_URI")
TRUELAYER_AUTH_URL = os.getenv("TRUELAYER_AUTH_URL")
TRUELAYER_API_URL = os.getenv("TRUELAYER_API_URL")
# "mock" = TrueLayer sandbox mock bank; e.g. "uk-ob-all uk-oauth-all" for real banks
TRUELAYER_PROVIDERS = os.getenv("TRUELAYER_PROVIDERS", "mock")

STATE_PURPOSE = "truelayer_connect"
STATE_TTL_MINUTES = 10
# Refresh a little before expiry so a token doesn't die mid-sync
TOKEN_EXPIRY_MARGIN = timedelta(seconds=60)


def _create_state(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=STATE_TTL_MINUTES)
    return jwt.encode({"sub": str(user_id), "purpose": STATE_PURPOSE, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def _user_id_from_state(state: str | None) -> int | None:
    if not state:
        return None
    try:
        payload = jwt.decode(state, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    if payload.get("purpose") != STATE_PURPOSE:
        return None
    try:
        return int(payload.get("sub"))
    except (TypeError, ValueError):
        return None


def _frontend_redirect(connected: bool) -> RedirectResponse:
    query = "connected=true" if connected else "error=true"
    return RedirectResponse(url=f"{FRONTEND_URL}/dashboard?{query}", status_code=status.HTTP_302_FOUND)


async def _request_token(client: httpx.AsyncClient, grant: dict) -> dict | None:
    resp = await client.post(
        f"{TRUELAYER_AUTH_URL}/connect/token",
        data={"client_id": TRUELAYER_CLIENT_ID, "client_secret": TRUELAYER_CLIENT_SECRET, **grant},
        timeout=30,
    )
    if resp.status_code != 200:
        logger.warning("TrueLayer token request (%s) failed with status %s", grant.get("grant_type"), resp.status_code)
        return None
    data = resp.json()
    if not data.get("access_token") or not data.get("expires_in"):
        logger.warning("TrueLayer token response missing access_token/expires_in")
        return None
    return data


@router.get("/connect")
async def banking_connect(current_user=Depends(forbid_demo)):
    if not all([TRUELAYER_CLIENT_ID, TRUELAYER_REDIRECT_URI, TRUELAYER_AUTH_URL]):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="TrueLayer configuration missing")

    params = {
        "response_type": "code",
        "client_id": TRUELAYER_CLIENT_ID,
        "scope": "accounts transactions offline_access",
        "redirect_uri": TRUELAYER_REDIRECT_URI,
        "providers": TRUELAYER_PROVIDERS,
        "state": _create_state(current_user.id),
    }
    auth_url = f"{TRUELAYER_AUTH_URL}/?{urlencode(params)}"
    return {"auth_url": auth_url}


@router.get("/callback")
async def banking_callback(
    code: str | None = Query(None),
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    user_id = _user_id_from_state(state)
    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    if user is None or is_demo_user(user):
        logger.warning("Bank connect callback rejected: missing or invalid state")
        return _frontend_redirect(False)
    if error or not code:
        logger.info("Bank connect cancelled or failed at provider for user %s", user.id)
        return _frontend_redirect(False)

    if not all([TRUELAYER_CLIENT_ID, TRUELAYER_CLIENT_SECRET, TRUELAYER_REDIRECT_URI, TRUELAYER_AUTH_URL, TRUELAYER_API_URL]):
        logger.error("TrueLayer configuration missing")
        return _frontend_redirect(False)

    async with httpx.AsyncClient() as client:
        token_data = await _request_token(
            client,
            {"grant_type": "authorization_code", "redirect_uri": TRUELAYER_REDIRECT_URI, "code": code},
        )
        if token_data is None:
            return _frontend_redirect(False)
        access_token = token_data["access_token"]

        accounts_resp = await client.get(
            f"{TRUELAYER_API_URL}/data/v1/accounts",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )
        if accounts_resp.status_code != 200:
            logger.warning("TrueLayer accounts request failed with status %s", accounts_resp.status_code)
            return _frontend_redirect(False)
        accounts = accounts_resp.json().get("results", [])

    try:
        enc_access = encrypt_token(access_token)
        enc_refresh = encrypt_token(token_data.get("refresh_token"))
    except TokenEncryptionNotConfigured:
        logger.error("TOKEN_ENCRYPTION_KEY is not set; cannot store bank tokens")
        return _frontend_redirect(False)
    token_expires_at = datetime.utcnow() + timedelta(seconds=int(token_data["expires_in"]))

    saved = 0
    for item in accounts:
        account_id = item.get("account_id")
        if not account_id:
            continue

        existing = db.query(Account).filter(Account.truelayer_account_id == account_id).first()
        if existing and existing.user_id != user.id:
            logger.warning("Skipping account already linked to another user")
            continue
        if existing:
            existing.display_name = item.get("display_name", existing.display_name)
            existing.currency = item.get("currency", existing.currency)
            existing.account_type = item.get("account_type", existing.account_type)
            existing.access_token = enc_access
            existing.refresh_token = enc_refresh
            existing.token_expires_at = token_expires_at
        else:
            db.add(
                Account(
                    user_id=user.id,
                    truelayer_account_id=account_id,
                    display_name=item.get("display_name"),
                    currency=item.get("currency"),
                    account_type=item.get("account_type"),
                    access_token=enc_access,
                    refresh_token=enc_refresh,
                    token_expires_at=token_expires_at,
                )
            )
        saved += 1

    db.commit()
    logger.info("Saved %s bank accounts for user %s", saved, user.id)
    return _frontend_redirect(True)


@router.get("/accounts")
async def banking_accounts(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    return [
        {
            "id": a.id,
            "display_name": a.display_name,
            "currency": a.currency,
            "account_type": a.account_type,
            "last_synced_at": a.last_synced_at,
        }
        for a in accounts
    ]


@router.post("/sync")
async def banking_sync(current_user=Depends(forbid_demo), db: Session = Depends(get_db)):
    if not all([TRUELAYER_CLIENT_ID, TRUELAYER_CLIENT_SECRET, TRUELAYER_AUTH_URL, TRUELAYER_API_URL]):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="TrueLayer configuration missing")

    now = datetime.utcnow()
    total_new = 0
    warnings = []
    # Accounts from one bank connection share a refresh token, and TrueLayer
    # rotates it on use, so refresh once per connection and reuse the result.
    refreshed: dict[str, dict | None] = {}

    accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    async with httpx.AsyncClient() as client:
        for acct in accounts:
            try:
                access_token = decrypt_token(acct.access_token)
                refresh_token = decrypt_token(acct.refresh_token)
            except TokenEncryptionNotConfigured:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Bank token encryption is not configured",
                )

            if not access_token:
                warnings.append(f"No valid access token for account {acct.id}; reconnect your bank")
                continue

            if acct.token_expires_at and acct.token_expires_at - TOKEN_EXPIRY_MARGIN < now:
                if not refresh_token:
                    warnings.append(f"Token expired for account {acct.id}; reconnect your bank")
                    continue
                if refresh_token not in refreshed:
                    refreshed[refresh_token] = await _request_token(
                        client, {"grant_type": "refresh_token", "refresh_token": refresh_token}
                    )
                new_tokens = refreshed[refresh_token]
                if new_tokens is None:
                    warnings.append(f"Could not refresh access for account {acct.id}; reconnect your bank")
                    continue
                access_token = new_tokens["access_token"]
                acct.access_token = encrypt_token(access_token)
                acct.refresh_token = encrypt_token(new_tokens.get("refresh_token") or refresh_token)
                acct.token_expires_at = now + timedelta(seconds=int(new_tokens["expires_in"]))
                db.commit()

            tx_resp = await client.get(
                f"{TRUELAYER_API_URL}/data/v1/accounts/{acct.truelayer_account_id}/transactions",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30,
            )
            if tx_resp.status_code == 401:
                warnings.append(f"Unauthorized for account {acct.id}")
                continue
            if tx_resp.status_code != 200:
                warnings.append(f"Failed to fetch transactions for account {acct.id}")
                continue

            tx_list = tx_resp.json().get("results", [])
            for tx in tx_list:
                tx_id = tx.get("transaction_id")
                if not tx_id:
                    continue
                if db.query(Transaction).filter(Transaction.truelayer_tx_id == tx_id).first():
                    continue

                amount = float(tx.get("amount", 0))
                if (tx.get("direction") or "").lower() == "debit":
                    amount = -abs(amount)

                description = tx.get("description", "")
                merchant_name = tx.get("merchant_name") or (description.split(" - ")[0].strip() if description else None)

                timestamp_str = tx.get("timestamp")
                try:
                    timestamp_val = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")) if timestamp_str else now
                except Exception:
                    timestamp_val = now

                db.add(
                    Transaction(
                        account_id=acct.id,
                        truelayer_tx_id=tx_id,
                        amount=amount,
                        currency=tx.get("currency"),
                        description=description,
                        merchant_name=merchant_name,
                        timestamp=timestamp_val,
                        categorisation_source="pending",
                        is_anomaly=False,
                    )
                )
                total_new += 1

            acct.last_synced_at = now
            db.commit()

    return {"synced": total_new, "warnings": warnings}


@router.delete("/disconnect")
async def banking_disconnect(current_user=Depends(forbid_demo), db: Session = Depends(get_db)):
    # Transactions can't exist without an account (account_id is NOT NULL and
    # they'd belong to no user), so delete them with their accounts in one commit.
    account_ids = [a.id for a in db.query(Account.id).filter(Account.user_id == current_user.id).all()]
    transactions_removed = 0
    if account_ids:
        transactions_removed = (
            db.query(Transaction)
            .filter(Transaction.account_id.in_(account_ids))
            .delete(synchronize_session=False)
        )
        db.query(Account).filter(Account.id.in_(account_ids)).delete(synchronize_session=False)
    db.commit()
    return {
        "disconnected": True,
        "accounts_removed": len(account_ids),
        "transactions_removed": transactions_removed,
    }
