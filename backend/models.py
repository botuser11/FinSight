from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    accounts = relationship('Account', back_populates='user')

class Account(Base):
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    truelayer_account_id = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=True)
    currency = Column(String, default='GBP', nullable=False)
    account_type = Column(String, nullable=True)
    access_token = Column(String, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='accounts')
    transactions = relationship('Transaction', back_populates='account')

class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    color_hex = Column(String, nullable=False)
    is_default = Column(Boolean, default=True, nullable=False)

    transactions = relationship('Transaction', back_populates='category')

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    truelayer_tx_id = Column(String, unique=True, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    description = Column(String, nullable=True)
    merchant_name = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    categorisation_source = Column(String, nullable=True)
    is_anomaly = Column(Boolean, default=False, nullable=False)
    anomaly_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship('Account', back_populates='transactions')
    category = relationship('Category', back_populates='transactions')
