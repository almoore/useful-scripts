#!/usr/bin/env python3

import sys
import os
import git
import urllib.parse as up
from giturlparse import parse
import shutil

USER_BASE = os.path.expanduser('~')
REPO_BASE = os.path.join(USER_BASE, 'repos')


def get_os_path(git_remote):
    try:
        g = parse(git_remote)
        return os.path.join(REPO_BASE, g.host, g.owner, g.repo)
    except AttributeError:
        g = up.urlparse(git_remote)
        os_path = os.path.join(REPO_BASE, g.hostname, g.path[1:].replace('.git', ''))
        return os_path


def get_remote(path, name='origin'):
    repo = git.Repo(path)
    remote = repo.remote(name)
    return list(remote.urls)[0]


def walklevel(some_dir, level=1):
    some_dir = some_dir.rstrip(os.path.sep)
    assert os.path.isdir(some_dir)
    num_sep = some_dir.count(os.path.sep)
    for root, dirs, files in os.walk(some_dir):
        yield root, dirs, files
        num_sep_this = root.count(os.path.sep)
        if num_sep + level <= num_sep_this:
            del dirs[:]


def main():
    for root, dirs, files in walklevel('.'):
        for d in dirs:
            if os.path.exists(os.path.join(d, '.git')):
                r = get_remote(d)
                path = get_os_path(r)
                print("moving {} -> {}".format(d, path))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                shutil.move(d, path)


if __name__ == '__main__':
    main()