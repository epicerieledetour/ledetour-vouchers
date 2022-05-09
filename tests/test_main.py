from fastapi import status
from fastapi.testclient import TestClient
from requests.auth import AuthBase

from pytest import fixture

from app import main


class BearerAuth(AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, req):
        req.headers["authorization"] = "Bearer " + self.token
        return req


@fixture
def con():
    c = main.init_con(":memory:")
    main.new_user(
        c,
        main.UserBase(
            name="DIST",
            description="A distributor user",
            ac_distribute=True,
            ac_cashin=False,
        ),
    )
    main.new_user(
        c,
        main.UserBase(
            name="POS",
            description="A cashier user",
            ac_distribute=False,
            ac_cashin=True,
        ),
    )
    return c


@fixture
def users(con):
    cur = con.cursor()
    cur.execute("SELECT * FROM users")
    return tuple(main.User(**row) for row in cur.fetchall())


@fixture
def user_distributor(users):
    return users[0]


@fixture
def user_cashier(users):
    return users[1]


@fixture
def app(con):
    def get_con():
        try:
            yield con
        finally:
            con.close()

    main.app.dependency_overrides[main.get_con] = get_con
    yield main.app
    del main.app.dependency_overrides[main.get_con]


@fixture
def unauthenticated_client(app):
    return TestClient(app)


@fixture
def distributor_client(app, user_distributor):
    client = TestClient(app)
    client.auth = BearerAuth(user_distributor.id)
    return client


@fixture
def cashier_client(app, user_cashier):
    client = TestClient(app)
    client.auth = BearerAuth(user_cashier.id)
    return client


def test_auth__unauthenticated(unauthenticated_client):
    response = unauthenticated_client.get("/auth")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


def test_auth__invalid_bearer_token(unauthenticated_client):
    unauthenticated_client.auth = BearerAuth("invalid_token")
    response = unauthenticated_client.get("/auth")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


def test_auth__distributor(distributor_client, user_distributor):
    response = distributor_client.get("/auth")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "user": user_distributor.dict(),
        "next_actions": {
            "scan": {
                "url": "/vouchers/{voucherid}",
                "verb": "PATCH",
                "body": {"state": 1},  # distributed
                "message": {"text": "Scan to distribute a voucher", "severity": 0},
            },
            "button": None,
        },
    }


def test_auth__cashier(cashier_client, user_cashier):
    response = cashier_client.get("/auth")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "user": user_cashier.dict(),
        "next_actions": {
            "scan": {
                "url": "/vouchers/{voucherid}",
                "verb": "PATCH",
                "body": {"state": 2},  # distributed
                "message": {"text": "Scan to cash a voucher in", "severity": 0},
            },
            "button": None,
        },
    }
