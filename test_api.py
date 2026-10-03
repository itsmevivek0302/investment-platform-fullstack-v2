from .conftest import auth


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_login_me(client):
    body = {"name": "Ravi", "email": "Ravi@Example.com", "password": "Passw0rd123"}
    assert client.post("/auth/register", json=body).status_code == 201
    assert client.post("/auth/register", json=body).status_code == 409
    r = client.post("/auth/login", json={"email": "ravi@example.com", "password": "Passw0rd123"})
    assert r.status_code == 200
    me = client.get("/me", headers=auth(r.json()["access_token"])).json()
    assert me["email"] == "ravi@example.com" and me["role"] == "user"
    bad = client.post("/auth/login", json={"email": "ravi@example.com", "password": "wrong-pass1"})
    assert bad.status_code == 401


def test_weak_password_rejected(client):
    r = client.post("/auth/register", json={"name": "X Y", "email": "weak@example.com", "password": "abcdefgh"})
    assert r.status_code == 422


def test_requires_auth(client):
    assert client.get("/wallet").status_code in (401, 403)


def test_wallet_deposit_withdraw(client, user_token):
    h = auth(user_token)
    assert client.get("/wallet", headers=h).json()["balance"] == 0
    assert client.post("/wallet/deposit", json={"amount": 500.25}, headers=h).json()["balance"] == 500.25
    assert client.post("/wallet/withdraw", json={"amount": 100}, headers=h).json()["balance"] == 400.25
    assert client.post("/wallet/withdraw", json={"amount": 9999}, headers=h).status_code == 400
    assert client.post("/wallet/deposit", json={"amount": -5}, headers=h).status_code == 422
    txns = client.get("/transactions", headers=h).json()
    assert [t["type"] for t in txns] == ["withdrawal", "deposit"]
    assert txns[0]["balance_after"] == 400.25


def test_buy_sell_and_pnl(client, user_token, admin_token):
    h, ah = auth(user_token), auth(admin_token)
    client.post("/wallet/deposit", json={"amount": 1000}, headers=h)
    pid = client.get("/products").json()[0]["id"]  # price 100

    r = client.post("/orders", json={"product_id": pid, "side": "buy", "quantity": 2.5}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["amount"] == 250 and r.json()["balance"] == 750

    assert client.post("/orders", json={"product_id": pid, "side": "buy", "quantity": 100}, headers=h).status_code == 400
    assert client.post("/orders", json={"product_id": pid, "side": "sell", "quantity": 5}, headers=h).status_code == 400

    # admin raises the price -> unrealised profit
    assert client.patch(f"/admin/products/{pid}", json={"price": 120}, headers=ah).status_code == 200
    pf = client.get("/portfolio", headers=h).json()
    assert pf["total_value"] == 300 and pf["total_invested"] == 250 and pf["total_pnl"] == 50
    assert pf["holdings"][0]["pnl_pct"] == 20

    s = client.post("/orders", json={"product_id": pid, "side": "sell", "quantity": 1}, headers=h).json()
    assert s["realized_pnl"] == 20 and s["balance"] == 870
    assert len(client.get("/orders", headers=h).json()) == 2
    assert len(client.get(f"/products/{pid}/history").json()) >= 2
    client.patch(f"/admin/products/{pid}", json={"price": 100}, headers=ah)


def test_admin_protection(client, user_token, admin_token):
    h = auth(user_token)
    assert client.get("/admin/stats", headers=h).status_code == 403
    assert client.post("/admin/products", headers=h, json={}).status_code in (403, 422)
    stats = client.get("/admin/stats", headers=auth(admin_token)).json()
    assert stats["users"] >= 2 and stats["products"] >= 3


def test_admin_product_and_user_management(client, admin_token):
    ah = auth(admin_token)
    new = {"name": "Gold ETF", "category": "ETF", "symbol": "gold", "price": 55.5, "risk": "moderate"}
    r = client.post("/admin/products", json=new, headers=ah)
    assert r.status_code == 201 and r.json()["symbol"] == "GOLD"
    assert client.post("/admin/products", json=new, headers=ah).status_code == 409
    pid = r.json()["id"]
    client.patch(f"/admin/products/{pid}", json={"active": False}, headers=ah)
    assert all(p["symbol"] != "GOLD" for p in client.get("/products").json())

    users = client.get("/admin/users", headers=ah).json()
    me_id = next(u["id"] for u in users if u["email"] == "admin@example.com")
    assert client.patch(f"/admin/users/{me_id}", json={"is_active": False}, headers=ah).status_code == 400


def test_disabled_user_blocked(client, admin_token):
    ah = auth(admin_token)
    email = "block@example.com"
    t = client.post("/auth/register", json={"name": "Block Me", "email": email, "password": "Passw0rd123"}).json()
    uid = t["user"]["id"]
    client.patch(f"/admin/users/{uid}", json={"is_active": False}, headers=ah)
    assert client.get("/me", headers=auth(t["access_token"])).status_code == 403
    assert client.post("/auth/login", json={"email": email, "password": "Passw0rd123"}).status_code == 403
