#!/usr/bin/env python3
import sys
from ruamel.yaml import YAML

yaml = YAML()


def main():
    data = yaml.load(open(sys.argv[1]))
    yaml.dump(data["spec"]["values"], sys.stdout)


if __name__ == "__main__":
    try:
        main()
    except IndexError:
        print(f"Usage: {sys.argv[0]} <helmrelease.yaml>")
    except OSError:
        print(f"Error: {sys.argv[1]} not found")
