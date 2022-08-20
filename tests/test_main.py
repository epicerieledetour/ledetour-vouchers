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
def con_uri(tmpdir):
    return tmpdir / "db.sqlite3"


@fixture
def con(con_uri):
    return main.init_con(con_uri)


@fixture
def user_admin(con):
    values = main.new_user(
        con,
        main.UserBase(
            name="ADMIN",
            description="An admin user",
            ac_distribute=True,
            ac_cashin=True,
        ),
    )
    return main.User(**values)


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
def voucher_registered(con, user_admin, expiration_date):
    values = main.new_voucher(
        con,
        user_admin,
        main.VoucherBase(
            label=f"Voucher-registered",
            expiration_date=expiration_date,
            value=20,
            state=0,  # TODO: use an enum
        ),
    )
    return main.Voucher(**values)


@fixture
def voucher_distributed(con, user_admin, user_distributor, expiration_date):
    values = main.new_voucher(
        con,
        user_admin,
        main.VoucherBase(
            label=f"Voucher-distributed",
            expiration_date=expiration_date,
            value=20,
            state=0,  # TODO: use an enum
        ),
    )
    voucher = main.Voucher(**values)
    assert voucher.history
    patch = main.VoucherPatch(state=1)
    main.patch_voucher(con, user_distributor, voucher, patch)
    return main.Voucher(**main.get_voucher(con, voucher.id))


@fixture
def voucher_spent(con, user_admin, user_distributor, user_cashier, expiration_date):
    values = main.new_voucher(
        con,
        user_admin,
        main.VoucherBase(
            label=f"Voucher-spent",
            expiration_date=expiration_date,
            value=20,
            state=0,  # TODO: use an enum
        ),
    )
    voucher = main.Voucher(**values)
    patch = main.VoucherPatch(state=1)
    main.patch_voucher(con, user_distributor, voucher, patch)
    patch = main.VoucherPatch(state=2)
    main.patch_voucher(con, user_cashier, voucher, patch)
    return main.Voucher(**main.get_voucher(con, voucher.id))


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
    response = unauthenticated_client.get("/api/auth")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


def test_auth__get__invalid_bearer_token(unauthenticated_client):
    unauthenticated_client.auth = BearerAuth("invalid_token")
    response = unauthenticated_client.get("/api/auth")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


def test_auth__get__distributor(distributor_client, user_distributor):
    response = distributor_client.get("/api/auth")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "user": user_distributor.dict(),
        "voucher": None,
        "message_main": {"text": "Scan to distribute a voucher", "severity": 0},
        "message_detail": None,
        "next_actions": {
            "scan": {
                "url": "/api/vouchers/{code}",
                "verb": "PATCH",
                "body": {"state": 1},  # distributed
                "message": {"text": "Scan to distribute a voucher", "severity": 0},
            },
            "button": None,
        },
    }


def test_auth__get__cashier(cashier_client, user_cashier):
    response = cashier_client.get("/api/auth")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "user": user_cashier.dict(),
        "voucher": None,
        "message_main": {"text": "Scan to cash a voucher in", "severity": 0},
        "message_detail": None,
        "next_actions": {
            "scan": {
                "url": "/api/vouchers/{code}",
                "verb": "PATCH",
                "body": {"state": 2},  # distributed
                "message": {"text": "Scan to cash a voucher in", "severity": 0},
            },
            "button": None,
        },
    }


def test_vouchers__patch__unauthenticated(unauthenticated_client, voucher_registered):
    response = unauthenticated_client.patch(
        f"/api/vouchers/{voucher_registered.id}", data={"state": 0}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


def test_vouchers__patch__invalid_bearer_token(
    unauthenticated_client, voucher_registered
):
    unauthenticated_client.auth = BearerAuth("invalid_token")
    response = unauthenticated_client.patch(
        f"/api/vouchers/{voucher_registered.id}", data={"state": 0}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


# Distributor tests


def test_vouchers_patch__distributor__registered_to_distributed(
    con_uri, distributor_client, user_distributor, voucher_registered
):
    response = distributor_client.patch(
        f"/api/vouchers/{voucher_registered.id}", json={"state": 1}
    )

    con = main.init_con(con_uri)
    voucher = main.Voucher(**main.get_voucher(con, voucher_registered.id))

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
                "url": "/api/vouchers/{code}",
                "verb": "PATCH",
                "body": {"state": 1},  # distributed
                "message": {"text": "Scan to distribute a voucher", "severity": 0},
            },
            "button": {
                "url": f"/api/vouchers/{voucher_registered.id}",
                "verb": "PATCH",
                "body": {"state": 0},
                "message": {"text": "Cancel distribution", "severity": 2},
            },
        },
    }


