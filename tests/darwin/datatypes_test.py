from typing import Any, Dict, List

from darwin.datatypes import (
    GraphData,
    GraphDataEdge,
    GraphDataNode,
    Point,
    StringData,
    StringDataSource,
    TableData,
    TableDataCell,
    make_complex_polygon,
    make_graph,
    make_polygon,
    make_string,
    make_table,
)


def describe_make_polygon():
    def it_returns_annotation_with_default_params():
        class_name: str = "class_name"
        points: List[Point] = [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}]
        annotation = make_polygon(class_name, points)

        assert_annoation_class(annotation, class_name, "polygon")

        path = annotation.data.get("path")
        assert path == points

    def it_returns_annotation_with_bounding_box():
        class_name: str = "class_name"
        points: List[Point] = [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}]
        bbox: Dict[str, float] = {"x": 1, "y": 2, "w": 2, "h": 2}
        annotation = make_polygon(class_name, points, bbox)

        assert_annoation_class(annotation, class_name, "polygon")

        path = annotation.data.get("path")
        assert path == points

        class_bbox = annotation.data.get("bounding_box")
        assert class_bbox == bbox


def describe_make_complex_polygon():
    def it_returns_annotation_with_default_params():
        class_name: str = "class_name"
        points: List[List[Point]] = [
            [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}],
            [{"x": 4, "y": 5}, {"x": 6, "y": 7}, {"x": 4, "y": 5}],
        ]
        annotation = make_complex_polygon(class_name, points)

        assert_annoation_class(annotation, class_name, "complex_polygon", "polygon")

        paths = annotation.data.get("paths")
        assert paths == points

    def it_returns_annotation_with_bounding_box():
        class_name: str = "class_name"
        points: List[List[Point]] = [
            [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}],
            [{"x": 4, "y": 5}, {"x": 6, "y": 7}, {"x": 4, "y": 5}],
        ]
        bbox: Dict[str, float] = {"x": 1, "y": 2, "w": 2, "h": 2}
        annotation = make_complex_polygon(class_name, points, bbox)

        assert_annoation_class(annotation, class_name, "complex_polygon", "polygon")

        paths = annotation.data.get("paths")
        assert paths == points

        class_bbox = annotation.data.get("bounding_box")
        assert class_bbox == bbox


def describe_make_string():
    def it_returns_string_annotation():
        class_name: str = "class_name"
        parameters: Dict[str, Any] = {
            "sources": [{"id": "uuid-1", "ranges": [[0, 8]]}, {"id": "uuid-2", "ranges": None}]
        }
        annotation = make_string(class_name, parameters)

        expected_data: StringData = StringData(
            sources=[StringDataSource(id="uuid-1", ranges=[(0, 8)]), StringDataSource(id="uuid-2", ranges=None)]
        )

        assert_annoation_class(annotation, class_name, "string")
        assert annotation.data == expected_data


def describe_make_graph():
    def it_returns_graph_annotation():
        class_name: str = "class_name"
        parameters: Dict[str, Any] = {
            "edges": [{"end": "value", "start": "key"}],
            "nodes": [
                {"id": "dae7b1d2-0292-4cd1-a13d-5040bc762523", "name": "key"},
                {"id": "3e1b4890-ec28-4853-91f4-f7efeaa7dcd0", "name": "value"},
            ],
        }
        annotation = make_graph(class_name, parameters)

        expected_data: GraphData = GraphData(
            edges=[GraphDataEdge(start="key", end="value")],
            nodes=[
                GraphDataNode(id="dae7b1d2-0292-4cd1-a13d-5040bc762523", name="key"),
                GraphDataNode(id="3e1b4890-ec28-4853-91f4-f7efeaa7dcd0", name="value"),
            ],
        )

        assert_annoation_class(annotation, class_name, "graph")
        assert annotation.data == expected_data


