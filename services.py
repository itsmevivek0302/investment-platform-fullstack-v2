"""Money & trading logic. All balance changes go through here, inside one DB transaction,
with row locks (SELECT ... FOR UPDATE on PostgreSQL) so concurrent requests can't overspend."""
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import MAX_TXN_AMOUNT
from .models import Holding, Order, Product, Transaction, Wallet

ZERO = Decimal("0")
CENT = Decimal("0.01")
UNIT = Decimal("0.0001")


def q2(v: Decimal) -> Decimal:
    return Decimal(v).quantize(CENT, rounding=ROUND_HALF_UP)


def q4(v: Decimal) -> Decimal:
    return Decimal(v).quantize(UNIT, rounding=ROUND_HALF_UP)


def dec(v) -> Decimal:
    return Decimal(str(v)) if v is not None else ZERO


def locked_wallet(db: Session, user_id: int) -> Wallet:
    w = db.execute(select(Wallet).where(Wallet.user_id == user_id).with_for_update()).scalar_one_or_none()
    if w is None:
        w = Wallet(user_id=user_id, balance=ZERO)
        db.add(w)
        db.flush()
    return w


def add_ledger(db: Session, user_id: int, type_: str, amount: Decimal, balance_after: Decimal,
               order_id: int | None = None) -> Transaction:
    t = Transaction(user_id=user_id, type=type_, amount=amount, balance_after=balance_after,
                    reference=uuid4().hex, order_id=order_id)
    db.add(t)
    return t


def _check_limit(amount: Decimal) -> None:
    if amount > MAX_TXN_AMOUNT:
        raise HTTPException(400, f"Amount exceeds the per-transaction limit of {MAX_TXN_AMOUNT}")


def deposit(db: Session, user_id: int, amount: Decimal) -> tuple[Decimal, str]:
    amount = q2(amount)
    _check_limit(amount)
    w = locked_wallet(db, user_id)
    w.balance = q2(dec(w.balance) + amount)
    t = add_ledger(db, user_id, "deposit", amount, w.balance)
    db.commit()
    return dec(w.balance), t.reference


def withdraw(db: Session, user_id: int, amount: Decimal) -> tuple[Decimal, str]:
    amount = q2(amount)
    _check_limit(amount)
    w = locked_wallet(db, user_id)
    if dec(w.balance) < amount:
        raise HTTPException(400, "Insufficient balance")
    w.balance = q2(dec(w.balance) - amount)
    t = add_ledger(db, user_id, "withdrawal", amount, w.balance)
    db.commit()
    return dec(w.balance), t.reference


def place_order(db: Session, user_id: int, product_id: int, side: str, quantity: Decimal) -> tuple[Order, Decimal]:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    if side == "buy" and not product.active:
        raise HTTPException(400, "Product is not available for buying")

    price = dec(product.price)
    quantity = q4(quantity)
    amount = q2(price * quantity)
    if amount <= ZERO:
        raise HTTPException(400, "Order value is too small")
    _check_limit(amount)

    wallet = locked_wallet(db, user_id)
    holding = db.execute(
        select(Holding).where(Holding.user_id == user_id, Holding.product_id == product_id).with_for_update()
    ).scalar_one_or_none()

    realized = ZERO
    if side == "buy":
        if dec(wallet.balance) < amount:
            raise HTTPException(400, "Insufficient wallet balance")
        wallet.balance = q2(dec(wallet.balance) - amount)
        if holding is None:
            holding = Holding(user_id=user_id, product_id=product_id, quantity=ZERO, avg_price=ZERO)
            db.add(holding)
        old_qty = dec(holding.quantity)
        new_qty = old_qty + quantity
        holding.avg_price = q4((old_qty * dec(holding.avg_price) + quantity * price) / new_qty)
        holding.quantity = new_qty
    else:
        if holding is None or dec(holding.quantity) < quantity:
            raise HTTPException(400, "Insufficient holding")
        realized = q2((price - dec(holding.avg_price)) * quantity)
        holding.quantity = dec(holding.quantity) - quantity
        if holding.quantity == ZERO:
            holding.avg_price = ZERO
        wallet.balance = q2(dec(wallet.balance) + amount)

    order = Order(user_id=user_id, product_id=product_id, side=side, quantity=quantity,
                  price=price, amount=amount, realized_pnl=realized, status="filled")
    db.add(order)
    try:
        db.flush()
        add_ledger(db, user_id, side, amount, wallet.balance, order_id=order.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Concurrent update detected, please retry")
    return order, dec(wallet.balance)
