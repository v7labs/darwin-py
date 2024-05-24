def test_imports_version_without_error() -> None:
    from darwin.version import __version__

    assert __version__ is not None
    assert isinstance(__version__, str)
