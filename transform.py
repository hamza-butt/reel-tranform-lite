import subprocess
import argparse
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# FFprobe utilities
# ---------------------------------------------------------------------------

def get_video_duration(video_path):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return None

def get_audio_sample_rate(video_path):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return int(result.stdout.strip())
    except Exception:
        return 44100

def has_audio_stream(video_path):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return "audio" in result.stdout
    except Exception:
        return True

# ---------------------------------------------------------------------------
# Filter builders
# ---------------------------------------------------------------------------

def build_video_filters(zoom, saturation, gamma, tint, vignette, noise, speed):
    filters = [
        f"crop=iw*{zoom}:ih*{zoom}",
        f"eq=saturation={saturation}:gamma={gamma}",
        # "hflip",  # disabled until subtitle-safe flip plan is ready
    ]
    if tint == "warm":
        filters.append("colorbalance=rs=0.03:gs=0.01:bs=-0.02")
    elif tint == "cool":
        filters.append("colorbalance=rs=-0.02:gs=0.00:bs=0.03")
    if vignette > 0:
        filters.append(f"vignette=angle={vignette}")
    if noise > 0:
        filters.append(f"noise=alls={noise}:allf=t+u")
    filters.append(f"setpts=PTS/{speed}")
    return ",".join(filters)


def build_audio_filter(speed, pitch, sample_rate):
    if pitch != 1.0:
        adjusted_rate = int(sample_rate * pitch)
        return f"asetrate={adjusted_rate},atempo={speed / pitch},aresample={sample_rate}"
    return f"atempo={speed}"



# ---------------------------------------------------------------------------
# Metadata randomizers
# ---------------------------------------------------------------------------

