import gzip
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console

console = Console()


def _check_ffmpeg_version():
    """
    Check if FFmpeg version 5 or higher is installed.
    Raises RuntimeError if FFmpeg is not found or version is lower.
    """
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        version_line = result.stdout.split("\n")[0]
        # Extract major version number (e.g., "ffmpeg version 5.1.2" -> "5")
        version_match = re.search(r"ffmpeg version (\d+)", version_line)
        if not version_match:
            raise RuntimeError("Could not determine FFmpeg version")

        major_version = int(version_match.group(1))
        if major_version < 5:
            raise RuntimeError(
                f"FFmpeg version 5 or higher required, found version {major_version}"
            )

    except FileNotFoundError:
        raise RuntimeError(
            "FFmpeg not found. Please install FFmpeg version 5 or higher"
        )


def _create_directories(base_dir: str) -> Dict[str, str]:
    """Create required directory structure for artifacts"""

    paths = {
        "base_dir": base_dir,
        "segments": os.path.join(base_dir, "segments"),
        "sections": os.path.join(base_dir, "sections"),
    }

    # Create high/low quality segment dirs
    paths["segments_high"] = os.path.join(paths["segments"], "high")
    paths["segments_low"] = os.path.join(paths["segments"], "low")

    for path in paths.values():
        os.makedirs(path, exist_ok=True)

    return paths


def _maybe_repair_video(source_file: str, output_dir: str) -> Tuple[bool, str]:
    """
    Attempt to repair video if errors are detected.

    Args:
        source_file: Path to source video file
        output_dir: Directory to store repaired video if needed

    Returns:
        Tuple[bool, str]: (was_repaired, final_source_file_path)
    """
    console.print(f"Checking video for errors: {source_file}")
    errors = _check_video_for_errors(source_file)
    if errors:
        errors_list = errors.split("\n")
        first_three = "\n".join(errors_list[:3])
        console.print(f"Video contains errors:\n{first_three}\n...")
        console.print("Attempting to repair video...")
        repaired_file = _attempt_video_repair(source_file, output_dir)
        console.print(f"Video repaired successfully: {repaired_file}")
        return (True, repaired_file)
    else:
        console.print("No errors detected, proceeding with original video")
        return (False, source_file)


