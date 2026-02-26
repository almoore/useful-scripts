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
    result = subprocess.run(cmd)
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
