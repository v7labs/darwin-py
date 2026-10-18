import copy

import numpy as np
import pytest

from darwin.lidar import geometry as g


def _check(manifest):
    """Every image's ``world_to_image`` is ``K @ camera_from_world[:3]`` with a rigid ``camera_from_world``."""
    cams = {c["name"]: c for c in manifest["cameras"]}
    n = 0
    for frame in manifest["frames"]:
        for name, image in (frame.get("images") or {}).items():
            k = g.intrinsics_matrix(cams[name])
            cfw = np.array(image["camera_from_world"])
            assert np.allclose(cfw[:3, :3] @ cfw[:3, :3].T, np.eye(3), atol=1e-5)
            assert np.allclose(cfw[3], [0, 0, 0, 1])
            assert np.allclose(
                image["world_to_image"], k @ cfw[:3], rtol=1e-5, atol=1e-3
            )
            n += 1
    assert n
    return cams


def _with_package_calibration(annotation_file, manifest):
    """
    ``annotation_file`` with the slot metadata a Darwin export of the package carries (busybee:
    ``cameras``, ``origin``, per-frame ``cameras[cam].camera_from_world``).
    """
    af = copy.deepcopy(annotation_file)
    meta = af.slots[0].metadata
    meta["cameras"] = manifest["cameras"]
    if "origin" in manifest:
        meta["origin"] = manifest["origin"]
    for frame, built in zip(meta["frames"], manifest["frames"]):
        frame["cameras"] = {
            cam: {"camera_from_world": image["camera_from_world"]}
            for cam, image in (built.get("images") or {}).items()
        }
    return af


@pytest.fixture
def check_calibration():
    return _check


@pytest.fixture
def with_package_calibration():
    return _with_package_calibration
