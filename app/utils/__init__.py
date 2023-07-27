import shortuuid

from .legacy import *


def makeid(prefix: str) -> str:
    return f"{prefix}_{shortuuid.uuid()}"
