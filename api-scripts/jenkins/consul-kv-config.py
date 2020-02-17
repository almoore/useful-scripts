#!/usr/bin/python

import yaml
import sys
from consul_kv import Connection
import argparse

def parse_arguments(args):
    parser = argparse.ArgumentParser(description='Push consul keys to a particular keyspace')
    parser.add_argument('--token', metavar='TOKEN', type=str,
            help='Consul token to use', default="")
    parser.add_argument('--endpoint', metavar='URL', type=str,
            required=True,
            default='http://localhost:8500/v1/',
            help='Consul endpoint URL')
    parser.add_argument('--keyspace', metavar='KEY/SPACE', type=str,
            required=True,
            help='Keyspace to work in')
    parser.add_argument('--conffile', metavar='conf/file.yaml', type=argparse.FileType('r')
            required=True,
            help='Keyspace to work in')
    args = parser.parse_args()
    return args

def prefix_key_dictionary(keyspace, conf):
    clean_keyspace = keyspace.rstrip('/').lstrip('/')
    keyspace_parts = re.split(r'/+', clean_keyspace)
    keyspace_parts.reverse()
    building_dict = {}
    for part in keyspace_parts:
        building_dict = {part: building_dict}
    return building_dict

def configure_keyspace(endpoint, keyspace, conffile, token):
    consul_connection = Connection(endpoint=endpoint)
    consul_connection.delete(keyspace,recurse=True)
    with open(conffile, 'r',
            encoding='utf-8', errors='replace') as conf_handle:
        conf = yaml.safe_load(conf_handle)
        conf = prefix_key_dictionary(keyspace, conf)
    with Connection(endpoint=endpoint) as conn:
        conn.delete(keyspace, recurse=True)
        conn.put_dict(conf)

def main(args):
    parsed_args = parse_arguments(args)
    configure_keyspace(args.endpoint,
        args.keyspace,
        args.conffile,
        args.token)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
