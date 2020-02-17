#!/usr/bin/env python
import os
import yaml
import json
import base64
import sys
import argparse
usage = '''
yaml2consul YAML_FILE OUTPUT_JSON
'''
parser = argparse.ArgumentParser()
parser.add_argument('input_file', action='store', help='The yaml file to read from.')
parser.add_argument('output_file', action='store', help='The json file to write to.')
parser.add_argument('-p', '--prefix', action='store', help='The prefix to add as a consul path')
parser.add_argument('--debug', action='store_true')
args = parser.parse_args()
def get_nested(item, prefix=[], encode=True):
    if type(item) is dict:
        ret_vals = []
        for k, v in item.items():
            np = prefix + [ k ]
            ret = get_nested(v, prefix=np)
            if type(ret) is list:
                ret_vals += ret
            else:
                ret_vals.append(ret)
        return ret_vals
    else:
        ret = { 'key': '/'.join(prefix), 'flags': 0 }
        if encode:
            # encode and decode for type changes in python 2 and 3
            ret['value'] = base64.b64encode(str(item).encode('ascii')).decode('utf-8')
        else:
            ret['value']= item
        return ret
def main():
    data = {}
    with open(args.input_file) as f:
        data = yaml.safe_load(f)
    values = []
    for key, value in data.items():
        prefix = [key]
        if args.prefix:
            prefix = args.prefix.split('/') + [key]
        nd = get_nested(value, prefix=prefix)
        if args.debug:
            print("{} {}".format(type(nd),nd))
        if type(nd) is list:
            values += nd
        else:
            values.append(nd)
    consul_data = values
    with open(args.output_file, 'w') as f:
        json.dump(consul_data, f, indent=2, sort_keys=True)
if __name__ == '__main__':
    main()
