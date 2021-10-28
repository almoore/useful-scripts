import base64
import gzip
import yaml
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("secret", help="The helm secret file to extract values from")
    return parser.parse_args()


def get_release_data(f):
    data = yaml.safe_load(open(f))
    zdata = base64.b64decode(base64.b64decode(data["data"]["release"]))
    return yaml.safe_load(gzip.decompress(zdata).decode("utf-8"))


def main():
    args = parse_args()
    data = get_release_data(f = args.secret)
    print(yaml.safe_dump(data))


if __name__ == "__main__":
    main()
