import json
import os
from typing import Dict

from PIL import Image, ImageOps

# Same bounds as the video thumbnail (see darwin/extractor/video.py)
THUMBNAIL_MAX_SIZE = (356, 200)
THUMBNAIL_FILE_NAME = "thumbnail.jpg"
# Used when the source image itself is named "thumbnail.jpg", so the upload
# of the thumbnail does not overwrite the source file in storage.
FALLBACK_THUMBNAIL_FILE_NAME = "darwin_thumbnail.jpg"


def _to_rgb(image: Image.Image) -> Image.Image:
    """Convert an image of any mode to RGB, putting transparency on white."""
    if image.mode in ("I", "I;16", "I;16B", "I;16L", "I;16N"):
        # Scale 16-bit samples to 8 bits instead of clipping them at 255
        image = image.convert("I").point(lambda value: value * (1 / 256))
        return image.convert("L").convert("RGB")

    if image.mode == "P" and "transparency" in image.info:
        image = image.convert("RGBA")

    if image.mode in ("RGBA", "LA", "PA"):
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.getchannel("A"))
        return background

    return image.convert("RGB")


def extract_artifacts(
    source_file: str,
    output_dir: str,
    storage_key_prefix: str,
    *,
    save_metadata: bool = False,
) -> Dict:
    """
    Extracts image artifacts (dimensions and a JPEG thumbnail) for
    read-only registration in the Darwin platform.

    Width and height are the dimensions after the EXIF orientation is applied,
    which is how browsers display the image. The thumbnail is also rotated.

    Args:
        source_file: Path to source image file
        output_dir: Directory to store generated artifacts
        storage_key_prefix: Prefix for storage keys
        save_metadata: If True, save metadata to a file, defaults to False

    Returns:
        Dict containing metadata and the registration payload

    Raises:
        FileNotFoundError: If source_file does not exist
        ValueError: If source_file cannot be read as an image
    """
    if not os.path.exists(source_file):
        raise FileNotFoundError(f"Source image file not found: {source_file}")

    os.makedirs(output_dir, exist_ok=True)
    storage_key_prefix = storage_key_prefix.strip("/")
    source_file_name = os.path.basename(source_file)
    thumbnail_file_name = (
        FALLBACK_THUMBNAIL_FILE_NAME
        if source_file_name == THUMBNAIL_FILE_NAME
        else THUMBNAIL_FILE_NAME
    )

    try:
        with Image.open(source_file) as source_image:
            image = ImageOps.exif_transpose(source_image)
            width, height = image.size
            thumbnail = _to_rgb(image)
            thumbnail.thumbnail(THUMBNAIL_MAX_SIZE)
            thumbnail.save(
                os.path.join(output_dir, thumbnail_file_name), "JPEG", quality=85
            )
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError) as e:
        # Pillow raises UnidentifiedImageError (an OSError) for unknown data,
        # and OSError, SyntaxError or ValueError for corrupt or truncated data.
        raise ValueError(f"Cannot read image file {source_file}: {e}") from e

    registration_payload = {
        "type": "image",
        "width": width,
        "height": height,
        "storage_key": f"{storage_key_prefix}/{source_file_name}",
        "storage_thumbnail_key": f"{storage_key_prefix}/{thumbnail_file_name}",
        "total_size_bytes": os.path.getsize(source_file),
        "name": source_file_name,
        "path": "/",
    }

    result_metadata = {
        "source_file": source_file,
        "storage_key_prefix": storage_key_prefix,
        "registration_payload": registration_payload,
    }

    if save_metadata:
        with open(os.path.join(output_dir, "metadata.json"), "w") as f:
            json.dump(result_metadata, f, indent=2)

    return result_metadata
