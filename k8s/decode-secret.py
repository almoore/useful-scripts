#!/usr/bin/env python

import sys
import base64
import yaml


def represent_str(dumper, data):
    # borrowed from http://stackoverflow.com/a/33300001
    if len(data.splitlines()) > 1:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


# Get input
input_stream = sys.stdin
input_data = yaml.safe_load(input_stream)
# Format and Dump output
yaml.SafeDumper.add_representer(str, represent_str)
for k, v in input_data.get("data", {}).items():
    d_v = base64.b64decode(v).decode('utf-8')
    print(yaml.safe_dump({k: d_v}, indent=2, default_flow_style=False, canonical=False))
