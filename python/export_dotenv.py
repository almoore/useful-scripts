#!/usr/bin/env python3
import os, sys
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
