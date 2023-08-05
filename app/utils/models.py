from collections.abc import Iterable
from sqlite3 import Connection

from pydantic import BaseModel

import app.events.models

from app.utils.sql import _KeysAsAttrsDict  # TODO: make _KeyAsAttrDict public


def build_crud(
    BaseModel: type[BaseModel],
    EntityModel: type[BaseModel],
    id_prefix: str,
    sqls: _KeysAsAttrsDict,
):
    def create(
        conn: Connection, entities: Iterable[BaseModel]
    ) -> Iterable[EntityModel]:
        def events():
            for entity, entityid in zip(entities, ids):
                # Creation event

                # TODO: rename elemid to entityid
                yield app.events.models.CreateEvent(elemid=entityid)

                # Attribute setting events

                data = entity.dict()
                data["deleted"] = False

                for field, value in data.items():
                    yield app.events.models.UpdateEvent(
                        elemid=entityid, field=field, value=value
                    )

        ids = [app.utils.makeid(id_prefix) for _ in entities]

        app.events.models.append_events(conn, events())
        return read(conn, ids)

    def read(conn: Connection, ids: Iterable[str] | None = None) -> BaseModel:
        # TODO: perf, lot of buffering and traversals here
        ids, ids_string = _make_ids_string_usable_in_where_id_in_clause(ids)
        query = sqls.read.format(ids_string=ids_string) if ids_string else sqls.list
        res = conn.execute(query)
        entities = tuple(EntityModel(**entity_data) for entity_data in res)

        diff_ids = set(ids) - {entity.id for entity in entities}

        if diff_ids:
            raise ValueError(f"Trying to fetch unknown ids: {', '.join(diff_ids)}")

        return entities

    def update(conn: Connection, updated_entities: Iterable[EntityModel]) -> None:
        def events():
            diff_dicts = tuple(
                _diff_models(current, updated)
                for (current, updated) in zip(current_entities, updated_entities)
            )

            for entityid, diff_dict in zip(ids, diff_dicts):
                for field, value in diff_dict.items():
                    if value is not None:
                        yield app.events.models.UpdateEvent(
                            elemid=entityid, field=field, value=value
                        )

        updated_entities = tuple(updated_entities)

        ids = tuple(entity.id for entity in updated_entities)

        with conn:
            current_entities = read(conn, ids)
            events = tuple(events())
            app.events.models.append_events(conn, events)

    def delete(conn: Connection, entities: Iterable[EntityModel]) -> None:
        # TODO: pass ids, not EntityModel
        users = (entity.copy(update={"deleted": "1"}) for entity in entities)
        update(conn, users)

    def history(
        conn: Connection, ids: Iterable[str] | None = None
    ) -> Iterable[app.events.models.Event]:
        ids, ids_string = _make_ids_string_usable_in_where_id_in_clause(ids)
        query = app.events.models._SQLS.history.format(ids_string=ids_string)
        res = conn.execute(query)

        return (app.events.models.Event(**event) for event in res)

    return create, read, update, delete, history


def _make_ids_string_usable_in_where_id_in_clause(
    ids: Iterable[str] | None,
) -> tuple[tuple[str], str | None]:
    if not ids:
        return tuple(), None

    ids_tuple = tuple(ids)

    if not ids_tuple:
        return tuple(), None

    id_strings = (f"'{id_str}'" for id_str in ids_tuple)

    return ids_tuple, ", ".join(id_strings)


def _diff_models(base: BaseModel, updated: BaseModel) -> dict:
    base = base.dict()
    updated = updated.dict()
    return {k: updated[k] for k in base if k in updated and base[k] != updated[k]}
