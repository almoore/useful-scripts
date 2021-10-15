#!/usr/bin/env python3
import yaml
import os
import sys

with open('resources.yaml') as f:
  data = yaml.safe_load(f)

for o in data["items"]:
  k = o["kind"]
  n = o["metadata"]["name"]
  ns = o["metadata"].get("namespace", "cluster")
  d = f'{ns}/{k}'
  os.makedirs(d, exist_ok=True)
  fn = f'{d}/{n}.yaml'
  print(f'Creating: {fn}')
  with open(fn, 'w') as f:
    yaml.safe_dump(o, f)
