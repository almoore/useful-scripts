#!/usr/bin/env python
'''
A CLI interface to a remote salt-api instance
'''
from __future__ import print_function

import json
import sys
import time

import pepper
from pepper.cli import PepperCli
from pepper import PepperException

def get_jid(json_data):
    if type(json_data) is str:
        data = json.loads(json_data)
    elif type(json_data) is dict:
        data = json_data
    else:
        return None
    ret_dict = next(iter(data.get('return',[])), None)
    return ret_dict.get('jid')


def run():
    try:
        cli = PepperCli()
        for exit_code, result in async_run():
            print(result)
            if exit_code is not None:
                raise SystemExit(exit_code)
    except PepperException as exc:
        print('Pepper error: {0}'.format(exc), file=sys.stderr)
        raise SystemExit(1)
    except KeyboardInterrupt:
        # TODO: mimic CLI and output JID on ctrl-c
        raise SystemExit(0)
    except Exception as e:
        if __name__ == '__main__':
            print(e)
            print('Uncaught Pepper error (increase verbosity for the full traceback).', file=sys.stderr)
            raise SystemExit(1)
        else:
            pass
    
def poll_for_returns(cli, api, load, timeout=0, poll_time=0):
    '''
    Run a command with the local_async client and periodically poll the job
    cache for returns for the job.
    '''
    load[0]['client'] = 'local_async'
    async_ret = api.low(load)
    jid = async_ret['return'][0]['jid']
    nodes = async_ret['return'][0]['minions']
    ret_nodes = []
    exit_code = 1

    # keep trying until all expected nodes return
    total_time = 0
    start_time = time.time()
    exit_code = 0
    _timeout = timeout if timeout else cli.options.timeout
    _poll = poll_time if poll_time else cli.seconds_to_wait
    while True:
        total_time = time.time() - start_time
        print("Total time:", total_time)
        if total_time > _timeout:
            exit_code = 1
            break
        # Login every time removing option for token
        auth = api.login(*cli.parse_login())
        jid_ret = api.lookup_jid(jid)
        ret_nodes = list(jid_ret['return'][0].keys())

        if set(ret_nodes) == set(nodes):
            exit_code = 0
            break
        else:
            time.sleep(_poll)

    exit_code = exit_code if cli.options.fail_if_minions_dont_respond else 0
    if set(ret_nodes) == set(nodes):
        ret = api.runner(fun='jobs.print_job',jid=jid)
    else:
        ret = { 'Failed': list(set(ret_nodes) ^ set(nodes)) } 
    yield exit_code, ret

def async_run():
    try:
        cli = PepperCli()
        cli.parse()
        
        load = cli.parse_cmd()
        api = pepper.Pepper(
            cli.parse_url(),
            debug_http=cli.options.debug_http,
            ignore_ssl_errors=cli.options.ignore_ssl_certificate_errors)
        auth = api.login(*cli.parse_login())
        # Call with the 
        if load[0]['client'] == 'local':
            for exit_code, ret in poll_for_returns(cli, api, load):
                yield exit_code, json.dumps(ret, sort_keys=True, indent=4)
        else:
            ret = api.low(load)
            exit_code = 0
            yield exit_code, json.dumps(ret, sort_keys=True, indent=4)
    except PepperException as exc:
        print('Pepper error: {0}'.format(exc), file=sys.stderr)


if __name__ == '__main__':
    run()
