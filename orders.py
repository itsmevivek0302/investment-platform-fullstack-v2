from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import services
from ..auth import current_user
from ..database import get_db
from ..models import Order, Product, User
from ..schemas import OrderIn, OrderOut, OrderResult

router = APIRouter(prefix="/orders", tags=["orders"])


def to_out(o: Order, p: Product) -> OrderOut:
    return OrderOut(id=o.id, product_id=o.product_id, symbol=p.symbol, name=p.name, side=o.side,
                    quantity=o.quantity, price=o.price, amount=o.amount, realized_pnl=o.realized_pnl,
                    status=o.status, created_at=o.created_at)


@router.post("", response_model=OrderResult)
def create_order(x: OrderIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    o, balance = services.place_order(db, u.id, x.product_id, x.side, x.quantity)
    return OrderResult(order_id=o.id, status=o.status, side=o.side, quantity=o.quantity, price=o.price,
                       amount=o.amount, realized_pnl=o.realized_pnl, balance=balance)


@router.get("", response_model=list[OrderOut])
def list_orders(side: Optional[Literal["buy", "sell"]] = None, product_id: Optional[int] = None,
                limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                u: User = Depends(current_user), db: Session = Depends(get_db)):
    stmt = select(Order, Product).join(Product, Product.id == Order.product_id).where(Order.user_id == u.id)
    if side:
        stmt = stmt.where(Order.side == side)
    if product_id:
        stmt = stmt.where(Order.product_id == product_id)
    rows = db.execute(stmt.order_by(Order.id.desc()).limit(limit).offset(offset)).all()
    return [to_out(o, p) for o, p in rows]


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.execute(select(Order, Product).join(Product, Product.id == Order.product_id)
                     .where(Order.id == order_id, Order.user_id == u.id)).first()
    if not row:
        raise HTTPException(404, "Order not found")
    return to_out(*row)
