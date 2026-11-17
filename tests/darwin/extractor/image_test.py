import json
from pathlib import Path

import pytest
from PIL import Image

from darwin.extractor.image import THUMBNAIL_MAX_SIZE, extract_artifacts

EXIF_ORIENTATION_TAG = 0x0112


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    path = tmp_path / "artifacts"
    path.mkdir()
    return path


def _save_image(path: Path, image: Image.Image, **save_kwargs) -> Path:
    image.save(path, **save_kwargs)
    return path


def _open_thumbnail(output_dir: Path) -> Image.Image:
    thumbnail = Image.open(output_dir / "thumbnail.jpg")
    thumbnail.load()
    return thumbnail


class TestImageArtifactExtraction:
    def test_reads_dimensions(self, tmp_path, output_dir):
        source = _save_image(tmp_path / "image.png", Image.new("RGB", (800, 600)))

        result = extract_artifacts(
            source_file=str(source),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
        )

        payload = result["registration_payload"]
        assert payload["width"] == 800
        assert payload["height"] == 600

    def test_writes_bounded_jpeg_thumbnail_keeping_aspect_ratio(
        self, tmp_path, output_dir
    ):
        source = _save_image(tmp_path / "image.png", Image.new("RGB", (1600, 1200)))

        extract_artifacts(
            source_file=str(source),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
        )

        thumbnail = _open_thumbnail(output_dir)
        assert thumbnail.format == "JPEG"
        assert thumbnail.mode == "RGB"
        max_width, max_height = THUMBNAIL_MAX_SIZE
        assert thumbnail.width <= max_width
        assert thumbnail.height <= max_height
        assert max(thumbnail.width / max_width, thumbnail.height / max_height) == (
            pytest.approx(1.0, abs=0.01)
        )
        assert thumbnail.width / thumbnail.height == pytest.approx(
            1600 / 1200, rel=0.02
        )

    def test_does_not_upscale_small_images(self, tmp_path, output_dir):
        source = _save_image(tmp_path / "small.png", Image.new("RGB", (50, 30)))

        extract_artifacts(
            source_file=str(source),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
        )

        assert _open_thumbnail(output_dir).size == (50, 30)

    @pytest.mark.parametrize(
        "file_name, image, save_kwargs",
        [
            ("rgba.png", Image.new("RGBA", (64, 48), (255, 0, 0, 128)), {}),
            ("la.png", Image.new("LA", (64, 48), (100, 50)), {}),
            ("palette.png", Image.new("P", (64, 48), 3), {}),
            (
                "palette_transparent.png",
                Image.new("P", (64, 48), 0),
                {"transparency": 0},
            ),
            ("grayscale.png", Image.new("L", (64, 48), 128), {}),
            ("bilevel.bmp", Image.new("1", (64, 48), 1), {}),
            ("cmyk.jpg", Image.new("CMYK", (64, 48), (0, 255, 255, 0)), {}),
            ("cmyk.tiff", Image.new("CMYK", (64, 48), (0, 255, 255, 0)), {}),
            ("gray16.png", Image.new("I;16", (64, 48), 40000), {}),
            ("rgba.webp", Image.new("RGBA", (64, 48), (0, 0, 255, 255)), {}),
        ],
    )
    def test_converts_image_modes_to_rgb_thumbnail(
        self, tmp_path, output_dir, file_name, image, save_kwargs
    ):
        source = _save_image(tmp_path / file_name, image, **save_kwargs)

        result = extract_artifacts(
            source_file=str(source),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
        )

        thumbnail = _open_thumbnail(output_dir)
        assert thumbnail.format == "JPEG"
        assert thumbnail.mode == "RGB"
        assert thumbnail.size == (64, 48)
        assert result["registration_payload"]["width"] == 64
        assert result["registration_payload"]["height"] == 48

    def test_transparent_pixels_become_white(self, tmp_path, output_dir):
        source = _save_image(
            tmp_path / "transparent.png", Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        )

        extract_artifacts(
            source_file=str(source),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
        )

        red, green, blue = _open_thumbnail(output_dir).getpixel((20, 20))
        assert min(red, green, blue) >= 250

    def test_sixteen_bit_grayscale_is_scaled_not_clipped(self, tmp_path, output_dir):
        source = _save_image(
            tmp_path / "gray16.png", Image.new("I;16", (40, 40), 32768)
        )

        extract_artifacts(
            source_file=str(source),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
        )

        red, _, _ = _open_thumbnail(output_dir).getpixel((20, 20))
        assert 120 <= red <= 136

    def test_applies_exif_orientation(self, tmp_path, output_dir):
        exif = Image.Exif()
        exif[EXIF_ORIENTATION_TAG] = 6  # Rotate 90 CW to display
        source = _save_image(
            tmp_path / "rotated.jpg", Image.new("RGB", (400, 200)), exif=exif
        )

        result = extract_artifacts(
            source_file=str(source),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
        )

        payload = result["registration_payload"]
        assert (payload["width"], payload["height"]) == (200, 400)
        thumbnail = _open_thumbnail(output_dir)
        assert thumbnail.height > thumbnail.width

    def test_raises_file_not_found_for_missing_file(self, tmp_path, output_dir):
        with pytest.raises(FileNotFoundError, match="missing.png"):
            extract_artifacts(
                source_file=str(tmp_path / "missing.png"),
                output_dir=str(output_dir),
                storage_key_prefix="test/prefix",
            )

    def test_raises_value_error_for_corrupt_file(self, tmp_path, output_dir):
        source = tmp_path / "corrupt.png"
        source.write_bytes(b"this is not an image")

        with pytest.raises(ValueError, match="Cannot read image file"):
            extract_artifacts(
                source_file=str(source),
                output_dir=str(output_dir),
                storage_key_prefix="test/prefix",
            )

    def test_raises_value_error_for_truncated_file(self, tmp_path, output_dir):
        full = _save_image(tmp_path / "full.jpg", Image.effect_noise((256, 256), 64))
        source = tmp_path / "truncated.jpg"
        source.write_bytes(full.read_bytes()[:1024])

        with pytest.raises(ValueError, match="Cannot read image file"):
            extract_artifacts(
                source_file=str(source),
                output_dir=str(output_dir),
                storage_key_prefix="test/prefix",
            )

    def test_registration_payload(self, tmp_path, output_dir):
        source = _save_image(tmp_path / "photo.jpg", Image.new("RGB", (320, 240)))

        result = extract_artifacts(
            source_file=str(source),
            output_dir=str(output_dir),
            storage_key_prefix="/test/prefix/",
        )

        assert result["registration_payload"] == {
            "type": "image",
            "width": 320,
            "height": 240,
            "storage_key": "test/prefix/photo.jpg",
            "storage_thumbnail_key": "test/prefix/thumbnail.jpg",
            "total_size_bytes": source.stat().st_size,
            "name": "photo.jpg",
            "path": "/",
        }
        assert result["storage_key_prefix"] == "test/prefix"
        assert result["source_file"] == str(source)

    def test_saves_metadata_json(self, tmp_path, output_dir):
        source = _save_image(tmp_path / "photo.png", Image.new("RGB", (10, 20)))

        result = extract_artifacts(
            source_file=str(source),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
            save_metadata=True,
        )

        with open(output_dir / "metadata.json") as f:
            metadata = json.load(f)
        assert metadata == result
        assert set(metadata["registration_payload"]) == {
            "type",
            "width",
            "height",
            "storage_key",
            "storage_thumbnail_key",
            "total_size_bytes",
            "name",
            "path",
        }

    def test_does_not_save_metadata_json_by_default(self, tmp_path, output_dir):
        source = _save_image(tmp_path / "photo.png", Image.new("RGB", (10, 20)))

        extract_artifacts(
            source_file=str(source),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
        )

        assert sorted(p.name for p in output_dir.iterdir()) == ["thumbnail.jpg"]

    def test_thumbnail_does_not_overwrite_source_named_thumbnail(
        self, tmp_path, output_dir
    ):
        source = _save_image(tmp_path / "thumbnail.jpg", Image.new("RGB", (500, 500)))

        result = extract_artifacts(
            source_file=str(source),
            output_dir=str(output_dir),
            storage_key_prefix="test/prefix",
        )

        payload = result["registration_payload"]
        assert payload["storage_key"] == "test/prefix/thumbnail.jpg"
        assert payload["storage_thumbnail_key"] != payload["storage_key"]
        thumbnail_name = payload["storage_thumbnail_key"].rsplit("/", 1)[1]
        assert (output_dir / thumbnail_name).exists()
        assert not (output_dir / "thumbnail.jpg").exists()
