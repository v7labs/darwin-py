from . import csvtags, dataloop, pascalvoc

supported_formats = [
    ("pascalvoc", pascalvoc.parse_file),
    ("dataloop", dataloop.parse_file),
    ("csvtags", csvtags.parse_file),
]
