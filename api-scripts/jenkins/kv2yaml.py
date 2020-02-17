#!/usr/bin/env python
import os
import yaml
import base64
import sys
import six

usage = '''
yaml2consul INPUT_FILE OUTPUT_FILE
'''

debug = False

class kv2YamlMergeError(Exception):
    pass


def help():
    print(usage)

def get(c, k, default=None):
    try:
        return c[k]
    except (IndexError, KeyError, TypeError):
        return default


def is_int(s):
    if type(s) is not str:
        return False
    try: 
        int(s)
        return True
    except ValueError:
        return False


def assoc(d, k ,v):
    if d is None:
        d = {}
    if debug:
        print("v({type}) = {val}".format(type=type(v),val=v))
    if is_int(v):
        d[k] = int(v)
    else:
        d[k] = v
    return d

def assoc_in(d, key_path, v):
    if not key_path:
        raise ValueError("Cannot provide empty key path")
    key, rest = key_path[0], key_path[1:]
    if not rest:
        return assoc(d, key, v)
    else:
        return assoc(d, key, assoc_in(get(d, key), rest, v))

def data_merge(a, b):
    """merges b into a and return merged result
    NOTE: tuples and arbitrary objects are not handled as it is totally ambiguous what should happen"""
    key = None
    try:
        if a is None or isinstance(a, (six.string_types, float, six.integer_types)):
            # border case for first run or if a is a primitive
            a = b
        elif isinstance(a, list):
            # lists can be only appended
            if isinstance(b, list):
                # merge lists
                a.extend(b)
            else:
                # append to list
                a.append(b)
        elif isinstance(a, dict):
            # dicts must be merged
            if isinstance(b, dict):
                for key in b:
                    if key in a:
                        a[key] = data_merge(a[key], b[key])
                    else:
                        a[key] = b[key]
            else:
                raise k2YamlMergeError('Cannot merge non-dict "%s" into dict "%s"' % (b, a))
        else:
            raise k2YamlMergeError('NOT IMPLEMENTED "%s" into "%s"' % (b, a))
    except TypeError as e:
        raise k2YamlMergeError('TypeError "%s" in key "%s" when merging "%s" into "%s"' % (e, key, b, a))
    return a


def expand_key(key, value):
    path = key.split("/")
    return assoc_in({}, path, value)

def expand_keys(d):
    try:
        expanded = [expand_key(k, v) for k, v in d]
        acc = {}
        for exp in expanded:
            acc = data_merge(acc, exp)
        return acc
    except ValueError as e:
        print(e)
        print(d)

def main():
    if len(sys.argv) != 3:
        help()
        exit(1)
    data = {}
    with open(sys.argv[1]) as f:
        data = f.read()
    lines = []
    for a in data.split('\n'):
        if a:
            i = a.split(' ')
            tup = (i[0], ' '.join(i[1:]))
            lines.append(tup)
    with open(sys.argv[2], 'w') as f:
        output = yaml.safe_dump(expand_keys(lines), indent=2, default_flow_style=False)
        if debug:
            print(output)
        f.write(output)
    

if __name__ == '__main__':
    main()
