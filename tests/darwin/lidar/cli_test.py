import json
from pathlib import Path
from typing import Mapping, Optional, Union

import numpy as np

from darwin.lidar.__main__ import _converter, main
from darwin.lidar.scene import read_scene


def test_cli_build_labels_export(tmp_path, capsys):
    seq = tmp_path / "sequences" / "00"
    (seq / "velodyne").mkdir(parents=True)
    (seq / "labels").mkdir()
    rng = np.random.default_rng(0)
    labels = []
    for i in range(2):
        rng.uniform(-5, 5, (20, 4)).astype("<f4").tofile(
            seq / "velodyne" / f"{i:06d}.bin"
        )
        label = rng.choice([0, 10, 40 | (3 << 16)], 20).astype("<u4")
        label.tofile(seq / "labels" / f"{i:06d}.label")
        labels.append(label)

    main(
        [
            "build",
            "pointcloud",
            str(seq / "velodyne"),
            str(tmp_path / "pkg"),
            "--fps",
            "5",
        ]
    )
    scene = read_scene(tmp_path / "pkg" / "velodyne.lidar.zip")
    assert scene.manifest["fps"] == 5 and len(scene) == 2

    names = '{"10": "Car", "40": "Road"}'
    main(
        [
            "labels",
            "semantic_kitti",
            str(seq / "labels"),
            "--class-names",
            names,
            "-o",
            str(tmp_path / "json"),
        ]
    )
    json_file = tmp_path / "json" / "semantickitti_00.lidar.json"
    assert {a["name"] for a in json.loads(json_file.read_text())["annotations"]} == {
        "Car",
        "Road",
    }

    main(
        [
            "export",
            "semantic_kitti",
            str(tmp_path / "json"),
            "--class-ids",
            '{"Car": 10, "Road": 40}',
            "-o",
            str(tmp_path / "out"),
        ]
    )
    for i, label in enumerate(labels):
        out = np.fromfile(
            tmp_path / "out" / "semantickitti_00" / "labels" / f"{i:06d}.label", "<u4"
        )
        assert (out == label).all()
    assert "out" in capsys.readouterr().out


def test_cli_converters():
    assert _converter(Optional[Union[str, Path, Mapping[str, str]]]) is str
    assert _converter(Optional[dict[int, str]])('{"10": "car"}') == {10: "car"}
    assert _converter(Optional[int])("3") == 3
