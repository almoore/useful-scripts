# -*- coding: utf-8 -*-
"""
Getting realtime output using Python Subprocess
===============================================

A convenience module for shelling out with realtime output

Credit:
  Largely taken from https://www.endpoint.com/blog/2015/01/28/getting-realtime-output-using-python


The Problem
-----------
When I launch a long running unix process within a python script, it waits
until the process is finished, and only then do I get the complete output of my
program. This is annoying if I’m running a process that takes a while to
finish. And I want to capture the output and display it in the nice manner with
clear formatting. 

includes: 
- subprocess - ​Works with additional processes.
"""

from subprocess import Popen, PIPE


def run(command):
    """
    Create a generator to a shell command with async output yielded
    :param command:
    :return:
    """
    process = Popen(command, stdout=PIPE, shell=True)
    while True:
        line = process.stdout.readline().rstrip()
        if not line:
            break
        yield line.decode('utf-8')


def run_command(command, verbose=False, dry=False):
    """
    Get output from command printed to stdout
    :param command: the command to run in the shell
    :param verbose: print command before executing it
    :param dry: print command do not execute
    """
    if verbose or dry:
        print(command)
        if dry:
            return
    for line in run(command):
        print(line)


if __name__ == "__main__":
    for path in run("ping -c 5 google.com"):
        print(path)
