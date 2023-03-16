def parse_name(name: str) -> str:
    assert isinstance(name, str)
    return name.lower().strip()


def is_positive(id: int) -> int:
    assert id >= 0
    return id
