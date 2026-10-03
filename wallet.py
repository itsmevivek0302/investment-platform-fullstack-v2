from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import services
from ..auth import current_user
from ..database import get_db
from ..models import Transaction, User
from ..schemas import MoneyIn, TransactionOut, WalletOut, WalletTxnOut

router = APIRouter(tags=["wallet"])


@router.get("/wallet", response_model=WalletOut)
def wallet(u: User = Depends(current_user), db: Session = Depends(get_db)):
    w = services.locked_wallet(db, u.id)
    db.commit()
    return WalletOut(balance=w.balance)


@router.post("/wallet/deposit", response_model=WalletTxnOut)
def deposit(x: MoneyIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    balance, ref = services.deposit(db, u.id, x.amount)
    return WalletTxnOut(balance=balance, reference=ref)


@router.post("/wallet/withdraw", response_model=WalletTxnOut)
def withdraw(x: MoneyIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    balance, ref = services.withdraw(db, u.id, x.amount)
    return WalletTxnOut(balance=balance, reference=ref)


@router.get("/transactions", response_model=list[TransactionOut])
def transactions(type: Optional[str] = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                 u: User = Depends(current_user), db: Session = Depends(get_db)):
    stmt = select(Transaction).where(Transaction.user_id == u.id)
    if type:
        stmt = stmt.where(Transaction.type == type.lower())
    return db.scalars(stmt.order_by(Transaction.id.desc()).limit(limit).offset(offset)).all()
