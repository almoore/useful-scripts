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
- shlex - Lexical analysis of shell-style syntaxes.
"""

from subprocess import Popen, PIPE
import shlex


def run(command):
    process = Popen(command, stdout=PIPE, shell=True)
    while True:
        line = process.stdout.readline().rstrip()
        if not line:
            break
        yield line.decode('utf-8')


def run_command(command):
    process = Popen(shlex.split(command), stdout=PIPE)
    while True:
        output = process.stdout.readline().rstrip().decode('utf-8')
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())
    rc = process.poll()
    return rc


if __name__ == "__main__":
    for path in run("ping -c 5 google.com"):
        print(path)