def test_vouchers_patch__distributor__distributed_to_registered(
    con_uri, distributor_client, user_distributor, voucher_distributed
):
    response = distributor_client.patch(
        f"/api/vouchers/{voucher_distributed.id}", json={"state": 0}
    )

    con = main.init_con(con_uri)
    voucher = main.Voucher(**main.get_voucher(con, voucher_distributed.id))

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
                "url": "/api/vouchers/{code}",
                "verb": "PATCH",
                "body": {"state": 1},  # distributed
                "message": {"text": "Scan to distribute a voucher", "severity": 0},
            },
            "button": {
                "url": f"/api/vouchers/{voucher_distributed.id}",
                "verb": "PATCH",
                "body": {"state": 1},
                "message": {"text": "Distribute", "severity": 1},
            },
        },
    }


def test_vouchers_patch__distributor__distributed_to_distributed(
    con_uri, distributor_client, user_distributor, voucher_distributed
):
    response = distributor_client.patch(
        f"/api/vouchers/{voucher_distributed.id}", json={"state": 1}
    )
    voucher = voucher_distributed.dict()

    con = main.init_con(con_uri)
    dist_date = main._last_history_date(con, voucher_distributed.id)

    assert response.status_code == status.HTTP_200_OK
    j = response.json()
    expected_action_response = main.ActionResponse(**j)
    assert expected_action_response.dict() == {
        "user": user_distributor.dict(),
        "voucher": voucher,
        "message_main": {"text": "Already distributed", "severity": 2},
        "message_detail": {"text": f"Distributed by DIST {dist_date}", "severity": 0},
        "next_actions": {
            "scan": {
                "url": "/api/vouchers/{code}",
                "verb": "PATCH",
                "body": {"state": 1},  # distributed
                "message": {"text": "Scan to distribute a voucher", "severity": 0},
            },
            "button": {
                "url": f"/api/vouchers/{voucher_distributed.id}",
                "verb": "PATCH",
                "body": {"state": 0},
                "message": {"text": "Cancel distribution", "severity": 2},
            },
        },
    }


def test_vouchers_patch__distributor__spent_to_distributed(
    con_uri, distributor_client, user_distributor, voucher_spent
):
    response = distributor_client.patch(
        f"/api/vouchers/{voucher_spent.id}", json={"state": 1}
    )
    voucher = voucher_spent.dict()
    # voucher["state"] = 1

    con = main.init_con(con_uri)
    spent_date = main._last_history_date(con, voucher_spent.id)

    assert response.status_code == status.HTTP_200_OK
    j = response.json()
    expected_action_response = main.ActionResponse(**j)
    assert expected_action_response.dict() == {
        "user": user_distributor.dict(),
        "voucher": voucher,
        "message_main": {"text": "Already spent", "severity": 2},
        "message_detail": {"text": f"Cashed-in by POS {spent_date}", "severity": 0},
        "next_actions": {
            "scan": {
                "url": "/api/vouchers/{code}",
                "verb": "PATCH",
                "body": {"state": 1},  # distributed
                "message": {"text": "Scan to distribute a voucher", "severity": 0},
            },
            "button": None,
        },
    }


# Cashier tests


def test_vouchers_patch__cashier__registered_to_cashedin(
    con_uri, cashier_client, user_cashier, voucher_registered
):
    response = cashier_client.patch(
        f"/api/vouchers/{voucher_registered.id}", json={"state": 2}
    )

    con = main.init_con(con_uri)
    voucher = main.Voucher(**main.get_voucher(con, voucher_registered.id))

    assert response.status_code == status.HTTP_200_OK
    j = response.json()
    expected_action_response = main.ActionResponse(**j)
    assert expected_action_response.dict() == {
        "user": user_cashier.dict(),
        "voucher": voucher,
        "message_main": {"text": "Not yet distributed", "severity": 2},
        "message_detail": None,
        "next_actions": {
            "scan": {
                "url": "/api/vouchers/{code}",
                "verb": "PATCH",
                "body": {"state": 2},  # distributed
                "message": {"text": "Scan to cash a voucher in", "severity": 0},
            },
            "button": None,
        },
    }


def test_vouchers_patch__cashier__distributed_to_cashedin(
    con_uri, cashier_client, user_cashier, voucher_distributed
):
    response = cashier_client.patch(
        f"/api/vouchers/{voucher_distributed.id}", json={"state": 2}
    )

    con = main.init_con(con_uri)
    voucher = main.Voucher(**main.get_voucher(con, voucher_distributed.id))

    assert response.status_code == status.HTTP_200_OK
    j = response.json()
    expected_action_response = main.ActionResponse(**j)
    assert expected_action_response.dict() == {
        "user": user_cashier.dict(),
        "voucher": voucher,
        "message_main": {"text": "Cashed-in", "severity": 1},
        "message_detail": None,
        "next_actions": {
            "scan": {
                "url": "/api/vouchers/{code}",
                "verb": "PATCH",
                "body": {"state": 2},
                "message": {"text": "Scan to cash a voucher in", "severity": 0},
            },
            "button": {
                "url": f"/api/vouchers/{voucher_distributed.id}",
                "verb": "PATCH",
                "body": {"state": 1},
                "message": {"text": "Cancel cashing-in", "severity": 2},
            },
        },
    }


