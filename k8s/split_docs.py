#!/usr/bin/env python3
import os
import sys
import yaml


def load_docs(path):
    path = os.path.expanduser(path)
    fl = [f for f in os.listdir(path) if f.endswith('.yaml')]
    all_docs = []
    for f in fl:
        with open(os.path.expanduser(os.path.join(path, f)), "r") as fd:
            docs = list(yaml.load_all(fd))
            n = len(docs)
            all_docs.extend(docs)
            print(f"Found {n} documents in {f}")
    return all_docs


def get_name(doc):
    return doc.get('metadata').get('name')


def get_kind(doc):
    return doc.get('kind')


def write_docs(docs, path):
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        os.makedirs(path)
    for d in docs:
        if d is None:
            continue
        name = get_name(d).lower()
        kind = get_kind(d).lower()
        if not (name or kind):
            continue
        fp = os.path.join(path, f"{name}.{kind}.yaml")
        with open(fp, 'w') as fs:
            yaml.safe_dump(d, fs, indent=2, default_flow_style=False, canonical=False)
        print(f"Wrote: {fp}")


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {__file__} <input path> <output path>")
        exit()
    input = sys.argv[1]
    output = sys.argv[2]
    docs = load_docs(input)
    write_docs(docs, output)


if __name__ == "__main__":
    main()
