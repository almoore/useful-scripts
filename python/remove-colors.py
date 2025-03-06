#!/usr/bin/env python3
import re
import sys
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument

    
def remove_colors(data):
    color_sym_re = re.compile(rb'\x1b\[[0-9]+m')
    return color_sym_re.sub(b'', data)


def main():
    if len(sys.argv) < 2:
        print('Supply a file name.')
        sys.exit(1)
    elif len(sys.argv) == 3:
        filename_out = sys.argv[2]
    else:
        filename = sys.argv[1]
    try:
        with open(filename, 'rb') as fsi:
            data = fsi.read()
        # Substitute in a blank string
        data_out = remove_colors(data)
        with open(filename, 'wb') as fso:
            fso.write(data_out)
    except FileNotFoundError as e:
      print(e)
      sys.exit(1)
    
if __name__ == '__main__':
    main()
