#!/usr/bin/env python3
"""
Download YouTube videos as MP3 audio files.

Usage:
    python download-youtube-audio.py URL [URL ...]
    python download-youtube-audio.py -o ~/Music URL
    python download-youtube-audio.py --bitrate 320 URL

Requires:
    - yt-dlp: pip install yt-dlp
    - ffmpeg: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)
"""

import argparse
import subprocess
import sys


def download_audio(url, output_dir=".", bitrate="192"):
    """Download a YouTube URL as an MP3 file."""
    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", f"{bitrate}K",
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
        description="Download YouTube videos as MP3 audio files.",
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
        "--bitrate", default="192",
        help="Audio bitrate in kbps (default: 192).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    failures = 0
    for url in args.urls:
        rc = download_audio(url, args.output_dir, args.bitrate)
        if rc != 0:
            failures += 1
    if failures:
        print(f"\n{failures} of {len(args.urls)} download(s) failed.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
