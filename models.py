from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, ForeignKey, Boolean, Text,
    UniqueConstraint, CheckConstraint, Index,
)
from sqlalchemy.sql import func
from .database import Base

MONEY = Numeric(18, 2)   # wallet balances, order amounts, ledger
PRICE = Numeric(18, 4)   # unit prices / average cost
QTY = Numeric(18, 4)     # units held


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(160), nullable=False)
    category = Column(String(80), nullable=False, index=True)
    symbol = Column(String(40), unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    price = Column(PRICE, nullable=False)
    risk = Column(String(30), default="moderate", nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PriceHistory(Base):
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    price = Column(PRICE, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (CheckConstraint("balance >= 0", name="ck_wallet_non_negative"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    balance = Column(MONEY, default=Decimal("0"), nullable=False)


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_holding_user_product"),
        CheckConstraint("quantity >= 0", name="ck_holding_non_negative"),
    )
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(QTY, default=Decimal("0"), nullable=False)
    avg_price = Column(PRICE, default=Decimal("0"), nullable=False)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (Index("ix_orders_user_created", "user_id", "created_at"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    side = Column(String(10), nullable=False)  # buy | sell
    quantity = Column(QTY, nullable=False)
    price = Column(PRICE, nullable=False)
    amount = Column(MONEY, nullable=False)
    realized_pnl = Column(MONEY, default=Decimal("0"), nullable=False)
    status = Column(String(30), default="filled", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(30), nullable=False)  # deposit | withdrawal | buy | sell
    amount = Column(MONEY, nullable=False)
    balance_after = Column(MONEY, nullable=False)
    status = Column(String(30), default="completed", nullable=False)
    reference = Column(String(80), unique=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
