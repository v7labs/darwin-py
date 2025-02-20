"""Tests for medical metadata functionality in the importer module."""

import pytest
from unittest.mock import MagicMock, Mock
from pathlib import Path
import numpy as np
from typing import List, Optional

from darwin.item import DatasetItem
from darwin.importer.importer import _get_remote_file_medical_metadata


class TestGetRemoteFileMedicalMetadata:
    """Tests for the _get_remote_file_medical_metadata function."""

    @pytest.fixture
    def base_medical_metadata(self):
        """Base medical metadata structure used across tests."""
        return {
            "height": 100,
            "width": 100,
            "pixdims": [1.0, 2.0, 3.0],
            "affine": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
            "original_affine": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
        }

    def create_mock_file(
        self,
        slot_name: str,
        medical_metadata: Optional[dict] = None,
        file_path: str = "/path/to/file",
    ) -> Mock:
        """Create a mock file with given medical metadata."""
        mock_file = MagicMock(spec=DatasetItem)
        mock_file.slots = [
            {
                "slot_name": slot_name,
                "total_sections": 10,
                "metadata": {"height": 100, "width": 100, "medical": medical_metadata},
            }
        ]
        mock_file.full_path = file_path
        return mock_file

    def assert_metadata_matches(
        self, metadata: dict, expected: dict, file_path: str, slot_name: str
    ):
        """Assert that metadata matches expected values."""
        path = Path(file_path)
        slot_metadata = metadata[path][slot_name]
        expected_slot_metadata = expected[path][slot_name]

        assert np.array_equal(slot_metadata["affine"], expected_slot_metadata["affine"])
        assert np.array_equal(
            slot_metadata["original_affine"], expected_slot_metadata["original_affine"]
        )
        assert np.array_equal(
            slot_metadata["axial_flips"], expected_slot_metadata["axial_flips"]
        )

        # Assert scalar values
        assert slot_metadata["primary_plane"] == expected_slot_metadata["primary_plane"]
        assert slot_metadata["num_frames"] == expected_slot_metadata["num_frames"]
        assert slot_metadata["width"] == expected_slot_metadata["width"]
        assert slot_metadata["height"] == expected_slot_metadata["height"]
        assert slot_metadata["legacy"] == expected_slot_metadata["legacy"]
        assert slot_metadata["pixdims"] == expected_slot_metadata["pixdims"]

    def test_empty_list(self):
        """Test that empty input list returns empty dictionary"""
        remote_files: List[DatasetItem] = []
        metadata = _get_remote_file_medical_metadata(remote_files)
        assert metadata == {}

    def test_no_slots(self):
        """Test that files with no slots are handled correctly"""
        mock_file = MagicMock(spec=DatasetItem)
        mock_file.slots = None
        mock_file.full_path = "/path/to/file"
        metadata = _get_remote_file_medical_metadata([mock_file])
        assert metadata == {}

    def test_non_medical_slots(self):
        """Test that files with non-medical slots are handled correctly"""
        mock_file = self.create_mock_file("slot1")
        metadata = _get_remote_file_medical_metadata([mock_file])
        assert metadata == {}

    def test_monai_planes(self, base_medical_metadata):
        """Test MONAI-handled medical slots with different planes"""
        test_cases = [
            ("AXIAL", [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]),
            ("CORONAL", [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]),
            ("SAGITTAL", [[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]]),
        ]

        for plane, original_affine in test_cases:
            medical_metadata = {**base_medical_metadata}
            medical_metadata.update(
                {
                    "handler": "MONAI",
                    "plane_map": {"slot1": plane},
                    "original_affine": original_affine,
                }
            )

            mock_file = self.create_mock_file("slot1", medical_metadata)
            metadata = _get_remote_file_medical_metadata([mock_file])

            expected_metadata = {
                Path("/path/to/file"): {
                    "slot1": {
                        "legacy": False,
                        "affine": np.array(
                            base_medical_metadata["affine"], dtype=np.float64
                        ),
                        "original_affine": np.array(original_affine, dtype=np.float64),
                        "pixdims": [1.0, 2.0, 3.0],
                        "width": 100,
                        "height": 100,
                        "primary_plane": plane,
                        "num_frames": 10,
                        "axial_flips": np.array([1, 1, 1]),
                    }
                }
            }

            self.assert_metadata_matches(
                metadata, expected_metadata, "/path/to/file", "slot1"
            )

    def test_legacy_nifti(self, base_medical_metadata):
        """Test legacy NifTI scaling"""
        medical_metadata = {**base_medical_metadata}
        medical_metadata.update(
            {
                "plane_map": {"slot1": "AXIAL"},
            }
        )

        mock_file = self.create_mock_file("slot1", medical_metadata)
        metadata = _get_remote_file_medical_metadata([mock_file])

        expected_metadata = {
            Path("/path/to/file"): {
                "slot1": {
                    "legacy": True,
                    "affine": np.array(
                        base_medical_metadata["affine"], dtype=np.float64
                    ),
                    "original_affine": np.array(
                        base_medical_metadata["original_affine"], dtype=np.float64
                    ),
                    "pixdims": [1.0, 2.0, 3.0],
                    "width": 100,
                    "height": 100,
                    "primary_plane": "AXIAL",
                    "num_frames": 10,
                    "axial_flips": np.array([1, 1, 1]),
                }
            }
        }

        self.assert_metadata_matches(
            metadata, expected_metadata, "/path/to/file", "slot1"
        )

    def test_mixed(self, base_medical_metadata):
        """Test mixed case with both MONAI and legacy NifTI files"""
        # MONAI file
        monai_metadata = {**base_medical_metadata}
        monai_metadata.update(
            {
                "handler": "MONAI",
                "plane_map": {"slot1": "AXIAL"},
            }
        )
        mock_file1 = self.create_mock_file("slot1", monai_metadata, "/path/to/file1")

        # Legacy NifTI file
        legacy_metadata = {**base_medical_metadata}
        legacy_metadata.update(
            {
                "plane_map": {"slot2": "AXIAL"},
            }
        )
        mock_file2 = self.create_mock_file("slot2", legacy_metadata, "/path/to/file2")

        metadata = _get_remote_file_medical_metadata([mock_file1, mock_file2])

        expected_metadata = {
            Path("/path/to/file1"): {
                "slot1": {
                    "legacy": False,
                    "affine": np.array(
                        base_medical_metadata["affine"], dtype=np.float64
                    ),
                    "original_affine": np.array(
                        base_medical_metadata["original_affine"], dtype=np.float64
                    ),
                    "pixdims": [1.0, 2.0, 3.0],
                    "width": 100,
                    "height": 100,
                    "primary_plane": "AXIAL",
                    "num_frames": 10,
                    "axial_flips": np.array([1, 1, 1]),
                }
            },
            Path("/path/to/file2"): {
                "slot2": {
                    "legacy": True,
                    "affine": np.array(
                        base_medical_metadata["affine"], dtype=np.float64
                    ),
                    "original_affine": np.array(
                        base_medical_metadata["original_affine"], dtype=np.float64
                    ),
                    "pixdims": [1.0, 2.0, 3.0],
                    "width": 100,
                    "height": 100,
                    "primary_plane": "AXIAL",
                    "num_frames": 10,
                    "axial_flips": np.array([1, 1, 1]),
                }
            },
        }

        self.assert_metadata_matches(
            metadata, expected_metadata, "/path/to/file1", "slot1"
        )
        self.assert_metadata_matches(
            metadata, expected_metadata, "/path/to/file2", "slot2"
        )

    def test_axial_flips(self, base_medical_metadata):
        """Test different axial flip configurations"""
        test_cases = [
            (
                "x_flip",
                [[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
                [-1, 1, 1],
            ),
            (
                "y_flip",
                [[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
                [1, -1, 1],
            ),
            (
                "z_flip",
                [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]],
                [1, 1, -1],
            ),
            (
                "xyz_flip",
                [[-1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]],
                [-1, -1, -1],
            ),
        ]

        for name, original_affine, expected_flips in test_cases:
            medical_metadata = {**base_medical_metadata}
            medical_metadata.update(
                {
                    "handler": "MONAI",
                    "plane_map": {"slot1": "AXIAL"},
                    "original_affine": original_affine,
                }
            )

            mock_file = self.create_mock_file("slot1", medical_metadata)
            metadata = _get_remote_file_medical_metadata([mock_file])

            expected_metadata = {
                Path("/path/to/file"): {
                    "slot1": {
                        "legacy": False,
                        "affine": np.array(
                            base_medical_metadata["affine"], dtype=np.float64
                        ),
                        "original_affine": np.array(original_affine, dtype=np.float64),
                        "pixdims": [1.0, 2.0, 3.0],
                        "width": 100,
                        "height": 100,
                        "primary_plane": "AXIAL",
                        "num_frames": 10,
                        "axial_flips": np.array(expected_flips),
                    }
                }
            }

            self.assert_metadata_matches(
                metadata, expected_metadata, "/path/to/file", "slot1"
            )
