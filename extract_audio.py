import subprocess
from pathlib import Path
import argparse

def extract_audios(input_dir):
    input_path = Path(input_dir)
    if not input_path.exists() or not input_path.is_dir():
        print(f"Error: Directory '{input_dir}' does not exist.")
        return

    output_dir = input_path.parent / f"{input_path.name}_audios"
    output_dir.mkdir(exist_ok=True)

    videos = list(input_path.glob("*.mp4"))
    if not videos:
        print(f"No .mp4 files found in {input_dir}")
        return

    print(f"Found {len(videos)} videos. Extracting audio...")

    for i, video_path in enumerate(videos):
        output_path = output_dir / f"{video_path.stem}.mp3"
        print(f"[{i+1}/{len(videos)}] Extracting audio from {video_path.name}...")
        
        # FFmpeg command to extract audio as a lightweight mp3
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn",              # Skip video
            "-acodec", "libmp3lame",
            "-q:a", "5",        # Moderate quality to keep file size very small
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print(f"  [✗] Failed to extract audio from {video_path.name}")

    print(f"\nDone! All audios saved to: {output_dir.resolve()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract audio from reels for Gemini.")
    parser.add_argument("folder", nargs="?", default="reels", help="Path to the folder containing .mp4 reels (default: reels)")
    args = parser.parse_args()
    
    extract_audios(args.folder)
