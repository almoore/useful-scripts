#!/usr/bin/env python3
import os
import tempfile
import yaml
import argparse
from subprocess import Popen, PIPE

release_data = None


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    YELLOW = "\033[33m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("release", help="The helm release file to extract values from")
    parser.add_argument(
        "--name",
        help="The release name to use this will default to what is in the release file",
    )
    parser.add_argument(
        "--namespace",
        help="The namespace to use this will default to what is in the release file",
    )
    parser.add_argument(
        "--chart",
        default="anthemai-helm/hos-generic",
        help="The helm chart to use defaults to anthemai-helm/hos-generic",
    )
    parser.add_argument("--version", help="The helm chart version to use")
    return parser.parse_args()


def run(command):
    """
    Create a generator to a shell command with async output yielded
    :param command:
    :return:
    """
    process = Popen(command, stdout=PIPE, shell=True)
    while True:
        line = process.stdout.readline().rstrip()
        if not line:
            break
        yield line.decode("utf-8")


def print_context(ns=None):
    ctx = list(run("kubectl config current-context"))[0]
    if ns is None:
        ns = list(
            run(
                """kubectl config view -o=jsonpath='{.contexts[?(@.name=="_ctx")].context.namespace}'""".replace(
                    "_ctx", ctx
                )
            )
        )[0]
    print(
        f"{bcolors.BOLD}{bcolors.OKGREEN}Using the context {ctx}, namespace {ns}{bcolors.ENDC}"
    )


def get_release_data(file_name):
    with open(file_name) as fs:
        return yaml.safe_load(fs)


def get_values(data):
    return yaml.dump(data["spec"]["values"])


def get_release_name(data):
    return data.get("spec", {}).get("releaseName")


def get_chart_version(data):
    return data.get("spec", {}).get("chart", {}).get("version")


def get_namespace(data):
    return data.get("metadata", {}).get("namespace")


def main():
    args = parse_args()
    data = get_release_data(args.release)
    # Get all the values
    name = get_release_name(data) if args.name is None else args.name
    if name is None:
        name = args.release.replace(".yaml", "")
    # Get namespace
    ns_cmd = ""
    namespace = get_namespace(data) if args.namespace is None else args.namespace
    if namespace is not None:
        ns_cmd = f"-n {namespace}"
    # Get Version
    v_cmd = ""
    version = get_chart_version(data) if args.version is None else args.version
    print(f"version {version}")
    if version is not None:
        v_cmd = f"--version {version}"
    fd, values_file = tempfile.mkstemp()
    # use a context manager to open the file at that path and close it again
    with open(values_file, "w") as fs:
        fs.write(get_values(data))
    command = f"helm diff -C 3 upgrade {name} {args.chart} {v_cmd} {ns_cmd} --values {values_file}"
    print(f"{bcolors.WARNING}Running: {command}{bcolors.ENDC}")
    print_context(ns=namespace)
    lines = list(run(command))
    if not len(lines):
        print("NO CHANGES")
    for line in lines:
        print(line)
    print_context(ns=namespace)
    # close the file descriptor
    os.close(fd)


if __name__ == "__main__":
    main()
