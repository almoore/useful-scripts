#!/usr/bin/env python3
import os
import tempfile
import yaml
import argparse
from subprocess import Popen, PIPE, STDOUT

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
    parser.add_argument("-n", "--namespace",
                        help="The namespace to use this will default to what is in the release file")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress context and display short command summary")
    parser.add_argument("-k", "--kinds",
                        default="all,jobs,cronjobs,ingresses,endpoints,customresourcedefinitions,configmaps,secrets,configmap,events,pvc,serviceaccount,clusterrole,clusterrolebindings,storageclass,hrs",
                        help="comma seperated list of kinds of object to restrict the dump to example: configmaps,secrets,events,pods")
    parser.add_argument("-a", "--all", action="store_true", help="if present, collects from all namespace and kinds")
    parser.add_argument("-d", "--output-directory",
                        default="k8s-backup",
                        help="directory to output files; defaults to k8s-backup/<cluster-dir>")
    # parser.add_argument("-z", "--archive", action="store_true", help="if present, archives and removes the output directory")
    return parser.parse_args()


def run(command):
    """
    Create a generator to a shell command with async output yielded
    :param command:
    :return:
    """
    process = Popen(command, stdout=PIPE, stderr=STDOUT, shell=True)
    while True:
        line = process.stdout.readline().rstrip()
        if not line:
            break
        yield line.decode("utf-8")


def shell_out(command):
    """
    Create a generator to a shell command with async output yielded
    :param command:
    :return:
    """
    process = Popen(command, stdout=PIPE, stderr=STDOUT, shell=True)
    stdout_data = process.communicate()[0]
    return stdout_data, process.returncode


def get_context(ns=None):
    ctx = list(run("kubectl config current-context"))[0]
    if ns is None:
        ns = list(
            run(
                """kubectl config view -o=jsonpath='{.contexts[?(@.name=="_ctx")].context.namespace}'""".replace(
                    "_ctx", ctx
                )
            )
        )[0]
    return ctx, ns


def get_all_kinds():
    return ",".join(run("kubectl api-resources  -o name"))


def split_resources(data, quiet=False):
    print(f"{bcolors.OKGREEN}Splitting output and creating files{bcolors.ENDC}")
    for o in data["items"]:
        k = o.get("kind")
        if k is None:
            print(f"{bcolors.WARNING}Kind not found{bcolors.ENDC}")
            print(yaml.safe_dump(o))
            continue
        n = o["metadata"]["name"]
        ns = o["metadata"].get("namespace", "cluster")
        d = f'{ns}/{k}'
        os.makedirs(d, exist_ok=True)
        fn = f'{d}/{n}.yaml'
        if not quiet:
            print(f'{bcolors.BOLD}{bcolors.YELLOW}\t{fn}{bcolors.ENDC}')
        with open(fn, 'w') as f:
            yaml.safe_dump(o, f)


def main():
    args = parse_args()
    ns_cmd = ""
    namespace = args.namespace
    if args.all:
        ns_cmd = "-A"
        namespace = "All"
    elif namespace is not None:
        ns_cmd = f"--namespace {namespace}"

    ctx, ns = get_context(ns=namespace)
    if args.kinds is None:
        args.kinds = get_all_kinds()
    output_dir = os.path.join(args.output_directory, ctx)
    print(f"{bcolors.OKGREEN}Creating output in: {output_dir}{bcolors.ENDC}")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    os.chdir(output_dir)

    command = f"kubectl get {args.kinds} -o yaml {ns_cmd}"
    if not args.quiet:
        print(f"{bcolors.WARNING}Running: {command}{bcolors.ENDC}")
    else:
        print(
            f"{bcolors.WARNING}Gathering data from:{bcolors.ENDC}"
            f" {bcolors.HEADER}{ctx}/{ns} namespace{bcolors.ENDC}"
        )

    if not args.quiet:
        print(f"{bcolors.BOLD}{bcolors.OKGREEN}Using the context {ctx}, namespace {ns}{bcolors.ENDC}")
    text, ret = shell_out(command)
    resources = yaml.safe_load(text)
    split_resources(resources, args.quiet)


if __name__ == "__main__":
    main()
