#!/usr/bin/env python3
import os, yaml

k_template = '''
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
'''


def main():
    data = yaml.safe_load(k_template)
    dirpath, dirnames, filenames = next(os.walk('.'))
    for d in dirnames:
        r = os.listdir(d)
        r.sort()
        for rmf in ["kustomization.yaml", "tmp"]:
            if rmf in r:
                r.remove(rmf)
        data["resources"] = r
        with open(os.path.join(d, "kustomization.yaml"), 'w') as f:
            yaml.safe_dump(data, f)


if __name__ == "__main__":
    main()
