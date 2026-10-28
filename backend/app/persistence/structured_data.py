"""Lossless relational representation of nested persistence values."""

from typing import Protocol


class DataNode(Protocol):
    field: str
    path: str
    kind: str
    text_value: str | None
    bool_value: bool | None


def encode(value: object, field: str, path: str = "") -> list[dict[str, object]]:
    row: dict[str, object] = {"field": field, "path": path, "kind": "null"}
    children: list[dict[str, object]] = []
    if isinstance(value, dict):
        row["kind"] = "object"
        for key, item in value.items():
            escaped = key.replace("~", "~0").replace("/", "~1")
            children.extend(encode(item, field, path + "/" + escaped))
    elif isinstance(value, list):
        row["kind"] = "array"
        for index, item in enumerate(value):
            children.extend(encode(item, field, path + "/" + str(index)))
    elif isinstance(value, bool):
        row.update(kind="boolean", bool_value=value)
    elif isinstance(value, int):
        row.update(kind="integer", text_value=str(value))
    elif isinstance(value, float):
        row.update(kind="float", text_value=repr(value))
    elif isinstance(value, str):
        row.update(kind="string", text_value=value)
    elif value is not None:
        raise TypeError(f"Unsupported value: {type(value).__name__}")
    return [row, *children]


def decode(rows: list[DataNode], field: str) -> object:
    values = {row.path: row for row in rows if row.field == field}

    def visit(path: str) -> object:
        row = values[path]
        if row.kind in ("object", "array"):
            prefix = path + "/"
            children = [
                (p[len(prefix) :], p)
                for p in values
                if p.startswith(prefix) and "/" not in p[len(prefix) :]
            ]
            if row.kind == "array":
                return [
                    visit(p) for _, p in sorted(children, key=lambda pair: int(pair[0]))
                ]
            return {
                key.replace("~1", "/").replace("~0", "~"): visit(p)
                for key, p in children
            }
        if row.kind == "null":
            return None
        if row.kind == "boolean":
            return row.bool_value
        if row.kind == "integer":
            assert row.text_value is not None
            return int(row.text_value)
        if row.kind == "float":
            assert row.text_value is not None
            return float(row.text_value)
        return row.text_value

    return visit("")
