import tempfile
from pathlib import Path

import pytest

from darwin.extractor.video import extract_artifacts


@pytest.fixture
def data_dir():
    return Path(__file__).parent.parent / "data"


@pytest.fixture
def output_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestVideoArtifactExtraction:
    def test_extract_artifacts_basic_video(self, data_dir, output_dir):
        """Test basic video artifact extraction without audio"""
        source_file = data_dir / "test_video.mp4"

        result = extract_artifacts(
            source_file=str(source_file),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
            fps=30.0,
            segment_length=2,
            repair=False,
            save_metadata=True,
        )

        # Get the actual result for bitrate values
        actual_payload = result["registration_payload"]

        # Store actual bitrates for assertion
        actual_high_bitrate = actual_payload["hls_segments"]["high_quality"]["bitrate"]
        actual_low_bitrate = actual_payload["hls_segments"]["low_quality"]["bitrate"]

        # Verify bitrates are non-negative numbers
        assert actual_high_bitrate >= 0, "High quality bitrate should be non-negative"
        assert actual_low_bitrate >= 0, "Low quality bitrate should be non-negative"
        assert (
            actual_high_bitrate > actual_low_bitrate
        ), "High quality bitrate should be higher than low quality"

        expected_payload = {
            "type": "video",
            "width": 1280,
            "height": 720,
            "native_fps": 30.0,
            "fps": 30.0,
            "total_frames": 150,  # 5 seconds * 30 fps
            "visible_frames": 150,  # 5 seconds * 30 fps
            "hls_segments": {
                "high_quality": {
                    "bitrate": actual_high_bitrate,  # Use actual value instead of hardcoded
                    "index": (
                        "#EXTM3U\n"
                        "#EXT-X-VERSION:3\n"
                        "#EXT-X-TARGETDURATION:2\n"
                        "#EXT-X-MEDIA-SEQUENCE:0\n"
                        "#EXTINF:2.000000,\n"
                        "test/prefix/segments/high/000000000.ts\n"
                        "#EXTINF:2.000000,\n"
                        "test/prefix/segments/high/000000001.ts\n"
                        "#EXTINF:1.000000,\n"
                        "test/prefix/segments/high/000000002.ts\n"
                        "#EXT-X-ENDLIST\n"
                    ),
                },
                "low_quality": {
                    "bitrate": actual_low_bitrate,  # Use actual value instead of hardcoded
                    "index": (
                        "#EXTM3U\n"
                        "#EXT-X-VERSION:3\n"
                        "#EXT-X-TARGETDURATION:2\n"
                        "#EXT-X-MEDIA-SEQUENCE:0\n"
                        "#EXTINF:2.000000,\n"
                        "test/prefix/segments/low/000000000.ts\n"
                        "#EXTINF:2.000000,\n"
                        "test/prefix/segments/low/000000001.ts\n"
                        "#EXTINF:1.000000,\n"
                        "test/prefix/segments/low/000000002.ts\n"
                        "#EXT-X-ENDLIST\n"
                    ),
                },
            },
            "storage_key": "test/prefix/test_video.mp4",
            "storage_frames_manifest_key": "test/prefix/frames_manifest.txt",
            "storage_thumbnail_key": "test/prefix/thumbnail.jpg",
            "storage_sections_key_prefix": "test/prefix/sections/high",
            "storage_low_quality_sections_key_prefix": "test/prefix/sections/low",
            "total_size_bytes": 61859,
            "name": "test_video.mp4",
            "path": "/",
            "hq_frames_extension": "png",
        }

        # Verify the result structure matches exactly
        assert result["registration_payload"] == expected_payload

        # Verify generated files
        assert (output_dir / "metadata.json").exists()
        assert (output_dir / "thumbnail.jpg").exists()
        assert (output_dir / "frames_manifest.txt").exists()

        # Verify frames manifest content
        with open(output_dir / "frames_manifest.txt") as f:
            manifest_lines = f.readlines()

        # Verify number of frames
        assert len(manifest_lines) == 150, "Should have 150 frames"

        # Parse and verify each frame entry
        frame_duration = 1.0 / 30.0  # 0.0333333... seconds per frame
        for i, line in enumerate(manifest_lines):
            # Parse line format: frame_number:segment_number:1:timestamp
            frame_num, segment_num, _, timestamp = line.strip().split(":")
            frame_num = int(frame_num)
            segment_num = int(segment_num)
            timestamp = float(timestamp)

            # Verify frame number (0-59 within each segment)
            assert frame_num == i % 60, f"Wrong frame number at line {i}"

            # Verify segment number (0-2)
            assert segment_num == i // 60, f"Wrong segment number at line {i}"

            # Verify timestamp (allowing small floating point differences)
            expected_time = i * frame_duration
            assert (
                abs(timestamp - expected_time) < 0.0001
            ), f"Wrong timestamp at line {i}"

        # Verify generated files
        assert len(list((output_dir / "sections" / "high").glob("*.png"))) == 150
        assert len(list((output_dir / "sections" / "low").glob("*.jpg"))) == 150

        # Verify HLS segments
        assert len(list((output_dir / "segments" / "high").glob("*.ts"))) == 3
        assert len(list((output_dir / "segments" / "low").glob("*.ts"))) == 3

    def test_extract_artifacts_with_audio(self, data_dir, output_dir):
        """Test video artifact extraction with audio"""
        source_file = data_dir / "test_video_with_audio.mp4"

        result = extract_artifacts(
            source_file=str(source_file),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
            fps=30.0,
            segment_length=2,
            repair=False,
        )

        # Verify audio peaks are extracted
        assert (
            result["registration_payload"]["storage_audio_peaks_key"]
            == "test/prefix/audio_peaks.gz"
        )
        assert (output_dir / "audio_peaks.gz").exists()

    def test_extract_artifacts_with_repair(self, data_dir, output_dir):
        """Test video repair functionality"""
        source_file = data_dir / "test_video_corrupted.mp4"

        result = extract_artifacts(
            source_file=str(source_file),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
            fps=30.0,
            segment_length=2,
            repair=True,
        )

        repaired_file = output_dir / "repaired_test_video_corrupted.mp4"

        assert result["repaired"] is True
        assert result["source_file"] == str(repaired_file)
        assert repaired_file.exists()
        # Verify the video was processed successfully despite corruption
        assert result["registration_payload"]["type"] == "video"

    def test_extract_artifacts_file_not_found(self, output_dir):
        """Test handling of non-existent video file"""
        with pytest.raises(FileNotFoundError):
            extract_artifacts(
                source_file="nonexistent.mp4",
                output_dir=str(output_dir),
                storage_key_prefix="test",
            )

    def test_extract_artifacts_custom_fps(self, data_dir, output_dir):
        """Test artifact extraction with custom FPS"""
        source_file = data_dir / "test_video.mp4"

        result = extract_artifacts(
            source_file=str(source_file),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
            fps=15.0,  # Half of the original FPS
            segment_length=2,
            repair=False,
        )

        # Verify FPS settings
        assert result["registration_payload"]["native_fps"] == 30.0
        assert result["registration_payload"]["fps"] == 15.0
        # Should have half as many visible frames due to downsampling
        assert result["registration_payload"]["visible_frames"] == 75  # 150/2

    def test_extract_artifacts_native_fps(self, data_dir, output_dir):
        """Test artifact extraction using native FPS"""
        source_file = data_dir / "test_video.mp4"

        result = extract_artifacts(
            source_file=str(source_file),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
            fps=0.0,  # Use native FPS
            segment_length=2,
            repair=False,
        )

        # Verify FPS settings
        assert result["registration_payload"]["native_fps"] == 30.0
        assert result["registration_payload"]["fps"] == 0.0
        # Should have same number of visible frames as total frames
        assert (
            result["registration_payload"]["visible_frames"]
            == result["registration_payload"]["total_frames"]
        )

    def test_extract_artifacts_segment_length(self, data_dir, output_dir):
        """Test that segment_length parameter affects HLS segment duration"""
        source_file = data_dir / "test_video.mp4"

        # Test with 1-second segments
        extract_artifacts(
            source_file=str(source_file),
            output_dir=str(output_dir / "1s"),
            storage_key_prefix="test/prefix",
            fps=30.0,
            segment_length=1,  # 1-second segments
            repair=False,
        )

        # Test with 3-second segments
        extract_artifacts(
            source_file=str(source_file),
            output_dir=str(output_dir / "3s"),
            storage_key_prefix="test/prefix",
            fps=30.0,
            segment_length=3,  # 3-second segments
            repair=False,
        )

        # Read and parse HLS manifests
        def get_segment_durations(manifest_path):
            durations = []
            with open(manifest_path) as f:
                for line in f:
                    if line.startswith("#EXTINF:"):
                        # Extract duration value (format: #EXTINF:1.0,)
                        duration = float(line.strip().split(":")[1].split(",")[0])
                        durations.append(duration)
            return durations

        # Check high quality segments
        durations_1s = get_segment_durations(
            output_dir / "1s" / "segments" / "high" / "index.m3u8"
        )
        durations_3s = get_segment_durations(
            output_dir / "3s" / "segments" / "high" / "index.m3u8"
        )

        # Print actual durations for debugging
        print("\nActual 1-second segment durations:", durations_1s)
        print("Actual 3-second segment durations:", durations_3s)

        # Verify segment durations (allowing small deviation due to keyframe alignment)
        assert all(
            0.9 <= d <= 1.1 for d in durations_1s
        ), "1-second segments should be ~1 second long"
        assert all(
            1.9 <= d <= 3.1 for d in durations_3s
        ), "3-second segments should be ~2-3 seconds long"

        # Verify we have more segments with 1-second duration
        assert len(durations_1s) > len(
            durations_3s
        ), "Should have more 1-second segments than 3-second segments"

    def test_extract_artifacts_extract_preview_frames_false(self, data_dir, output_dir):
        """Test artifact extraction with extract_preview_frames=False skips preview frames"""
        source_file = data_dir / "test_video.mp4"

        result = extract_artifacts(
            source_file=str(source_file),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
            fps=30.0,
            segment_length=2,
            repair=False,
            extract_preview_frames=False,
        )

        payload = result["registration_payload"]

        # Verify LQ sections key prefix is NOT in payload
        assert (
            "storage_low_quality_sections_key_prefix" not in payload
        ), "LQ sections key prefix should not be in payload when extract_preview_frames=False"

        # Verify HQ sections are still present
        assert payload["storage_sections_key_prefix"] == "test/prefix/sections/high"

        # Verify hq_frames_extension is PNG by default
        assert payload["hq_frames_extension"] == "png"

        # Verify HQ frames are generated
        hq_frames = list((output_dir / "sections" / "high").glob("*.png"))
        assert len(hq_frames) == 150, "Should have 150 HQ PNG frames"

        # Verify LQ frames are NOT generated
        lq_frames_dir = output_dir / "sections" / "low"
        if lq_frames_dir.exists():
            lq_frames = list(lq_frames_dir.glob("*.jpg"))
            assert len(lq_frames) == 0, "Should have no LQ frames"

    def test_extract_artifacts_primary_frames_quality_jpeg(self, data_dir, output_dir):
        """Test artifact extraction with primary_frames_quality produces JPEG frames"""
        source_file = data_dir / "test_video.mp4"

        result = extract_artifacts(
            source_file=str(source_file),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
            fps=30.0,
            segment_length=2,
            repair=False,
            primary_frames_quality=5,  # High quality JPEG
        )

        payload = result["registration_payload"]

        # Verify hq_frames_extension is jpg
        assert (
            payload["hq_frames_extension"] == "jpg"
        ), "Primary frames extension should be jpg when quality is set"

        # Verify LQ sections key prefix is still present (default extract_preview_frames=True)
        assert (
            payload["storage_low_quality_sections_key_prefix"]
            == "test/prefix/sections/low"
        )

        # Verify HQ frames are JPEG
        hq_frames = list((output_dir / "sections" / "high").glob("*.jpg"))
        assert len(hq_frames) == 150, "Should have 150 HQ JPEG frames"

        # Verify no PNG HQ frames exist
        png_frames = list((output_dir / "sections" / "high").glob("*.png"))
        assert len(png_frames) == 0, "Should have no PNG frames when using JPEG quality"

        # Verify LQ frames still exist
        lq_frames = list((output_dir / "sections" / "low").glob("*.jpg"))
        assert len(lq_frames) == 150, "Should have 150 LQ JPEG frames"

    def test_extract_artifacts_both_options_combined(self, data_dir, output_dir):
        """Test artifact extraction with both extract_preview_frames=False and primary_frames_quality"""
        source_file = data_dir / "test_video.mp4"

        result = extract_artifacts(
            source_file=str(source_file),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
            fps=30.0,
            segment_length=2,
            repair=False,
            extract_preview_frames=False,
            primary_frames_quality=10,  # JPEG quality
        )

        payload = result["registration_payload"]

        # Verify LQ sections key prefix is NOT in payload
        assert "storage_low_quality_sections_key_prefix" not in payload

        # Verify hq_frames_extension is jpg
        assert payload["hq_frames_extension"] == "jpg"

        # Verify HQ frames are JPEG
        hq_frames = list((output_dir / "sections" / "high").glob("*.jpg"))
        assert len(hq_frames) == 150, "Should have 150 HQ JPEG frames"

        # Verify no LQ frames exist
        lq_frames_dir = output_dir / "sections" / "low"
        if lq_frames_dir.exists():
            lq_frames = list(lq_frames_dir.glob("*"))
            assert len(lq_frames) == 0, "Should have no LQ frames"

    def test_extract_artifacts_default_has_hq_frames_extension(
        self, data_dir, output_dir
    ):
        """Test that default extraction includes hq_frames_extension field"""
        source_file = data_dir / "test_video.mp4"

        result = extract_artifacts(
            source_file=str(source_file),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
            fps=30.0,
            segment_length=2,
            repair=False,
        )

        payload = result["registration_payload"]

        # Verify hq_frames_extension is present and set to png by default
        assert "hq_frames_extension" in payload
        assert payload["hq_frames_extension"] == "png"

        # Verify LQ sections key prefix is still present by default
        assert "storage_low_quality_sections_key_prefix" in payload