def _random_creation_time() -> str:
    """Random ISO timestamp within the past 30 days — looks like a real recording date."""
    offset = timedelta(
        days=random.randint(1, 30),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    dt = datetime.now(timezone.utc) - offset
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000000Z")


def _random_encoder_string() -> str:
    """Realistic FFmpeg Lavf version string — varies per video to avoid a fixed fingerprint."""
    major = random.randint(58, 61)
    minor = random.randint(20, 99)
    patch = random.randint(100, 200)
    return f"Lavf{major}.{minor}.{patch}"


# ---------------------------------------------------------------------------
# FFmpeg command builder
# ---------------------------------------------------------------------------

def build_ffmpeg_cmd(video_path, output_path, vf_str, af_str, has_audio):
    cmd = ["ffmpeg", "-y", "-i", str(video_path)]
    cmd.extend(["-vf", vf_str])
    if has_audio:
        cmd.extend(["-af", af_str])
    cmd.extend([
        "-c:v", "libx264",
        "-crf", "23",
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "128k",
        # Strip every field from the source file
        "-map_metadata", "-1",
        # Prevent FFmpeg from auto-writing its own encoder/version tags
        "-fflags", "+bitexact",
        "-flags:v", "+bitexact",
        "-flags:a", "+bitexact",
        # Inject randomized metadata so the file looks like a genuine new recording
        "-metadata", f"creation_time={_random_creation_time()}",
        "-metadata", f"encoder={_random_encoder_string()}",
        "-metadata", "comment=",
        str(output_path),
    ])
    return cmd


# ---------------------------------------------------------------------------
# Single-video transformer
# ---------------------------------------------------------------------------

def transform_video(video_path, output_path, vf_str, speed, pitch):
    has_audio   = has_audio_stream(video_path)
    sample_rate = get_audio_sample_rate(video_path) if has_audio else 44100
    af_str      = build_audio_filter(speed, pitch, sample_rate)
    cmd         = build_ffmpeg_cmd(video_path, output_path, vf_str, af_str, has_audio)
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------------------------------------------------------------------------
# Filter progress logger
# ---------------------------------------------------------------------------

def log_filters(video_num, total, video_name, zoom, saturation, gamma, tint,
                 vignette, noise, speed, pitch):
    print(f"\n  Filters for video {video_num}/{total} — {video_name}:", flush=True)
    print(f"    [✓] Crop / Zoom    : {zoom}  ({round((1 - zoom) * 100, 1)}% cropped)", flush=True)
    print(f"    [-] Horizontal Flip: disabled", flush=True)
    print(f"    [✓] Saturation     : {saturation}", flush=True)
    print(f"    [✓] Gamma          : {gamma}", flush=True)
    print(f"    [✓] Speed          : {speed}x", flush=True)
    if tint != "none":
        print(f"    [✓] Color Tint     : {tint}", flush=True)
    else:
        print(f"    [-] Color Tint     : disabled", flush=True)
    if vignette > 0:
        print(f"    [✓] Vignette       : {vignette}", flush=True)
    else:
        print(f"    [-] Vignette       : disabled (0)", flush=True)
    if noise > 0:
        print(f"    [✓] Noise / Grain  : {noise}", flush=True)
    else:
        print(f"    [-] Noise / Grain  : disabled (0)", flush=True)
    if pitch != 1.0:
        print(f"    [✓] Pitch Shift    : {pitch}x", flush=True)
    else:
        print(f"    [-] Pitch Shift    : disabled (1.0)", flush=True)


# ---------------------------------------------------------------------------
# Batch orchestrator
# ---------------------------------------------------------------------------

def process_videos(input_dir, zoom=0.98, speed=1.02, saturation=1.05, gamma=1.02,
                   noise=2, vignette=0.05, tint="warm", pitch=1.01):
    input_path = Path(input_dir)
    if not input_path.exists() or not input_path.is_dir():
        print(f"Error: Directory '{input_dir}' does not exist.")
        return

    output_dir = input_path.parent / "transformed_reels"
    output_dir.mkdir(exist_ok=True)

    videos = list(input_path.glob("*.mp4"))
    if not videos:
        print(f"No .mp4 files found in {input_dir}")
        return

    print(f"Found {len(videos)} videos. Beginning transformation...")

    vf_str = build_video_filters(zoom, saturation, gamma, tint, vignette, noise, speed)

    for i, video_path in enumerate(videos):
        video_num  = i + 1
        output_path = output_dir / f"{video_path.stem}_transformed.mp4"
        print(f"\n========================================================")
        print(f">>> CURRENTLY TRANSFORMING VIDEO: {video_path.name}")
        print(f">>> PROGRESS: {video_num} of {len(videos)}")
        print(f"========================================================")
        log_filters(video_num, len(videos), video_path.name,
                     zoom, saturation, gamma, tint, vignette, noise, speed, pitch)
        print(f"\n  Applying filters to video {video_num}/{len(videos)}...")
        try:
            transform_video(video_path, output_path, vf_str, speed, pitch)
            print(f"  [✓] All filters applied successfully to video {video_num}/{len(videos)}")
            print(f"  -> Saved as: {output_path.resolve()}")
        except subprocess.CalledProcessError:
            print(f"  [✗] ERROR: FFmpeg failed on video {video_num}/{len(videos)} ({video_path.name})")
        except FileNotFoundError:
            print("  [✗] ERROR: FFmpeg is not installed or not in your system PATH.")
            break

    print("\nTransformation complete! All files saved in:", output_dir.resolve())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transform short-form reels to bypass Unoriginal Content detection."
    )
    parser.add_argument("folder",       nargs="?", default="landlaben", help="Path to the folder containing .mp4 reels (default: landlaben)")
    parser.add_argument("--zoom",       type=float, default=0.98,  help="Zoom crop ratio (default 0.98 = 98%%)")
    parser.add_argument("--speed",      type=float, default=1.02,  help="Speed multiplier (default 1.02 = 2%% faster)")
    parser.add_argument("--saturation", type=float, default=1.05,  help="Saturation multiplier (default 1.05)")
    parser.add_argument("--gamma",      type=float, default=1.02,  help="Gamma/brightness multiplier (default 1.02)")
    parser.add_argument("--noise",      type=int,   default=2,     help="Temporal grain intensity, 0 to disable (default 2)")
    parser.add_argument("--vignette",   type=float, default=0.05,  help="Vignette angle, 0 to disable (default 0.05)")
    parser.add_argument("--tint",       choices=["none", "warm", "cool"], default="warm", help="Cinematic color tint (default warm)")
    parser.add_argument("--pitch",      type=float, default=1.01,  help="Pitch shift multiplier, 1.0 to disable (default 1.01)")

    args = parser.parse_args()

    process_videos(
        input_dir=args.folder,
        zoom=args.zoom,
        speed=args.speed,
        saturation=args.saturation,
        gamma=args.gamma,
        noise=args.noise,
        vignette=args.vignette,
        tint=args.tint,
        pitch=args.pitch,
    )
