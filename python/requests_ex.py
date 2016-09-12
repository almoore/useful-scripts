#!/usr/bin/env python
import requests

def download_binary(path):
    
    r = requests.get(path)
    
    with open('test.rpm', 'wb') as f:
        f.write(r.content)