def _check_video_for_errors(source_file: str) -> str:
    """
    Check if video file has any errors using FFmpeg error detection.

    Args:
        source_file: Path to source video file

    Returns:
        str: Error message if errors were detected, empty string otherwise
    """
    cmd = [
        "ffmpeg",
        "-err_detect",
        "explode",
        "-xerror",
        "-v",
        "error",
        "-i",
        source_file,
        "-f",
        "null",
        "-",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stderr.strip()
    except subprocess.CalledProcessError as e:
        return e.stderr.strip()


def _attempt_video_repair(source_file: str, output_dir: str) -> str:
    """
    Attempt to repair corrupted video by re-encoding it using hardware acceleration if available.

    Args:
        source_file: Path to source video file
        output_dir: Directory to store repaired video

    Returns:
        str: Path to repaired video file
    """
    output_file = os.path.join(output_dir, f"repaired_{os.path.basename(source_file)}")

    try:
        # First try hardware accelerated encoding (H265)
        cmd = [
            "ffmpeg",
            "-y",
            "-fflags",
            "discardcorrupt+genpts",
            "-vaapi_device",
            "/dev/dri/renderD128",
            "-i",
            source_file,
            "-vf",
            "format=nv12,hwupload",
            "-c:v",
            "hevc_vaapi",
            "-c:a",
            "copy",
            "-vsync",
            "cfr",
            output_file,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_file
    except subprocess.CalledProcessError:
        console.print(
            "Hardware acceleration with H265 failed, falling back to software encoding with H264"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-fflags",
            "discardcorrupt+genpts",
            "-i",
            source_file,
            "-c:v",
            "libx264",
            "-c:a",
            "copy",
            "-vsync",
            "cfr",
            output_file,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_file


def _count_frames(source_file: str) -> int:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-count_frames",
        "-show_entries",
        "stream=nb_read_frames",
        "-of",
        "json",
        source_file,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return int(json.loads(result.stdout)["streams"][0]["nb_read_frames"])


def _get_video_metadata(source_file: str) -> Dict:
    """Extract video metadata using ffprobe"""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,avg_frame_rate,duration",
        "-of",
        "json",
        source_file,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)["streams"][0]

    # Try to calculate native fps from avg_frame_rate first
    try:
        num, den = map(int, data["avg_frame_rate"].split("/"))
        if den > 0:
            native_fps = num / den
        else:
            native_fps = 0.0
    except (ValueError, ZeroDivisionError):
        native_fps = 0.0

    # If avg_frame_rate calculation failed, try calculating from frame count and duration
    if native_fps == 0.0:
        duration = float(data["duration"])
        total_frames = _count_frames(source_file)
        native_fps = round(total_frames / duration, 2)

    return {
        "width": int(data["width"]),
        "height": int(data["height"]),
        "native_fps": native_fps,
    }


def _calculate_avg_bitrate(index_data: str, segments: List[str]) -> Optional[float]:
    """
    Calculate average bitrate from HLS segments.
    Returns None if no valid segments found.
    """
    bitrates = []

    # Parse durations from index file
    durations = []
    for line in index_data.splitlines():
        if line.startswith("#EXTINF:"):
            try:
                duration = float(line.split(":")[1].split(",")[0])
                durations.append(duration)
            except (IndexError, ValueError):
                continue

    # Calculate bitrates for each segment
    for duration, segment in zip(durations, segments):
        try:
            if duration > 0:
                size = os.path.getsize(segment)
                # Convert bytes to bits and divide by duration to get bits per second
                bitrate = (size * 8) / duration
                bitrates.append(bitrate)
        except (OSError, ZeroDivisionError):
            continue

    # Calculate average bitrate if we have valid measurements
    if bitrates:
        return sum(bitrates) / len(bitrates)
    return None


def _extract_segments(source_file: str, dirs: Dict, segment_length: int) -> Dict:
    """
    Extract HLS segments in high and low quality
    Returns segment info and frame counts per segment
    """
    qualities = {
        "high": {"crf": 23, "gop": 15},
        "low": {
            "crf": 40,
            "gop": 15,
            "scale": "-2:'if(gt(ih,720),max(ceil(ih/4)*2,720),ih)'",
        },
    }

    bitrates = {}

    for quality, opts in qualities.items():
        quality_dir = dirs["segments_" + quality]
        segment_pattern = os.path.join(quality_dir, "%09d.ts")
        index_path = os.path.join(quality_dir, "index.m3u8")

        # Build ffmpeg command
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-v",
            "error",
            "-i",
            source_file,
            "-c:v",
            "libx264",
            "-crf",
            str(opts["crf"]),
            "-g",
            str(opts["gop"]),
            "-f",
            "hls",
            "-hls_time",
            str(segment_length),
            "-hls_list_size",
            "0",
            "-start_number",
            "0",
            "-hls_segment_filename",
            segment_pattern,
            "-vsync",
            "passthrough",
            "-max_muxing_queue_size",
            "1024",
        ]

        # Add scale filter for low quality
        if "scale" in opts:
            cmd.extend(["-vf", f"scale={opts['scale']}"])

        cmd.append(index_path)

        subprocess.run(cmd, check=True)

        # Read index file and calculate bitrate
        with open(index_path) as f:
            index_data = f.read()
            segments = sorted(Path(quality_dir).glob("*.ts"))
            bitrate = _calculate_avg_bitrate(index_data, [str(s) for s in segments])
            bitrates[quality] = bitrate

    return {"bitrates": bitrates}


def _extract_thumbnail(source_file: str, output_path: str, total_frames: int) -> str:
    """Extract thumbnail from middle frame"""
    middle_frame = total_frames // 2

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-v",
        "error",
        "-i",
        source_file,
        "-vf",
        f"select=gte(n\\,{middle_frame}),scale=w=356:h=200:force_original_aspect_ratio=decrease",
        "-vframes",
        "1",
        "-y",
        output_path,
    ]

    subprocess.run(cmd, check=True)
    return output_path


def _get_frames_timestamps(source_file: str) -> List[float]:
    """Get frame timestamps using ffmpeg showinfo filter"""
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-v",
        "info",
        "-i",
        source_file,
        "-vsync",
        "passthrough",
        "-vf",
        "showinfo",
        "-f",
        "null",
        "-",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Parse timestamps from stderr
    frames = []
    for line in result.stderr.splitlines():
        if "pts_time:" in line:
            pts_time = line.split("pts_time:")[1].split()[0]
            frames.append(float(pts_time))

    return frames


