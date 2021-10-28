#!/usr/bin/env python3
import yaml
import sys


def main():
    data = yaml.safe_load(open(sys.argv[1]))
    output = yaml.dump(data["spec"]["values"])
    print(output)


if __name__ == "__main__":
    try:
        main()
    except IndexError:
        print(f"Usage: {sys.argv[0]} <helmrelease.yaml>")
    except OSError:
        print(f"Error: {sys.argv[1]} not found")
