from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import PriceHistory, Product
from ..schemas import PricePointOut, ProductOut

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def list_products(category: Optional[str] = None, risk: Optional[str] = None,
                  q: Optional[str] = Query(None, max_length=60), db: Session = Depends(get_db)):
    stmt = select(Product).where(Product.active.is_(True))
    if category:
        stmt = stmt.where(Product.category == category)
    if risk:
        stmt = stmt.where(Product.risk == risk.lower())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Product.name.ilike(like), Product.symbol.ilike(like)))
    return db.scalars(stmt.order_by(Product.id)).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p or not p.active:
        raise HTTPException(404, "Product not found")
    return p


@router.get("/{product_id}/history", response_model=list[PricePointOut])
def price_history(product_id: int, limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)):
    if not db.get(Product, product_id):
        raise HTTPException(404, "Product not found")
    rows = db.scalars(select(PriceHistory).where(PriceHistory.product_id == product_id)
                      .order_by(PriceHistory.id.desc()).limit(limit)).all()
    return list(reversed(rows))
