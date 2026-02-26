#!/usr/bin/env python3
"""
Remove ANSI color/escape codes from files.

Usage:
    python remove-colors.py input.log
    python remove-colors.py input.log -o cleaned.log
"""
import re
import sys
import argparse


def remove_colors(data):
    color_sym_re = re.compile(rb'\x1b\[[0-9;]*m')
    return color_sym_re.sub(b'', data)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Remove ANSI color/escape codes from files.",
    )
    parser.add_argument("input", help="Input file to strip colors from.")
    parser.add_argument("-o", "--output",
                        help="Output file (default: overwrite input file in-place).")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        with open(args.input, 'rb') as f:
            data = f.read()
        data_out = remove_colors(data)
        output_path = args.output or args.input
        with open(output_path, 'wb') as f:
            f.write(data_out)
        print(f"Wrote cleaned output to {output_path}")
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
