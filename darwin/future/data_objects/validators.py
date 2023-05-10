def parse_name(name: str) -> str:
    """
    A function to parse and validate a name

    Parameters
    ----------
    name : str
        The name to be parsed and validated

    Returns
    -------
    str
        The parsed and validated name
    """
    assert isinstance(name, str)
    return name.lower().strip()
