#!/usr/bin/env python
import collections
import base64
import gzip
import yaml

__version__ = "0.1.0"

from yamlmerge.yamlmerge import yaml_load, construct_ordereddict, \
    represent_ordereddict, represent_str


def parse_args():
    import optparse
    parser = optparse.OptionParser(usage="%prog [options] source...",
                                   description="Merge YAML data from given files, dir or file glob",
                                   version="%" + "prog %s" % __version__,
                                   prog="helm-decode-configmap-data")
    parser.add_option("--out-file", action="store", default=None,
                      help="The push the output to a file.")
    parser.add_option("--debug", dest="debug", action="store_true", default=False,
                      help="Enable debug logging [%default]")
    return parser.parse_args()
    
def yaml_dump():
    try:
        yaml.SafeLoader.add_constructor(u'tag:yaml.org,2002:omap', construct_ordereddict)
        yaml.SafeDumper.add_representer(collections.OrderedDict, represent_ordereddict)
        yaml.SafeDumper.add_representer(str, represent_str)
        if six.PY2:
            # pylint: disable=undefined-variable
            yaml.SafeDumper.add_representer(unicode, represent_str)
        print(yaml.safe_dump(yaml_load(
            args, defaultdata={}, unique_list=options.unique_list, key_on=options.key_on),
            indent=2, default_flow_style=False, canonical=False))
    except Exception as e:
        parser.error(e)


def main():
    # setup
    options, args = parse_args()
    if options.debug:
        logger = logging.getLogger()
        loghandler = logging.StreamHandler()
        loghandler.setFormatter(logging.Formatter('yamlmerge: %(levelname)s: %(message)s'))
        logger.addHandler(loghandler)
        logger.setLevel(logging.DEBUG)

    if not args:
        parser.error("Need at least one argument")
    # get data
    cm = yaml_load(args)
    data = cm['data']['release']
    z = base64.b64decode(data)
    b = gzip.decompress(z)
    ascii_sym_re = re.compile(rb'[\x00-\x09\x0b-\x1f\x7f-\xff]', re.DOTALL|re.MULTILINE)
    exclude = [chr(c).encode('ascii') for c in range(0,31)]
    exclude.remove(b'\n')
    exclude.remove(b'\r')
    exclude.remove(b'\t')
    o = bytes([b[i] for i in range(0, len(b)) if b[i:i+1] not in exclude and b[i]<128])
    if options.out_file is None:
        print(o.decode('utf-8'))
    else:
        with open(options.out_file, 'wb') as fs:
            fs.write(o)
    
    
if __name__ == '__main__':
    main()
