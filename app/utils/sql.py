import pathlib
import sqlite3

from types import ModuleType
from typing import Any, Dict, Tuple


def get_connection(path: pathlib.Path) -> sqlite3.Connection:
    return sqlite3.connect(path)


class _KeysAsAttrsDict(dict):
    def __init__(self, *args: Tuple[Any], **kwargs: Dict[str, Any]) -> None:
        super().__init__(self, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"{type(self)} has no attribute {name!r}")


def get_module_queries(module: ModuleType) -> _KeysAsAttrsDict:
    ret = _KeysAsAttrsDict()

    sqldir = pathlib.Path(module.__file__).parent / "sql"

    try:
        for path in sqldir.iterdir():
            ret[path.stem] = path.read_text()
    except FileNotFoundError:
        pass

    return ret
