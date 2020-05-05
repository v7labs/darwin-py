from . import dataloop
from . import pascalvoc

supported_formats = [
    ("pascalvoc", pascalvoc.parse_file),
    ("dataloop", dataloop.parse_file),
]
