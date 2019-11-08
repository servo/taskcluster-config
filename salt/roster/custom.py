import os
import yaml


def roster():
    pools = os.path.join(os.path.dirname(__file__), "..", "..", "config", "worker-pools.yml")
    pool = yaml.safe_load(open(pools))["macos"]
    hostname = pool["worker_hostname_template"]
    return {w: hostname.format(id=w) for w in pool["workers"]}


# Custom roster modules are unfortunately not documented.
# This part is copied from
# https://github.com/dmacvicar/salt/blob/381cc162e74616643d97e49b8674db753c4b53b2/salt/roster/flat.py#L36
def targets(tgt, tgt_type='glob', **kwargs):
    raw = roster()
    return __utils__['roster_matcher.targets'](raw, tgt, tgt_type, 'ipv4')
