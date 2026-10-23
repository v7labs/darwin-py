import copy
import json
import re
import stat
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import orjson
import pytest

import darwin.dataset.json_formatter as formatter
from darwin.dataset.json_formatter import PrettyPrintError, pretty_print_json
from darwin.exporter.formats.darwin import build_image_annotation
from darwin.importer.formats.darwin import parse_path
from darwin.utils import parse_darwin_json, split_video_annotation


def _tokens(data: bytes) -> list[bytes]:
    return re.findall(rb'"(?:[^"\\]|\\.)*"|[^\s]', data)


@pytest.mark.parametrize(
    "source,expected",
    [
        (
            b' { "a" : [ 1, true, null, false, "x" ] } ',
            b'{\n  "a": [\n    1,\n    true,\n    null,\n    false,\n    "x"\n  ]\n}\n',
        ),
        (
            b'{"a":{},"b":[],"c":[{}]}',
            b'{\n  "a": {},\n  "b": [],\n  "c": [\n    {}\n  ]\n}\n',
        ),
        (b"  1e+001 \r\n", b"1e+001\n"),
        (b'"a"', b'"a"\n'),
        (b"false", b"false\n"),
        (b"null", b"null\n"),
    ],
)
def test_indents_valid_json(tmp_path: Path, source: bytes, expected: bytes):
    path = tmp_path / "annotation.json"
    path.write_bytes(source)

    pretty_print_json(path)

    assert path.read_bytes() == expected
    assert json.loads(path.read_bytes()) == json.loads(source)


@pytest.mark.parametrize("chunk_size", [1, 2, 3, 7, 64 * 1024])
def test_preserves_tokens_across_buffer_boundaries(tmp_path, monkeypatch, chunk_size):
    monkeypatch.setattr(formatter, "_CHUNK_SIZE", chunk_size)
    source = (
        '{"雪 🌱":"escaped \\n \\t \\r \\b \\f \\/ \\\\ \\" \\uD800 \\udfff",'
        '"duplicate":1,"duplicate":2,"numbers":[0,-0,-0.0,1.0000,1e+0002,'
        "1E-22,123456789012345678901234567890,0.12345678901234567890123456789]}"
    ).encode("utf-8")
    path = tmp_path / "annotation.json"
    path.write_bytes(source)

    pretty_print_json(path)

    assert _tokens(path.read_bytes()) == _tokens(source)
    assert json.loads(path.read_bytes()) == json.loads(source)


def test_streams_large_scalar_tokens_and_deep_containers(tmp_path, monkeypatch):
    monkeypatch.setattr(formatter, "_CHUNK_SIZE", 31)
    source = b'{"string":"' + b"x" * 100_000 + b'","number":' + b"1" * 100_000 + b"}"
    path = tmp_path / "annotation.json"
    path.write_bytes(source)
    pretty_print_json(path)
    assert _tokens(path.read_bytes()) == _tokens(source)

    source = b"[" * 1100 + b"0" + b"]" * 1100
    path.write_bytes(source)
    pretty_print_json(path)
    assert _tokens(path.read_bytes()) == _tokens(source)


@pytest.mark.parametrize(
    "source",
    [
        b"",
        b" \n\t",
        b"{",
        b"[",
        b"}",
        b"]",
        b"[}",
        b"{]",
        b"[,]",
        b"[1,]",
        b'{"a":1,}',
        b"[1 2]",
        b'{"a":1 "b":2}',
        b'{"a" 1}',
        b"{1:2}",
        b'{"a":}',
        b'[{"a":1]]',
        b"true false",
        b"{}[]",
        b"[]garbage",
        b"None",
        b"NaN",
        b"Infinity",
        b"-Infinity",
        b"tru",
        b"True",
        b"nul",
        b"falsee",
        b"[nulltrue]",
        b"-",
        b"+1",
        b"01",
        b"-01",
        b"1.",
        b".1",
        b"1e",
        b"1e+",
        b"1e-",
        b"--1",
        b"[1e2.3]",
        b"[0x1]",
        b"[1_000]",
        b"[1 2]",
        b'"unterminated',
        b'"control\x01"',
        b'"line\n"',
        b'"\\q"',
        b'"\\u"',
        b'"\\u123"',
        b'"\\u12x4"',
        b'"trailing\\',
        b'"\xff"',
        b'"\xc0\x80"',
        b'"\xed\xa0\x80"',
        b'"\xf4\x90\x80\x80"',
        b"\xef\xbb\xbf{}",
        b"[\v]",
        b"[\f]",
        b"[\xc2\xa0]",
        b"{}\x00",
    ],
)
def test_invalid_json_keeps_original_and_removes_temporary_file(tmp_path, source):
    path = tmp_path / "annotation.json"
    path.write_bytes(source)

    with pytest.raises(PrettyPrintError, match="original file is unchanged") as error:
        pretty_print_json(path)

    assert str(path) in str(error.value)
    assert path.read_bytes() == source
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("operation", ["read", "write", "permissions", "replace"])
def test_io_failure_keeps_original(tmp_path, operation):
    path = tmp_path / "annotation.json"
    source = b'{"a":1}'
    path.write_bytes(source)
    target = {
        "read": "pathlib.Path.open",
        "write": "darwin.dataset.json_formatter._format_json",
        "permissions": "pathlib.Path.chmod",
        "replace": "darwin.dataset.json_formatter.os.replace",
    }[operation]

    with patch(target, side_effect=OSError("simulated I/O failure")):
        with pytest.raises(PrettyPrintError, match="simulated I/O failure"):
            pretty_print_json(path)

    assert path.read_bytes() == source
    assert list(tmp_path.iterdir()) == [path]


