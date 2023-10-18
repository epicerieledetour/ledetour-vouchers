import itertools
import pprint

els = {
    "action_url": [
        # "unknown",  # 404
        "scan",
        "undo",
    ],
    "auth_header": [
        "none",
        # "malformed",  # 400 bad request
        "unknown_user_token",
        "valid_user_token",
    ],
    "url_token": [
        # "none",  # 404
        # "malformed", # Not sure what that would mean
        "unknown",
        "valid_user",
        "valid_voucher",
    ],
    "voucher_expired": [
        "no",
        "yes",
    ],
    "user_can_cashin": [
        "no",
        "yes",
    ],
    "voucher_cashedin": [
        "no",
        "by_current_user",
        "by_another_user",
    ],
    "voucher_undo_timeout_expired": [
        "no",
        "yes",
    ],
}

combs = list(itertools.product(*els.values()))

pprint.pprint(combs)
print(len(combs))
