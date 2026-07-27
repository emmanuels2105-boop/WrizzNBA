from dataclasses import dataclass


@dataclass(frozen=True)
class PropType:
    name: str
    stat_column: str


# Only POINTS is implemented in v1. Adding a new prop type is a matter of
# registering it here plus a matching row in the prop_types table (db/schema.py)
# -- the box score already stores rebounds/assists/etc. for free.
PROP_TYPES: dict[str, PropType] = {
    "POINTS": PropType(name="POINTS", stat_column="points"),
}


def get_prop_type(name: str) -> PropType:
    try:
        return PROP_TYPES[name]
    except KeyError:
        raise ValueError(f"Unknown prop type: {name!r}. Known: {sorted(PROP_TYPES)}") from None