def _extract_frames(source_file: str, output_dir: str, downsampling_step: float):
    """Extract frames using ffmpeg with optional downsampling"""
    frame_pattern = os.path.join(output_dir, "%09d.png")

    if downsampling_step > 1:
        # Use select filter to precisely control what frames are extracted
        # This matches the frame selection logic in the manifest
        select_expr = f"select='eq(trunc(trunc((n+1)/{downsampling_step})*{downsampling_step})\\,n)'"
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-v",
            "error",
            "-i",
            source_file,
            "-start_number",
            "0",
            "-vsync",
            "passthrough",
            "-vf",
            select_expr,
            "-f",
            "image2",
            frame_pattern,
        ]
    else:
        # Extract all frames when no downsampling needed
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-v",
            "error",
            "-i",
            source_file,
            "-start_number",
            "0",
            "-vsync",
            "passthrough",
            "-f",
            "image2",
            frame_pattern,
        ]

    subprocess.run(cmd, check=True)


def _get_segment_frame_counts(segments_dir: str) -> List[int]:
    """Get frame counts for each segment in order"""
    segments = sorted(Path(segments_dir).glob("*.ts"))
    segment_frame_counts = []
    for segment in segments:
        count = _count_frames(str(segment))
        segment_frame_counts.append(count)
    return segment_frame_counts


def _create_frames_manifest(
    source_file: str, segments_dir: str, downsampling_step: float, manifest_path: str
) -> Dict:
    """
    Create frames manifest mapping frames to segments
    Format: FRAME_NO_IN_SEGMENT:SEGMENT_NO:VISIBILITY_FLAG:TIMESTAMP
    """
    frames_timestamps = _get_frames_timestamps(source_file)
    segment_frame_counts = _get_segment_frame_counts(segments_dir)

    file_lines = []
    visible_frames = 0
    frame_no = 0
    segment_no = 0
    frame_no_segment = 0

    for frame_timestamp in frames_timestamps:
        # Check if frame should be visible based on downsampling
        next_visible_frame = int(visible_frames * downsampling_step)
        visibility = 1 if frame_no == next_visible_frame else 0

        if visibility == 1:
            visible_frames += 1

        # Move to next segment if current is full
        if frame_no_segment >= segment_frame_counts[segment_no]:
            segment_no += 1
            frame_no_segment = 0

        # Create manifest line
        line = f"{frame_no_segment}:{segment_no}:{visibility}:{frame_timestamp}"
        file_lines.append(line)

        frame_no += 1
        frame_no_segment += 1

    with open(manifest_path, "w") as f:
        f.write("\n".join(file_lines))

    return {"visible_frames": visible_frames, "total_frames": frame_no}


def _get_hls_index_with_storage_urls(segments_dir: str, storage_key_prefix: str) -> str:
    """
    Replaces relative paths in HLS index file by storage keys.
    """
    index_path = os.path.join(segments_dir, "index.m3u8")
    with open(index_path, "r") as f:
        content = f.read()
        return re.sub(
            r"^(.*\.ts)$",
            lambda m: f"{storage_key_prefix}/{m.group(1)}",
            content,
            flags=re.MULTILINE,
        )


def _maybe_extract_audio_peaks(source_file: str, output_dir: str) -> Optional[str]:
    """
    Extract audio peaks from video file and gzip the result.
    Returns path to the gzipped peaks file if audio stream exists, None otherwise.
    """
    # First check if audio stream exists
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=codec_type",
        "-of",
        "json",
        source_file,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)

    if not data.get("streams"):
        console.print("No audio streams found")
        return None

    raw_output_path = os.path.join(output_dir, "audio_peaks.raw")
    gzipped_output_path = os.path.join(output_dir, "audio_peaks.gz")

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-v",
        "error",
        "-i",
        source_file,
        "-map",
        "0:a:0",
        "-ac",
        "1",
        "-af",
        "aresample=1000,asetnsamples=1",
        "-f",
        "u8",
        raw_output_path,
    ]

    try:
        subprocess.run(cmd, check=True)
        # Gzip the output file
        with open(raw_output_path, "rb") as f_in:
            with gzip.open(gzipped_output_path, "wb") as f_out:
                f_out.writelines(f_in)
        # Remove the raw file
        os.remove(raw_output_path)
        return gzipped_output_path
    except (subprocess.CalledProcessError, OSError):
        console.print("Failed to extract audio peaks")
        if os.path.exists(raw_output_path):
            os.remove(raw_output_path)
        if os.path.exists(gzipped_output_path):
            os.remove(gzipped_output_path)
        return None


