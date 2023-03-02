import random
import string

import shortuuid

def new_voucher_id_string(index: int):
    stamp = random.choices(string.ascii_uppercase, k=5)
    stamp = "".join(stamp)
    return f"{index:04d}-{stamp}"


def new_user_id_string(*_, **__):
    return shortuuid.uuid()

