#!/usr/bin/env python3

import sys
import os
import urllib.parse as up
import shutil
import argparse
import logging
try:
    import git
    from giturlparse import parse
except ModuleNotFoundError:
    print("The modules gitpython and giturlparse are required\n\tpython3 -m pip install gitpython giturlparse")

logger = logging.getLogger(__name__)

USER_BASE = os.path.expanduser('~')
REPO_BASE = os.path.join(USER_BASE, 'repos')

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', action='store',
                        default='.', help='The starting path for repos to search and move')
    parser.add_argument('-b', '--base', action='store',
                        default=REPO_BASE, help='The base location to move the repo(s) to.')
    parser.add_argument('--dryrun', action='store_true',
                        default=False, help='Do a dryrun and don\'t modify anything.')
    parser.add_argument('-s', '--symlink', action='store_true',
                        default=False, help='Do a symlink back to the orinal location.')
    parser.add_argument('--debug', action='store_true',
                        default=False, help='Turn on debug logging.')
    return parser.parse_args()

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
    if name in [r.name for r in repo.remotes]:
        remote = repo.remote(name)
        return next(remote.urls)
    else:
        _avail = "Available remotes {}".format(repo.remotes)
        logger.warning("The remote named '{}' was not found. {}".format(
            name, _avail))
    return None


def walklevel(some_dir, level=1):
    some_dir = some_dir.rstrip(os.path.sep)
    assert os.path.isdir(some_dir)
    num_sep = some_dir.count(os.path.sep)
    for root, dirs, files in os.walk(some_dir):
        yield root, dirs, files
        num_sep_this = root.count(os.path.sep)
        if num_sep + level <= num_sep_this:
            del dirs[:]


def find_git_dirs(path):
    git_dirs = []
    for root, dirs, files in walklevel(path, 0):
        logger.debug("root: {} \ndirs: {}".format(root, dirs))
        logger.debug("Looking in {} for .git dir".format(root))
        if os.path.exists(os.path.join(root, '.git')):
            git_dirs.append(root)
            break
        for d in dirs:
            logger.debug("Looking in {} for .git dir".format(d))
            if os.path.exists(os.path.join(d, '.git')):
                logger.debug("Found .git dir in {}".format(d))
                git_dirs.append(d)
    return git_dirs

def setup_logging(args):
    if args.debug:
        loghandler = logging.StreamHandler()
        loghandler.setFormatter(logging.Formatter('mvrepo: %(levelname)s: %(message)s'))
        if args.dryrun:
            loghandler.setFormatter(logging.Formatter('mvrepo: %(levelname)s: dryrun: %(message)s'))
        logger.addHandler(loghandler)
        logger.setLevel(logging.DEBUG)
    else:
        loghandler = logging.StreamHandler()
        if args.dryrun:
            loghandler.setFormatter(logging.Formatter('dryrun: %(message)s'))
        logger.addHandler(loghandler)
        logger.setLevel(logging.INFO)


def move_dir(src, dest, symlink=False, dryrun=False):
    if os.path.islink(src):
        logger.warning("Directory {} is a symlink. Skipping...".format(src))
        return
    logger.info("{} -> {}".format(src, dest))
    if not dryrun:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(src, dest)
    if symlink:
        logger.info("symlink {} -> {}".format(src, dest))
        if not dryrun:
            os.symlink(dest, src)


def main():
    args = parse_args()
    setup_logging(args)
    dirs = find_git_dirs(args.path)
    logger.debug("Found git dirs: \n\t{}".format("\n\t".join(dirs)))
    for d in dirs:
        r = get_remote(d)
        if r is None:
            continue
        p = get_os_path(r)
        move_dir(d, p, args.symlink, args.dryrun)


if __name__ == '__main__':
    main()
