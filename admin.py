from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import admin_user
from ..database import get_db
from ..models import Holding, Order, PriceHistory, Product, Transaction, User, Wallet
from ..schemas import (AdminOrderOut, AdminStatsOut, AdminTransactionOut, AdminUserOut, AdminUserUpdate,
                       ProductIn, ProductOut, ProductUpdate)
from ..services import ZERO, dec, q2
from .orders import to_out

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------- products ----------
@router.get("/products", response_model=list[ProductOut])
def all_products(admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    return db.scalars(select(Product).order_by(Product.id)).all()


@router.post("/products", response_model=ProductOut, status_code=201)
def add_product(x: ProductIn, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    if db.scalar(select(Product).where(Product.symbol == x.symbol)):
        raise HTTPException(409, "Symbol already exists")
    p = Product(**x.model_dump())
    db.add(p)
    try:
        db.flush()
        db.add(PriceHistory(product_id=p.id, price=p.price))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Symbol already exists")
    db.refresh(p)
    return p


@router.patch("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, x: ProductUpdate, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    data = x.model_dump(exclude_unset=True)
    new_price = data.pop("price", None)
    for k, v in data.items():
        setattr(p, k, v)
    if new_price is not None and dec(new_price) != dec(p.price):
        p.price = new_price
        db.add(PriceHistory(product_id=p.id, price=new_price))
    db.commit()
    db.refresh(p)
    return p


# ---------- users ----------
@router.get("/users", response_model=list[AdminUserOut])
def list_users(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
               admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    rows = db.execute(select(User, Wallet.balance).outerjoin(Wallet, Wallet.user_id == User.id)
                      .order_by(User.id).limit(limit).offset(offset)).all()
    return [AdminUserOut(id=u.id, name=u.name, email=u.email, role=u.role, is_active=u.is_active,
                         created_at=u.created_at, balance=dec(b)) for u, b in rows]


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(user_id: int, x: AdminUserUpdate, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == admin.id and (x.is_active is False or x.role == "user"):
        raise HTTPException(400, "You cannot disable or demote your own account")
    if x.is_active is not None:
        u.is_active = x.is_active
    if x.role is not None:
        u.role = x.role
    db.commit()
    db.refresh(u)
    w = db.scalar(select(Wallet).where(Wallet.user_id == u.id))
    return AdminUserOut(id=u.id, name=u.name, email=u.email, role=u.role, is_active=u.is_active,
                        created_at=u.created_at, balance=dec(w.balance if w else 0))


# ---------- platform-wide data ----------
@router.get("/orders", response_model=list[AdminOrderOut])
def all_orders(user_id: Optional[int] = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
               admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    stmt = select(Order, Product).join(Product, Product.id == Order.product_id)
    if user_id:
        stmt = stmt.where(Order.user_id == user_id)
    rows = db.execute(stmt.order_by(Order.id.desc()).limit(limit).offset(offset)).all()
    return [AdminOrderOut(**to_out(o, p).model_dump(), user_id=o.user_id) for o, p in rows]


@router.get("/transactions", response_model=list[AdminTransactionOut])
def all_transactions(user_id: Optional[int] = None, type: Optional[str] = None,
                     limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                     admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    stmt = select(Transaction)
    if user_id:
        stmt = stmt.where(Transaction.user_id == user_id)
    if type:
        stmt = stmt.where(Transaction.type == type.lower())
    return db.scalars(stmt.order_by(Transaction.id.desc()).limit(limit).offset(offset)).all()


@router.get("/stats", response_model=AdminStatsOut)
def stats(admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    def total(*conds):
        return dec(db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0)).where(*conds)))

    holdings_value = db.scalar(
        select(func.coalesce(func.sum(Holding.quantity * Product.price), 0))
        .select_from(Holding).join(Product, Product.id == Holding.product_id))
    return AdminStatsOut(
        users=db.scalar(select(func.count(User.id))),
        products=db.scalar(select(func.count(Product.id))),
        orders=db.scalar(select(func.count(Order.id))),
        transaction_volume=total(),
        total_deposits=total(Transaction.type == "deposit"),
        total_withdrawals=total(Transaction.type == "withdrawal"),
        total_wallet_balance=dec(db.scalar(select(func.coalesce(func.sum(Wallet.balance), 0)))),
        total_holdings_value=q2(dec(holdings_value)),
    )
