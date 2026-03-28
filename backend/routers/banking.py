from datetime import datetime, timedelta
import base64
import json
import os
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Account, Transaction

router = APIRouter(prefix="/banking")

TRUELAYER_CLIENT_ID = os.getenv("TRUELAYER_CLIENT_ID")
TRUELAYER_CLIENT_SECRET = os.getenv("TRUELAYER_CLIENT_SECRET")
TRUELAYER_REDIRECT_URI = os.getenv("TRUELAYER_REDIRECT_URI")
TRUELAYER_AUTH_URL = os.getenv("TRUELAYER_AUTH_URL")
TRUELAYER_API_URL = os.getenv("TRUELAYER_API_URL")


@router.get("/connect")
async def banking_connect(current_user=Depends(get_current_user)):
    if not all([TRUELAYER_CLIENT_ID, TRUELAYER_REDIRECT_URI, TRUELAYER_AUTH_URL]):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="TrueLayer configuration missing")

    state = base64.urlsafe_b64encode(json.dumps({"user_id": current_user.id}).encode()).decode()
    params = {
        "response_type": "code",
        "client_id": TRUELAYER_CLIENT_ID,
        "scope": "accounts transactions",
        "redirect_uri": TRUELAYER_REDIRECT_URI,
        "providers": "mock",
        "state": state,
    }
    auth_url = f"{TRUELAYER_AUTH_URL}/?{urlencode(params)}"
    return {"auth_url": auth_url}


@router.get("/callback")
async def banking_callback(code: str = Query(...), state: str | None = None, db: Session = Depends(get_db)):
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing code")

    print(f"Callback received code: {code[:10]}...")

    if not all([TRUELAYER_CLIENT_ID, TRUELAYER_CLIENT_SECRET, TRUELAYER_REDIRECT_URI, TRUELAYER_AUTH_URL, TRUELAYER_API_URL]):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="TrueLayer configuration missing")

    token_url = f"{TRUELAYER_AUTH_URL}/connect/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": TRUELAYER_CLIENT_ID,
        "client_secret": TRUELAYER_CLIENT_SECRET,
        "redirect_uri": TRUELAYER_REDIRECT_URI,
        "code": code,
    }

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(token_url, data=payload, timeout=30)
        print(f"Token response status: {token_resp.status_code}")
        print(f"Token response body: {token_resp.text}")
        if token_resp.status_code == 401:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized token exchange")
        if token_resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to exchange token")

        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in")
        if not access_token or not expires_in:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token response")

        accounts_resp = await client.get(
            f"{TRUELAYER_API_URL}/data/v1/accounts",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )
        print(f"Accounts response status: {accounts_resp.status_code}")
        print(f"Accounts response body: {accounts_resp.text}")
        if accounts_resp.status_code == 401:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized fetching accounts")
        if accounts_resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch accounts")

        accounts = accounts_resp.json().get("results", [])

    token_expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))

    if state:
        try:
            state_data = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
            user_id = state_data.get("user_id", 1)
        except Exception:
            user_id = 1
    else:
        user_id = 1

    for item in accounts:
        account_id = item.get("account_id")
        if not account_id:
            continue

        existing = db.query(Account).filter(Account.truelayer_account_id == account_id).first()
        if existing:
            existing.display_name = item.get("display_name", existing.display_name)
            existing.currency = item.get("currency", existing.currency)
            existing.account_type = item.get("account_type", existing.account_type)
            existing.access_token = access_token
            existing.token_expires_at = token_expires_at
        else:
            db.add(
                Account(
                    user_id=user_id,
                    truelayer_account_id=account_id,
                    display_name=item.get("display_name"),
                    currency=item.get("currency"),
                    account_type=item.get("account_type"),
                    access_token=access_token,
                    token_expires_at=token_expires_at,
                )
            )

    db.commit()
    print(f"Saved {len(accounts)} accounts for user_id {user_id}")
    return RedirectResponse(url="http://localhost:5173/dashboard?connected=true", status_code=status.HTTP_302_FOUND)


@router.get("/accounts")
async def banking_accounts(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    print(f"current_user.id = {current_user.id}")
    print(f"current_user.email = {current_user.email}")
    all_accounts = db.query(Account).all()
    print(f"All accounts in DB: {[(a.id, a.user_id, a.display_name) for a in all_accounts]}")
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
async def banking_sync(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not TRUELAYER_API_URL:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="TrueLayer API URL not configured")

    now = datetime.utcnow()
    total_new = 0
    warnings = []

    accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    async with httpx.AsyncClient() as client:
        for acct in accounts:
            if acct.token_expires_at and acct.token_expires_at < now:
                warnings.append(f"Token expired for account {acct.id}")
                continue
            if not acct.access_token:
                warnings.append(f"No access token for account {acct.id}")
                continue

            tx_resp = await client.get(
                f"{TRUELAYER_API_URL}/data/v1/accounts/{acct.truelayer_account_id}/transactions",
                headers={"Authorization": f"Bearer {acct.access_token}"},
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
async def banking_disconnect(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    for acct in accounts:
        db.delete(acct)
    db.commit()
    return {"disconnected": True}