def describe_make_table():
    def it_returns_table_annotation():
        class_name: str = "class_name"

        parameters: Dict[str, Any] = {
            "cells": [
                {
                    "id": "25beefe5-74cd-4b85-b9d6-7c70a9a5314b",
                    "col": 1,
                    "row": 1,
                    "col_span": 1,
                    "row_span": 1,
                    "is_header": False,
                    "bounding_box": {
                        "h": 64.58190971426666,
                        "w": 217.52343571186066,
                        "x": 1233.9765247106552,
                        "y": 212.91808361560106,
                    },
                },
                {
                    "id": "6bd4e128-8334-4b84-b9ce-f3a057359e0d",
                    "col": 2,
                    "row": 1,
                    "col_span": 1,
                    "row_span": 1,
                    "is_header": False,
                    "bounding_box": {
                        "h": 64.58190971426666,
                        "w": 193.9101600497961,
                        "x": 1451.4999604225159,
                        "y": 212.91808361560106,
                    },
                },
                {
                    "id": "f85d902c-c045-45e0-bbac-c22e6116eb03",
                    "col": 1,
                    "row": 2,
                    "col_span": 1,
                    "row_span": 1,
                    "is_header": False,
                    "bounding_box": {
                        "h": 59.668517868965864,
                        "w": 217.52343571186066,
                        "x": 1233.9765247106552,
                        "y": 277.50000566244125,
                    },
                },
                {
                    "id": "d8dc6afd-fb2a-4621-986d-efb3a6655505",
                    "col": 2,
                    "row": 2,
                    "col_span": 1,
                    "row_span": 1,
                    "is_header": False,
                    "bounding_box": {
                        "h": 59.668517868965864,
                        "w": 193.9101600497961,
                        "x": 1451.4999604225159,
                        "y": 277.50000566244125,
                    },
                },
            ],
            "bounding_box": {
                "h": 124.25042347237468,
                "w": 411.43359576165676,
                "x": 1233.9765247106552,
                "y": 212.91808361560106,
            },
        }

        annotation = make_table(class_name, parameters)

        expected_data: TableData = TableData(
            cells=[
                TableDataCell(
                    id="25beefe5-74cd-4b85-b9d6-7c70a9a5314b",
                    col=1,
                    row=1,
                    col_span=1,
                    row_span=1,
                    is_header=False,
                    bounding_box={
                        "h": 64.58190971426666,
                        "w": 217.52343571186066,
                        "x": 1233.9765247106552,
                        "y": 212.91808361560106,
                    },
                ),
                TableDataCell(
                    id="6bd4e128-8334-4b84-b9ce-f3a057359e0d",
                    col=2,
                    row=1,
                    col_span=1,
                    row_span=1,
                    is_header=False,
                    bounding_box={
                        "h": 64.58190971426666,
                        "w": 193.9101600497961,
                        "x": 1451.4999604225159,
                        "y": 212.91808361560106,
                    },
                ),
                TableDataCell(
                    id="f85d902c-c045-45e0-bbac-c22e6116eb03",
                    col=1,
                    row=2,
                    col_span=1,
                    row_span=1,
                    is_header=False,
                    bounding_box={
                        "h": 59.668517868965864,
                        "w": 217.52343571186066,
                        "x": 1233.9765247106552,
                        "y": 277.50000566244125,
                    },
                ),
                TableDataCell(
                    id="d8dc6afd-fb2a-4621-986d-efb3a6655505",
                    col=2,
                    row=2,
                    col_span=1,
                    row_span=1,
                    is_header=False,
                    bounding_box={
                        "h": 59.668517868965864,
                        "w": 193.9101600497961,
                        "x": 1451.4999604225159,
                        "y": 277.50000566244125,
                    },
                ),
            ],
            bounding_box={
                "h": 124.25042347237468,
                "w": 411.43359576165676,
                "x": 1233.9765247106552,
                "y": 212.91808361560106,
            },
        )

        assert_annoation_class(annotation, class_name, "table")
        assert annotation.data == expected_data


def assert_annoation_class(annotation, name, type, internal_type=None):
    assert annotation.annotation_class.name == name
    assert annotation.annotation_class.annotation_type == type
    assert annotation.annotation_class.annotation_internal_type == internal_type