def test_cleanup_failure_does_not_hide_formatting_error(tmp_path):
    path = tmp_path / "annotation.json"
    path.write_bytes(b"[invalid]")
    with patch("pathlib.Path.unlink", side_effect=OSError("cleanup failure")):
        with pytest.raises(PrettyPrintError, match="Expected a JSON value"):
            pretty_print_json(path)
    assert path.read_bytes() == b"[invalid]"


def test_supports_long_filenames(tmp_path):
    path = tmp_path / ("a" * 245 + ".json")
    path.write_bytes(b'{"a":1}')
    pretty_print_json(path)
    assert json.loads(path.read_bytes()) == {"a": 1}


def test_preserves_permissions_and_is_idempotent(tmp_path):
    path = tmp_path / "annotation.json"
    path.write_bytes(b'{"a":1}')
    path.chmod(0o640)
    original_mode = stat.S_IMODE(path.stat().st_mode)
    pretty_print_json(path)
    first_output = path.read_bytes()
    pretty_print_json(path)

    assert stat.S_IMODE(path.stat().st_mode) == original_mode
    assert path.read_bytes() == first_output


@pytest.fixture(params=["image", "video", "multi_slot"])
def native_document(request):
    filenames = {
        "image": "single_slotted_image_flat.json",
        "video": "single_slotted_video_flat.json",
        "multi_slot": "multi_slotted_item_flat.json",
    }
    with ZipFile("tests/data.zip") as archive:
        document = json.loads(
            archive.read("v7-darwin-json-v2/force_slots/" + filenames[request.param])
        )
        if request.param == "multi_slot":
            image = json.loads(
                archive.read(
                    "v7-darwin-json-v2/force_slots/single_slotted_image_flat.json"
                )
            )
            annotation = copy.deepcopy(image["annotations"][0])
            annotation["slot_names"] = [document["item"]["slots"][0]["slot_name"]]
            document["annotations"] = [annotation]
    document["properties"] = [
        {"name": "temperature", "type": "number", "value": 1.2345678901234567}
    ]
    for annotation in document["annotations"]:
        annotation["annotators"] = [
            {"full_name": "Author", "email": "author@example.com"}
        ]
        annotation["reviewers"] = [
            {"full_name": "Reviewer", "email": "reviewer@example.com"}
        ]
        annotation["properties"] = [
            {"name": "quality", "type": "string", "value": "checked"}
        ]
    return document


def test_native_content_and_import_export_roundtrip(tmp_path, native_document):
    source = json.dumps(native_document, separators=(",", ":")).encode()
    path = tmp_path / "annotation.json"
    path.write_bytes(source)

    compact_import = parse_path(path)
    assert compact_import is not None
    compact_outputs = _native_roundtrip(path, compact_import)
    pretty_print_json(path)
    formatted_import = parse_path(path)
    assert formatted_import is not None

    assert json.loads(path.read_bytes()) == native_document
    assert _tokens(path.read_bytes()) == _tokens(source)
    assert formatted_import.annotations == compact_import.annotations
    assert formatted_import.slots == compact_import.slots
    assert formatted_import.item_properties == compact_import.item_properties
    assert _native_roundtrip(path, formatted_import) == compact_outputs


def _native_roundtrip(path, annotation_file):
    frames = (
        split_video_annotation(annotation_file)
        if annotation_file.is_video
        else [annotation_file]
    )
    results = []
    for frame in frames:
        exported = build_image_annotation(frame, "Test team")
        output = path.with_name("roundtrip.json")
        output.write_bytes(orjson.dumps(exported))
        parsed = parse_darwin_json(output)
        assert parsed is not None
        results.append((exported, parsed.annotations, parsed.slots))
    return results


@pytest.mark.parametrize("chunk_size", [1, 2, 3, 31, 64 * 1024])
def test_updates_only_indexed_local_paths_and_preserves_other_tokens(
    tmp_path, monkeypatch, chunk_size
):
    monkeypatch.setattr(formatter, "_CHUNK_SIZE", chunk_size)
    raw = (
        b'{"local_path":1.0000,"noise":{"item":{"slots":[]}},'
        b'"it\\u0065m":{"slots":[{"source_files":['
        b'{"local_\\u0070ath":{"old":[1e+002]},"url":"u",'
        b'"n":0.12345678901234567890123456789,"'
        + b"x" * 1000
        + b'":"\\u0061\\/"},{}]},'
        b'{"source_files":[{"url":"v","local_path":false}]}]}}'
    )
    local_paths = {(0, 0): 'new/雪/"path', (0, 1): "", (1, 0): "last"}
    expected = (
        raw.replace(b'{"old":[1e+002]}', json.dumps(local_paths[(0, 0)]).encode())
        .replace(b"{}", b'{"local_path":""}')
        .replace(b'"local_path":false', b'"local_path":"last"')
    )
    path = tmp_path / "annotation.json"
    path.write_bytes(raw)

    pretty_print_json(path, local_paths=local_paths)

    assert _tokens(path.read_bytes()) == _tokens(expected)
    assert json.loads(path.read_bytes()) == json.loads(expected)
    first_output = path.read_bytes()
    pretty_print_json(path, local_paths=local_paths)
    assert path.read_bytes() == first_output


@pytest.mark.parametrize(
    "invalid_path", [b"01", b'"bad\\uXYZW"', b'{"old":1,}', b"[false,]"]
)
def test_replaced_local_path_still_validates_original_json(tmp_path, invalid_path):
    path = tmp_path / "annotation.json"
    original = (
        b'{"item":{"slots":[{"source_files":[{"local_path":' + invalid_path + b"}]}]}}"
    )
    path.write_bytes(original)

    with pytest.raises(PrettyPrintError):
        pretty_print_json(path, local_paths={(0, 0): "replacement"})

    assert path.read_bytes() == original
    assert not list(tmp_path.glob("*.tmp"))
