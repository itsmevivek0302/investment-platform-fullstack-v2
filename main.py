import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS, JWT_SECRET
from .routers import admin, auth, orders, portfolio, products, wallet
from .seed import init_db

log = logging.getLogger("investment")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if JWT_SECRET in ("change-me", "change-this-to-a-long-random-secret") or len(JWT_SECRET) < 32:
        log.warning("JWT_SECRET is weak/default - set a long random value before any real deployment!")
    init_db()
    yield


app = FastAPI(title="Investment Platform API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


for r in (auth.router, products.router, wallet.router, orders.router, portfolio.router, admin.router):
    app.include_router(r)
