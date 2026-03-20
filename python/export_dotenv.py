#!/usr/bin/env python3
"""Export environment variables from a .env file as shell export statements.

Usage: export-dotenv [FILE]
  FILE defaults to .env in the current directory.
  Pipe to eval: eval "$(export-dotenv .env.production)"
"""
import os, sys

if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
    print(__doc__.strip())
    sys.exit(0)

from dotenv import load_dotenv, find_dotenv, dotenv_values
dotenv_as_dict = {}
if len(sys.argv) == 2:
    dotenv_path = sys.argv[1]
else:
    dotenv_path = '.env'
print(f'# Load values from {dotenv_path}')
dotenv_as_dict = dotenv_values(dotenv_path, verbose=True)
for k, v in dotenv_as_dict.items():
    print(f'export {k}={v}')