def test_vouchers_patch__cashier__cashedin_to_distributed(
    con_uri, cashier_client, user_cashier, voucher_spent
):
    response = cashier_client.patch(
        f"/api/vouchers/{voucher_spent.id}", json={"state": 1}
    )

    con = main.init_con(con_uri)
    voucher = main.Voucher(**main.get_voucher(con, voucher_spent.id))

    assert response.status_code == status.HTTP_200_OK
    j = response.json()
    expected_action_response = main.ActionResponse(**j)
    assert expected_action_response.dict() == {
        "user": user_cashier.dict(),
        "voucher": voucher,
        "message_main": {"text": "Cashed-in cancelled", "severity": 2},
        "message_detail": None,
        "next_actions": {
            "scan": {
                "url": "/api/vouchers/{code}",
                "verb": "PATCH",
                "body": {"state": 2},
                "message": {"text": "Scan to cash a voucher in", "severity": 0},
            },
            "button": {
                "url": f"/api/vouchers/{voucher_spent.id}",
                "verb": "PATCH",
                "body": {"state": 2},
                "message": {"text": "Cash-in", "severity": 1},
            },
        },
    }


def test_vouchers_patch__cashier__cashedin_to_cashedin(
    con_uri, cashier_client, user_cashier, voucher_spent
):
    response = cashier_client.patch(
        f"/api/vouchers/{voucher_spent.id}", json={"state": 2}
    )

    con = main.init_con(con_uri)
    voucher = main.Voucher(**main.get_voucher(con, voucher_spent.id))
    spent_date = main._last_history_date(con, voucher_spent.id)

    assert response.status_code == status.HTTP_200_OK
    j = response.json()
    expected_action_response = main.ActionResponse(**j)
    assert expected_action_response.dict() == {
        "user": user_cashier.dict(),
        "voucher": voucher,
        "message_main": {"text": "Already cashed-in", "severity": 2},
        "message_detail": {"text": f"Cashed-in by POS {spent_date}", "severity": 0},
        "next_actions": {
            "scan": {
                "url": "/api/vouchers/{code}",
                "verb": "PATCH",
                "body": {"state": 2},
                "message": {"text": "Scan to cash a voucher in", "severity": 0},
            },
            "button": {
                "url": f"/api/vouchers/{voucher_spent.id}",
                "verb": "PATCH",
                "body": {"state": 1},
                "message": {"text": "Cancel cashing-in", "severity": 2},
            },
        },
    }


# Other tests


def test_vouchers__history(voucher_spent):
    assert voucher_spent.history[0].startswith("Cashed-in by POS ")
    assert voucher_spent.history[1].startswith("Cashed-in by DIST ")
    assert voucher_spent.history[2].startswith("Cashed-in by ADMIN ")


def test_start(unauthenticated_client):
    response = unauthenticated_client.get("/api/start")
    assert response.status_code == status.HTTP_200_OK
    expected_action_response = main.ActionResponse(**response.json())
    assert expected_action_response.dict() == {
        "user": None,
        "voucher": None,
        "message_main": {"text": "Scan an authentification barcode", "severity": 0},
        "message_detail": None,
        "next_actions": {
            "scan": {
                "url": "/api/auth/{code}",
                "verb": "GET",
                "body": None,
                "message": None,
            },
            "button": None,
        },
    }


def test_auth__from_id__unknown_user_id(unauthenticated_client):
    response = unauthenticated_client.get("/api/auth/unknown_user_id")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Invalid user"}


def test_auth__from_id__distributor(unauthenticated_client, user_distributor):
    response = unauthenticated_client.get("/api/auth/{}".format(user_distributor.id))
    assert response.status_code == status.HTTP_200_OK
    expected_action_response = main.ActionResponse(**response.json())
    assert expected_action_response.dict() == {
        "user": user_distributor.dict(),
        "voucher": None,
        "message_main": {"text": "Scan to distribute a voucher", "severity": 0},
        "message_detail": None,
        "next_actions": {
            "scan": {
                "url": "/api/vouchers/{code}",
                "verb": "PATCH",
                "body": {"state": 1},
                "message": {"text": "Scan to distribute a voucher", "severity": 0},
            },
            "button": None,
        },
    }


def test_auth__from_id__cashier(unauthenticated_client, user_cashier):
    response = unauthenticated_client.get("/api/auth/{}".format(user_cashier.id))
    assert response.status_code == status.HTTP_200_OK
    expected_action_response = main.ActionResponse(**response.json())
    assert expected_action_response.dict() == {
        "user": user_cashier.dict(),
        "voucher": None,
        "message_main": {"text": "Scan to cash a voucher in", "severity": 0},
        "message_detail": None,
        "next_actions": {
            "scan": {
                "url": "/api/vouchers/{code}",
                "verb": "PATCH",
                "body": {"state": 2},
                "message": {"text": "Scan to cash a voucher in", "severity": 0},
            },
            "button": None,
        },
    }
