#!/usr/bin/env python

"""
k8s_filter: Command-line YAML processor - kubernetes YAML documents

yaml_filter filters YAML documents to remove extra metadata that would prevent
clean back up and restore.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import argparse
# import subprocess
import json
from collections import OrderedDict
from datetime import datetime, date, time
import yaml


def clean_resource(resource):
    del_metadata_keys = [
        "creationTimestamp",
        "selfLink",
        "uid",
        "resourceVersion",
        "generation",
    ]
    del_annotations_keys = [
        "kubectl.kubernetes.io/last-applied-configuration",
        "control-plane.alpha.kubernetes.io/leader",
        "deployment.kubernetes.io/revision",
        "cattle.io/creator",
        "field.cattle.io/creatorId",
    ]
    if "status" in resource.keys():
        resource.__delitem__("status")

    if resource.get("metadata"):
        for key in del_metadata_keys:
            if key in resource["metadata"].keys():
                resource["metadata"].__delitem__(key)

        if resource["metadata"].get("annotations"):
            for key in del_annotations_keys:
                if key in resource["metadata"]["annotations"].keys():
                    resource["metadata"]["annotations"].__delitem__(key)

            if resource["metadata"]["annotations"] == {}:
                resource["metadata"].__delitem__("annotations")

        if resource["metadata"].get("namespace") == '':
            resource["metadata"].__delitem__("namespace")

        if resource["metadata"] == {}:
            resource.__delitem__("metadata")

    if resource["kind"] == "Service" and resource.get("spec"):
        if resource["spec"].get("clusterIP") is not None:
            resource["spec"].__delitem__("clusterIP")
        if resource["spec"] == {}:
            resource.__delitem__("spec")
    return resource


class Parser(argparse.ArgumentParser):
    def print_help(self):
        k8s_filter_help = argparse.ArgumentParser.format_help(self).splitlines()
        print("\n".join(["usage: k8s_filter [options] [YAML file...]"] + k8s_filter_help[1:] + [""]))


class OrderedLoader(yaml.SafeLoader):
    pass


class OrderedDumper(yaml.SafeDumper):
    pass


class JSONDateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (datetime, date, time)):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)


def construct_mapping(loader, node):
    loader.flatten_mapping(node)
    return OrderedDict(loader.construct_pairs(node))


def represent_dict_order(dumper, data):
    return dumper.represent_mapping("tag:yaml.org,2002:map", data.items())


def represent_str(dumper, data):
    if len(data.splitlines()) > 1:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


def decode_docs(jq_output, json_decoder):
    while jq_output:
        doc, pos = json_decoder.raw_decode(jq_output)
        jq_output = jq_output[pos + 1:]
        yield doc


def parse_unknown_tags(loader, tag_suffix, node):
    if isinstance(node, yaml.nodes.ScalarNode):
        return loader.construct_scalar(node)
    elif isinstance(node, yaml.nodes.SequenceNode):
        return loader.construct_sequence(node)
    elif isinstance(node, yaml.nodes.MappingNode):
        return construct_mapping(loader, node)


OrderedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
OrderedLoader.add_multi_constructor('', parse_unknown_tags)
OrderedDumper.add_representer(OrderedDict, represent_dict_order)
OrderedDumper.add_representer(str, represent_str)


# Detection for Python 2
USING_PYTHON2 = True if sys.version_info < (3, 0) else False


def get_parser(program_name):
    # By default suppress these help strings and only enable them in the specific programs.
    yaml_output_help, width_help = argparse.SUPPRESS, argparse.SUPPRESS

    if program_name == "k8s_filter":
        current_language = "YAML"
        json_output_help = "Give JSON output back"
        yaml_output_help = "Transcode output back into YAML and emit it"
        width_help = "When using --yaml-output, specify string wrap width"
    else:
        raise Exception("Unknown program name")

    description = __doc__.replace("k8s_filter", program_name).replace("YAML", current_language)
    parser_args = dict(prog=program_name, description=description, formatter_class=argparse.RawTextHelpFormatter)
    if sys.version_info >= (3, 5):
        parser_args.update(allow_abbrev=False)  # required to disambiguate options listed in _arg_spec
    parser = Parser(**parser_args)
    parser.add_argument("--yaml-output", "--yml-output", "-y", action="store_true", default=True, help=yaml_output_help)
    parser.add_argument("--json-output", "-j", action="store_false", dest="yaml_output", help=json_output_help)
    parser.add_argument("--width", "-w", type=int, help=width_help)
    # parser.add_argument("--version", action="version", version="%(prog)s {version}".format(version=__version__))
    parser.add_argument("files", nargs="*", type=argparse.FileType())
    return parser


def main(args=None, input_format="yaml", program_name="k8s_filter"):
    parser = get_parser(program_name)
    args, jq_args = parser.parse_known_args(args=args)
    if sys.stdin.isatty() and not args.files:
        return parser.print_help()

    # Allow for multiple or state ments args.yaml_output or args.toml_output
    converting_output = args.yaml_output

    try:
        input_streams = args.files if args.files else [sys.stdin]

        if converting_output:
            input_data = []
            for input_stream in input_streams:
                if input_format == "yaml":
                    input_data.extend(yaml.load_all(input_stream, Loader=OrderedLoader))
                else:
                    raise Exception("Unknown input format")
            for doc in input_data:
                doc = clean_resource(doc)
            if args.yaml_output:
                yaml.dump_all(input_data, stream=sys.stdout, Dumper=OrderedDumper,
                              width=args.width, allow_unicode=True, default_flow_style=False)
        else:
            if input_format == "yaml":
                for input_stream in input_streams:
                    for doc in yaml.load_all(input_stream, Loader=OrderedLoader):
                        doc = clean_resource(doc)
            else:
                raise Exception("Unknown input format")
        for input_stream in input_streams:
            input_stream.close()
    except Exception as e:
        # parser.exit("{}: Error running k8s_filter: {}: {}.".format(program_name, type(e).__name__, e))
        raise Exception(e)


if __name__ == "__main__":
    main()
