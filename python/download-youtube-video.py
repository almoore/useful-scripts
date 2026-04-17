#!/usr/bin/env python3
"""
Download YouTube videos in the highest available resolution.

Usage:
    python download-youtube-video.py URL [URL ...]
    python download-youtube-video.py -o ~/Videos URL
    python download-youtube-video.py --format mp4 URL

Requires:
    - yt-dlp: pip install yt-dlp
    - ffmpeg: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)
"""

import argparse
import subprocess
import sys


def check_dependencies():
    """Check that required CLI tools are available."""
    missing = []
    for tool in ("yt-dlp", "ffmpeg"):
        try:
            subprocess.run([tool, "--version"], capture_output=True, check=False)
        except FileNotFoundError:
            missing.append(tool)
    if missing:
        print(f"Error: missing required tool(s): {', '.join(missing)}", file=sys.stderr)
        print("Install with:", file=sys.stderr)
        for tool in missing:
            if tool == "yt-dlp":
                print("  pip install yt-dlp", file=sys.stderr)
            elif tool == "ffmpeg":
                print("  brew install ffmpeg  # macOS", file=sys.stderr)
                print("  apt install ffmpeg   # Linux", file=sys.stderr)
        sys.exit(1)


def download_video(url, output_dir=".", fmt="mp4"):
    """Download a YouTube video in the highest quality."""
    cmd = [
        "yt-dlp",
        "--format", f"bestvideo[ext={fmt}]+bestaudio[ext=m4a]/best[ext={fmt}]/best",
        "--merge-output-format", fmt,
        "--output", f"{output_dir}/%(title)s.%(ext)s",
        url,
    ]
    print(f"Downloading: {url}")
    try:
        result = subprocess.run(cmd)
    except FileNotFoundError:
        print("Error: yt-dlp not found. Install with: pip install yt-dlp", file=sys.stderr)
        return 1
    if result.returncode == 0:
        print(f"Downloaded successfully: {url}")
    else:
        print(f"Failed to download: {url}", file=sys.stderr)
    return result.returncode


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download YouTube videos in the highest available resolution.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "urls", nargs="+", metavar="URL",
        help="YouTube URL(s) to download.",
    )
    parser.add_argument(
        "-o", "--output-dir", default=".",
        help="Output directory (default: current directory).",
    )
    parser.add_argument(
        "--format", default="mp4", choices=["mp4", "mkv", "webm"],
        help="Output video format (default: mp4).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    check_dependencies()
    failures = 0
    for url in args.urls:
        rc = download_video(url, args.output_dir, args.format)
        if rc != 0:
            failures += 1
    if failures:
        print(f"\n{failures} of {len(args.urls)} download(s) failed.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
