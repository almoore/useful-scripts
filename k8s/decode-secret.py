#!/usr/bin/env python3

import sys
import base64
import yaml
from collections import OrderedDict
from ast import literal_eval


class OrderedDumper(yaml.SafeDumper):
    pass


class PSS(str):
    pass


def represent_str(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


def represent_dict_order(dumper, data):
    return dumper.represent_mapping("tag:yaml.org,2002:map", data.items())


OrderedDumper.add_representer(OrderedDict, represent_dict_order)
OrderedDumper.add_representer(str, represent_str)

# Get input
input_stream = sys.stdin
input_data = yaml.safe_load(input_stream)
# Format and Dump output
for k, v in input_data.get("data", {}).items():
    d_v = base64.b64decode(v).decode('utf8')
    if len(d_v.splitlines()) > 1:
        d_v = '\n'.join([line.rstrip().replace('\t', '    ') for line in d_v.splitlines()])
    print(yaml.dump({k: d_v}, default_flow_style=False,
                    Dumper=OrderedDumper, allow_unicode=True))
