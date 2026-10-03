from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import services
from ..services import ZERO, dec, q2
from ..auth import current_user
from ..database import get_db
from ..models import Holding, Product, User
from ..schemas import HoldingOut, PortfolioOut

router = APIRouter(tags=["portfolio"])


def _pct(pnl: Decimal, invested: Decimal) -> Decimal:
    return q2(pnl / invested * 100) if invested > ZERO else ZERO


@router.get("/portfolio", response_model=PortfolioOut)
def portfolio(u: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Holding, Product).join(Product, Product.id == Holding.product_id)
                      .where(Holding.user_id == u.id, Holding.quantity > 0).order_by(Product.symbol)).all()
    items, total_value, total_invested = [], ZERO, ZERO
    for h, p in rows:
        qty, price, avg = dec(h.quantity), dec(p.price), dec(h.avg_price)
        value, invested = q2(qty * price), q2(qty * avg)
        pnl = value - invested
        total_value += value
        total_invested += invested
        items.append(HoldingOut(product_id=p.id, symbol=p.symbol, name=p.name, quantity=qty, avg_price=avg,
                                price=price, value=value, invested=invested, pnl=pnl, pnl_pct=_pct(pnl, invested)))
    wallet = services.locked_wallet(db, u.id)
    db.commit()
    total_pnl = total_value - total_invested
    return PortfolioOut(total_value=total_value, total_invested=total_invested, total_pnl=total_pnl,
                        total_pnl_pct=_pct(total_pnl, total_invested), wallet_balance=dec(wallet.balance),
                        holdings=items)
