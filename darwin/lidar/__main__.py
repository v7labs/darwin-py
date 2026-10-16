"""
``python -m darwin.lidar`` -- dataset conversion for Darwin LiDAR items.

    python -m darwin.lidar build <format> <args...>          raw dataset -> .lidar.zip / .pcd
    python -m darwin.lidar labels <format> <args...> -o DIR  dataset labels -> Darwin JSON 2.0
    python -m darwin.lidar export <format> FILES... -o DIR   Darwin JSON 2.0 -> format

Options of each command come from the keyword arguments of the Python function it calls
(``python -m darwin.lidar build kitti_raw -h``).
"""

import argparse
import collections.abc
import inspect
import json
import sys
import types
import typing
from importlib import import_module
from typing import Any, Callable, Dict, List, Optional

BUILDERS = {
    "pcd": "generic:convert_cloud",
    "pointcloud": "generic:build_pointcloud",
    "kitti_raw": "kitti:build_kitti_raw",
    "kitti_tracking": "kitti:build_kitti_tracking",
    "kitti_object": "kitti:build_kitti_object",
    "kitti_odometry": "semantic_kitti:build_kitti_odometry",
    "nuscenes": "nuscenes:build_nuscenes",
    "av2": "av2:build_av2",
    "pandaset": "pandaset:build_pandaset",
}
IMPORTERS = {
    "kitti": "kitti:parse_kitti_labels",
    "kitti_tracking": "kitti:parse_kitti_tracking",
    "kitti_tracklets": "kitti:parse_kitti_tracklets",
    "semantic_kitti": "semantic_kitti:parse_semantic_kitti",
    "nuscenes": "nuscenes:parse_nuscenes",
    "nuscenes_lidarseg": "nuscenes:parse_nuscenes_lidarseg",
    "av2": "av2:parse_av2",
    "pandaset": "pandaset:parse_pandaset",
    "openlabel": "openlabel:parse_openlabel",
}
EXPORTERS = {
    "kitti": "kitti:export_kitti",
    "nuscenes": "nuscenes:export_nuscenes",
    "openlabel": "openlabel:export_openlabel",
    "semantic_kitti": "semantic_kitti:export_semantic_kitti",
    "ego": "ego:export_ego",
    "av2": "av2:export_av2",
}
HELP = {
    "build": "raw dataset -> Darwin upload (.lidar.zip / .pcd)",
    "labels": "dataset labels -> Darwin JSON 2.0 (then `darwin dataset import <dataset> darwin DIR`)",
    "export": "Darwin JSON 2.0 export -> dataset format",
}
LISTS = {list, tuple, collections.abc.Sequence, collections.abc.Iterable}


def _load(target: str) -> Callable[..., Any]:
    module, name = target.split(":")
    return getattr(import_module(f"darwin.lidar.{module}"), name)


def _members(annotation: Any) -> set:
    """Members of an ``Optional`` / ``Union``, else the annotation itself."""
    if typing.get_origin(annotation) in (typing.Union, types.UnionType):
        return set(typing.get_args(annotation)) - {type(None)}
    return {annotation}


def _converter(annotation: Any) -> Callable[[str], Any]:
    members = _members(annotation)
    if members == {int}:
        return int
    if members <= {int, float}:
        return float
    if any(typing.get_origin(t) in (dict, collections.abc.Mapping) for t in members):
        return json.loads
    return str


def _add_arguments(
    parser: argparse.ArgumentParser, fn: Callable[..., Any], skip: int
) -> None:
    for p in list(inspect.signature(fn, eval_str=True).parameters.values())[skip:]:
        flag = "--" + p.name.replace("_", "-")
        sequence = next(
            (t for t in _members(p.annotation) if typing.get_origin(t) in LISTS), None
        )
        if p.default is inspect.Parameter.empty:
            parser.add_argument(p.name)
        elif isinstance(p.default, bool):
            parser.add_argument(
                flag,
                dest=p.name,
                default=p.default,
                action=argparse.BooleanOptionalAction,
            )
        elif sequence is not None:
            element = (typing.get_args(sequence) or (str,))[0]
            parser.add_argument(
                flag,
                dest=p.name,
                default=p.default,
                nargs="+",
                type=_converter(element),
            )
        else:
            kind = (
                type(p.default)
                if isinstance(p.default, (int, float))
                else _converter(p.annotation)
            )
            parser.add_argument(flag, dest=p.name, default=p.default, type=kind)


def _kwargs(
    args: argparse.Namespace, fn: Callable[..., Any], skip: int
) -> Dict[str, Any]:
    return {n: getattr(args, n) for n in list(inspect.signature(fn).parameters)[skip:]}


def main(argv: Optional[List[str]] = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(
        prog="python -m darwin.lidar", description=__doc__.split("\n\n")[0]
    )
    commands = parser.add_subparsers(dest="command", required=True)
    groups = {"build": BUILDERS, "labels": IMPORTERS, "export": EXPORTERS}
    for command, table in groups.items():
        sub = commands.add_parser(command, help=HELP[command]).add_subparsers(
            dest="format", required=True
        )
        for fmt, target in table.items():
            p = sub.add_parser(fmt)
            if argv[:2] != [command, fmt]:
                continue  # only the selected command imports its module
            fn = _load(target)
            p.description = (inspect.getdoc(fn) or "").split("\n\n")[0]
            if command == "export":
                p.add_argument("files", nargs="+", help="Darwin JSON files or folders")
            _add_arguments(p, fn, 2 if command == "export" else 0)
            if command != "build":
                p.add_argument("-o", "--output", required=True, help="output folder")
    args = parser.parse_args(argv)
    fn = _load(groups[args.command][args.format])
    if args.command == "build":
        print(fn(**_kwargs(args, fn, 0)))
    elif args.command == "labels":
        from darwin.lidar.darwin_json import write_darwin_json

        for annotation_file in fn(**_kwargs(args, fn, 0)):
            print(write_darwin_json(annotation_file, args.output))
    else:
        from darwin.exporter.exporter import darwin_to_dt_gen

        files = darwin_to_dt_gen(args.files, split_sequences=False)
        fn(files, args.output, **_kwargs(args, fn, 2))
        print(args.output)


if __name__ == "__main__":
    main()
