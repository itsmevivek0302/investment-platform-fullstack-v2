from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, PlainSerializer, field_validator

# Decimals are stored exactly, but sent to clients as plain JSON numbers.
Num = Annotated[Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")]
Amount = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
Quantity = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=4)]
UnitPrice = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=4)]
Risk = Literal["low", "moderate", "high"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth / users ----------
def _strong(p: str) -> str:
    if not any(c.isalpha() for c in p) or not any(c.isdigit() for c in p):
        raise ValueError("Password must contain at least one letter and one number")
    return p


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _strong(v)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=64)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(max_length=64)
    new_password: str = Field(min_length=8, max_length=64)

    @field_validator("new_password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _strong(v)


class ProfileUpdateIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class UserOut(ORM):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- products ----------
class ProductIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    category: str = Field(min_length=2, max_length=80)
    symbol: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9._-]+$")
    price: UnitPrice
    risk: Risk = "moderate"
    description: str = ""

    @field_validator("symbol")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=160)
    category: Optional[str] = Field(default=None, min_length=2, max_length=80)
    price: Optional[UnitPrice] = None
    risk: Optional[Risk] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class ProductOut(ORM):
    id: int
    name: str
    category: str
    symbol: str
    price: Num
    risk: str
    description: Optional[str] = ""
    active: bool


class PricePointOut(ORM):
    price: Num
    created_at: Optional[datetime] = None


# ---------- wallet / ledger ----------
class MoneyIn(BaseModel):
    amount: Amount


class WalletOut(BaseModel):
    balance: Num


class WalletTxnOut(BaseModel):
    balance: Num
    reference: str


class TransactionOut(ORM):
    id: int
    type: str
    amount: Num
    balance_after: Num
    status: str
    reference: str
    order_id: Optional[int] = None
    created_at: Optional[datetime] = None


# ---------- orders / portfolio ----------
class OrderIn(BaseModel):
    product_id: int
    side: Literal["buy", "sell"]
    quantity: Quantity

    @field_validator("side", mode="before")
    @classmethod
    def _lower(cls, v):
        return v.lower() if isinstance(v, str) else v


class OrderResult(BaseModel):
    order_id: int
    status: str
    side: str
    quantity: Num
    price: Num
    amount: Num
    realized_pnl: Num
    balance: Num


class OrderOut(BaseModel):
    id: int
    product_id: int
    symbol: str
    name: str
    side: str
    quantity: Num
    price: Num
    amount: Num
    realized_pnl: Num
    status: str
    created_at: Optional[datetime] = None


class HoldingOut(BaseModel):
    product_id: int
    symbol: str
    name: str
    quantity: Num
    avg_price: Num
    price: Num
    value: Num
    invested: Num
    pnl: Num
    pnl_pct: Num


class PortfolioOut(BaseModel):
    total_value: Num
    total_invested: Num
    total_pnl: Num
    total_pnl_pct: Num
    wallet_balance: Num
    holdings: list[HoldingOut]


# ---------- admin ----------
class AdminUserOut(UserOut):
    balance: Num = Decimal("0")


class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[Literal["user", "admin"]] = None


class AdminOrderOut(OrderOut):
    user_id: int


class AdminTransactionOut(TransactionOut):
    user_id: int


class AdminStatsOut(BaseModel):
    users: int
    products: int
    orders: int
    transaction_volume: Num
    total_deposits: Num
    total_withdrawals: Num
    total_wallet_balance: Num
    total_holdings_value: Num
