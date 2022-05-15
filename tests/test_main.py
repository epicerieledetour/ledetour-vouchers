import datetime

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
def expiration_date():
    return datetime.datetime.utcnow() + datetime.timedelta(days=1)


@fixture
def con(tmpdir):
    return main.init_con(tmpdir / "db.sqlite3")


@fixture
def user_distributor(con):
    values = main.new_user(
        con,
        main.UserBase(
            name="DIST",
            description="A distributor user",
            ac_distribute=True,
            ac_cashin=False,
        ),
    )
    return main.User(**values)


@fixture
def user_cashier(con):
    values = main.new_user(
        con,
        main.UserBase(
            name="POS",
            description="A cashier user",
            ac_distribute=False,
            ac_cashin=True,
        ),
    )
    return main.User(**values)


@fixture
def voucher_registered(con, expiration_date):
    values = main.new_voucher(
        con,
        main.VoucherBase(
            label=f"Voucher-registered",
            expiration_date=expiration_date,
            value=20,
            state=0,  # TODO: use an enum
        ),
    )
    return main.Voucher(**values)


@fixture
def voucher_distributed(con, expiration_date):
    values = main.new_voucher(
        con,
        main.VoucherBase(
            label=f"Voucher-distributed",
            expiration_date=expiration_date,
            value=20,
            state=1,  # TODO: use an enum
        ),
    )
    return main.Voucher(**values)


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


def test_auth__get__unauthenticated(unauthenticated_client):
    response = unauthenticated_client.get("/auth")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


def test_auth__get__invalid_bearer_token(unauthenticated_client):
    unauthenticated_client.auth = BearerAuth("invalid_token")
    response = unauthenticated_client.get("/auth")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


def test_auth__get__distributor(distributor_client, user_distributor):
    response = distributor_client.get("/auth")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "user": user_distributor.dict(),
        "voucher": None,
        "message_main": None,
        "message_detail": None,
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


def test_auth__get__cashier(cashier_client, user_cashier):
    response = cashier_client.get("/auth")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "user": user_cashier.dict(),
        "voucher": None,
        "message_main": None,
        "message_detail": None,
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


def test_vouchers__patch__unauthenticated(unauthenticated_client, voucher_registered):
    response = unauthenticated_client.patch(
        f"/vouchers/{voucher_registered.id}", data={"state": 0}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


def test_vouchers__patch__invalid_bearer_token(
    unauthenticated_client, voucher_registered
):
    unauthenticated_client.auth = BearerAuth("invalid_token")
    response = unauthenticated_client.patch(
        f"/vouchers/{voucher_registered.id}", data={"state": 0}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


def test_vouchers_patch__distributor__registered_to_distributed(
    distributor_client, user_distributor, voucher_registered
):
    response = distributor_client.patch(
        f"/vouchers/{voucher_registered.id}", json={"state": 1}
    )
    voucher = voucher_registered.dict()
    voucher["state"] = 1

    assert response.status_code == status.HTTP_200_OK
    j = response.json()
    expected_action_response = main.ActionResponse(**j)
    assert expected_action_response.dict() == {
        "user": user_distributor.dict(),
        "voucher": voucher,
        "message_main": {"text": "Distributed", "severity": 1},
        "message_detail": None,
        "next_actions": {
            "scan": {
                "url": "/vouchers/{voucherid}",
                "verb": "PATCH",
                "body": {"state": 1},  # distributed
                "message": {"text": "Scan to distribute a voucher", "severity": 0},
            },
            "button": {
                "url": f"/vouchers/{voucher_registered.id}",
                "verb": "PATCH",
                "body": {"state": 0},
                "message": {"text": "Cancel distribution", "severity": 2},
            },
        },
    }


def test_vouchers_patch__distributor__distributed_to_registered(
    distributor_client, user_distributor, voucher_distributed
):
    response = distributor_client.patch(
        f"/vouchers/{voucher_distributed.id}", json={"state": 0}
    )
    voucher = voucher_distributed.dict()
    voucher["state"] = 0

    assert response.status_code == status.HTTP_200_OK
    j = response.json()
    expected_action_response = main.ActionResponse(**j)
    assert expected_action_response.dict() == {
        "user": user_distributor.dict(),
        "voucher": voucher,
        "message_main": {"text": "Distribution cancelled", "severity": 2},
        "message_detail": None,
        "next_actions": {
            "scan": {
                "url": "/vouchers/{voucherid}",
                "verb": "PATCH",
                "body": {"state": 1},  # distributed
                "message": {"text": "Scan to distribute a voucher", "severity": 0},
            },
            "button": {
                "url": f"/vouchers/{voucher_distributed.id}",
                "verb": "PATCH",
                "body": {"state": 1},
                "message": {"text": "Distribute", "severity": 1},
            },
        },
    }


def test_vouchers_patch__distributor__distributed_to_distributed(
    distributor_client, user_distributor, voucher_distributed
):
    response = distributor_client.patch(
        f"/vouchers/{voucher_distributed.id}", json={"state": 1}
    )
    voucher = voucher_distributed.dict()
    # voucher["state"] = 1

    assert response.status_code == status.HTTP_200_OK
    j = response.json()
    expected_action_response = main.ActionResponse(**j)
    assert expected_action_response.dict() == {
        "user": user_distributor.dict(),
        "voucher": voucher,
        "message_main": {"text": "Already distributed", "severity": 2},
        "message_detail": None,
        "next_actions": {
            "scan": {
                "url": "/vouchers/{voucherid}",
                "verb": "PATCH",
                "body": {"state": 1},  # distributed
                "message": {"text": "Scan to distribute a voucher", "severity": 0},
            },
            "button": {
                "url": f"/vouchers/{voucher_distributed.id}",
                "verb": "PATCH",
                "body": {"state": 0},
                "message": {"text": "Cancel distribution", "severity": 2},
            },
        },
    }
