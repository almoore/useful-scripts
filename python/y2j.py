#!/usr/bin/env python3
"""
YAML for command line.
"""

import sys
import os.path
import yaml
import json
import re

EXNAME = os.path.basename(sys.argv[0])

USAGE = """\
Usage:
    %(exname)s (-h|--help)
    %(exname)s [-y|--yaml] ACTION KEY [DEFAULT]
""" % {"exname": EXNAME}

def stderr(msg):
    """Convenience function to write short message to stderr."""
    sys.stderr.write(msg)
    
def stdout(value):
    """Convenience function to write short message to stdout."""
    sys.stdout.write(value)


def die(msg, errlvl=1, prefix="Error: "):
    """Convenience function to write short message to stderr and quit."""
    stderr("%s%s\n" % (prefix, msg))
    sys.exit(errlvl)


def magic_dump(value):
    """Returns a representation of values directly usable by bash.
    Literal types are printed as-is (avoiding quotes around string for
    instance). But complex type are written in a YAML useable format.
    """
    return value if isinstance(value, SIMPLE_TYPES) \
        else json.dump(value, indent=2)
        

def yaml_dump(value):
    """Returns a representation of values directly usable by bash.
    Literal types are quoted and safe to use as YAML.
    """
    return yaml.dump(value, default_flow_style=False)


def json_dump(value):
    """Returns a representation of values directly usable by bash.
    Literal types are quoted and safe to use as json.
    """
    return json.dumps(value, indent=2)
    

def main(args):  ## pylint: disable=too-many-branches
    """Entrypoint of the whole application"""
    
    dump = magic_dump
    
    # if len(args) == 0:
    #     stderr("Error: Bad number of arguments.\n")
    #     die(USAGE, errlvl=1, prefix="")

    # if len(args) == 1 and args[0] in ("-h", "--help"):
    #     stdout(HELP)
    #     exit(0)
    
    contents = yaml.safe_load(sys.stdin)
    print(json_dump(contents))
    
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))