def extract_artifacts(
    source_file: str,
    output_dir: str,
    storage_key_prefix: str,
    *,
    fps: float = 0.0,
    segment_length: int = 2,
    repair: bool = False,
) -> Dict:
    """
    Extracts video artifacts including segments, frames, thumbnail for
    read-only registration in the Darwin platform.

    Args:
        source_file: Path to source video file
        output_dir: Directory to store generated artifacts
        storage_key_prefix: Prefix for storage keys
        fps: Desired frames per second (0.0 for native fps), defaults to 0.0
        segment_length: Length of each segment in seconds, defaults to 2
        repair: If True, attempt to repair video if errors are detected, defaults to False

    Returns:
        Dict containing metadata and paths to generated artifacts

    Raises:
        FileNotFoundError: If source_file does not exist
    """
    if not os.path.exists(source_file):
        raise FileNotFoundError(f"Source video file not found: {source_file}")

    _check_ffmpeg_version()
    dirs = _create_directories(output_dir)

    repaired = False
    if repair:
        repaired, source_file = _maybe_repair_video(source_file, dirs["base_dir"])

    storage_key_prefix = storage_key_prefix.strip("/")

    console.print("\nExtracting video metadata...")

    metadata = _get_video_metadata(source_file)
    native_fps = float(metadata["native_fps"])
    downsampling_step = round(max(native_fps / fps, 1.0), 4) if fps > 0 else 1.0
    source_file_size = os.path.getsize(source_file)

    console.print(f"\nVideo resolution: {metadata['width']}x{metadata['height']}")
    console.print(f"Native FPS: {native_fps}")
    console.print(f"Downsampling step: {downsampling_step}")
    console.print(f"Source file size: {source_file_size} bytes")

    console.print("\nExtracting video segments...")

    segments_metadata = _extract_segments(
        source_file=source_file, dirs=dirs, segment_length=segment_length
    )

    console.print("\nExtracting frames...")

    _extract_frames(source_file, dirs["sections"], downsampling_step)

    console.print("\nCreating frames manifest...")

    manifest_metadata = _create_frames_manifest(
        source_file=source_file,
        segments_dir=dirs["segments_high"],
        downsampling_step=downsampling_step,
        manifest_path=os.path.join(dirs["base_dir"], "frames_manifest.txt"),
    )

    console.print("\nExtracting thumbnail...")

    _extract_thumbnail(
        source_file=source_file,
        output_path=os.path.join(dirs["base_dir"], "thumbnail.jpg"),
        total_frames=manifest_metadata["total_frames"],
    )

    console.print("\nExtracting audio peaks...")

    _maybe_extract_audio_peaks(source_file, dirs["base_dir"])

    console.print("\nProcessing segment indices...")

    hq_hls_index = _get_hls_index_with_storage_urls(
        dirs["segments_high"], f"{storage_key_prefix}/segments/high"
    )
    lq_hls_index = _get_hls_index_with_storage_urls(
        dirs["segments_low"], f"{storage_key_prefix}/segments/low"
    )

    console.print("\nSaving metadata...")

    source_file_name = os.path.basename(source_file)

    # Prepare final metadata
    result_metadata = {
        "repaired": repaired,
        "source_file": source_file,
        "storage_key_prefix": storage_key_prefix,
        "registration_payload": {
            "type": "video",
            "width": metadata["width"],
            "height": metadata["height"],
            "native_fps": metadata["native_fps"],
            "fps": fps,
            "visible_frames": manifest_metadata["visible_frames"],
            "total_frames": manifest_metadata["total_frames"],
            # After item registration with this payload,
            # DARWIN will use storage keys from HLS indexes and fields defined below
            # to create signed URLs and fetch files from storage.
            # Therefore, the storage key must be correct.
            "hls_segments": {
                "high_quality": {
                    "index": hq_hls_index,
                    "bitrate": segments_metadata["bitrates"]["high"],
                },
                "low_quality": {
                    "index": lq_hls_index,
                    "bitrate": segments_metadata["bitrates"]["low"],
                },
            },
            "storage_key": f"{storage_key_prefix}/{source_file_name}",
            "storage_sections_key_prefix": f"{storage_key_prefix}/sections",
            "storage_frames_manifest_key": f"{storage_key_prefix}/frames_manifest.txt",
            "storage_thumbnail_key": f"{storage_key_prefix}/thumbnail.jpg",
            "total_size_bytes": source_file_size,
            "name": source_file_name,
            "path": "/",
        },
    }

    # Add audio peaks key if audio was extracted
    # Must be uploaded with Content-Encoding gzip
    audio_peaks_path = os.path.join(dirs["base_dir"], "audio_peaks.gz")
    if os.path.exists(audio_peaks_path):
        result_metadata["registration_payload"][
            "storage_audio_peaks_key"
        ] = f"{storage_key_prefix}/audio_peaks.gz"

    with open(os.path.join(dirs["base_dir"], "metadata.json"), "w") as f:
        json.dump(result_metadata, f, indent=2)

    return result_metadata
