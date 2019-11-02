#!/usr/bin/env python3

if __name__ == "__main__":
    import bootstrap

import os
import sys
os.environ.setdefault("TASKCLUSTER_ROOT_URL", "https://community-tc.services.mozilla.com/")
sys.path.insert(0, os.path.dirname(__file__))


from tcadmin.appconfig import AppConfig
from tcadmin.resources import Role, WorkerPool
import re
import yaml
import worker_pools


# All resources managed here should be "externally managed" in community-tc-config:
# https://github.com/mozilla/community-tc-config/blob/57615932e/generate/projects.py#L86-L96
appconfig = AppConfig()


@appconfig.generators.register
async def register_worker_pools(resources):
    externally_managed = []
    pools = []
    for name, config in parse_yaml("worker-pools.yml").items():
        kind = config.pop("kind")
        if kind == "externally-managed":
            externally_managed.append(name)
        else:
            pools.append(WorkerPool(
                workerPoolId="proj-servo/" + name,
                description="Servo `%s` workers" % name,
                owner="servo-ops@mozilla.com",
                emailOnError=False,
                **getattr(worker_pools, kind)(**config)
            ))

    externally_managed = "|".join(map(re.escape, externally_managed))
    resources.manage("WorkerPool=proj-servo/(?!(%s)$).*" % externally_managed)
    resources.update(pools)


@appconfig.generators.register
async def register_roles(resources):
    resources.manage("Role=repo:github.com/servo/servo:.*")
    resources.manage("Role=hook-id:project-servo/.*")
    resources.manage("Role=project:servo:.*")
    for config in parse_yaml("roles.yml"):
        resources.add(Role(**config))


@appconfig.generators.register
async def register_clients(resources):
    resources.manage("Client=project/servo/.*")


@appconfig.generators.register
async def register_hooks(resources):
    resources.manage("Hook=project-servo/.*")


def parse_yaml(filename):
    return yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "config", filename)))
