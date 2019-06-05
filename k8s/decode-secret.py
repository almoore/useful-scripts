#!/usr/bin/env python
import sys
import base64
import yaml

input_stream = sys.stdin
input_data = yaml.safe_load(input_stream)
for k, v in input_data.get("data", {}).items():
    d_v = base64.b64decode(v).decode('utf-8')
    print("{}: {}".format(k, repr( d_v)))
