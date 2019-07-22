import json
import os
import sys
import requests
import docker
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('reg_name', action='store', help='The regisrty to query')
    parser.add_argument('--no-paginate', action='store_false', dest="paginate",
                        default=True, help='Turn of pagination of image tags')
    return parser.parse_args()
    

def get_client():
    global client
    if 'client' in globals() and isinstance(client, docker.client.DockerClient):
        return client
    else:
        print("Creating docker client from env")
        client = docker.from_env()
        return client


def get_tags(url, paginate=True):
    response = requests.get(url)
    if response.ok:
        data = response.json()
        tags = data.get('results', [])
        _next = data.get('next')
        if _next and paginate:
            print("Getting next: {}".format(_next)) 
            tags += get_tags(_next)
    else:
        tags = []
    return tags


def get_remote_id(name):
    client = get_client()
    print("Getting hash id for {}".format(name))
    rd = client.images.get_registry_data(name)
    return rd.id


def main():
    args = parse_args()
    reg_name = 'library/{}'.format(args.reg_name) if len(args.reg_name.split('/')) == 1 else args.reg_name
    url = 'https://hub.docker.com/v2/repositories/{}/tags/'.format(reg_name)
    tags = get_tags(url, paginate=args.paginate)
    images = [':'.join([reg_name, t['name']]) for t in tags]
    id_map = {i: get_remote_id(i) for i in images}
    print('images = {}'.format(json.dumps(id_map, indent=2)))

if __name__ == '__main__':
    main()
