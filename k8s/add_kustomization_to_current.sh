#!/usr/local/bin/env python3
import os, yaml

k_template = '''
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
'''


def main():
    data = yaml.safe_load(k_template)
    d, dirnames, r = next(os.walk('.'))
    r.sort()
    for rmf in ["kustomization.yaml", "tmp"]:
        if rmf in r:
            r.remove(rmf)
    data["resources"] = r
    with open("kustomization.yaml", 'w') as f:
        yaml.safe_dump(data, f)


if __name__ == "__main__":
    main()
