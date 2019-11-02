#!/usr/bin/env python3

if __name__ == "__main__":
    import bootstrap

import os
os.environ.setdefault("TASKCLUSTER_ROOT_URL", "https://community-tc.services.mozilla.com/")


from tcadmin.appconfig import AppConfig
from tcadmin.resources import Role
import re
import yaml


# All resources managed here should be "externally managed" in community-tc-config:
# https://github.com/mozilla/community-tc-config/blob/57615932e/generate/projects.py#L86-L96
appconfig = AppConfig()


@appconfig.generators.register
async def worker_pools(resources):
    externally_managed = []
    for name, config in parse_yaml("worker-pools.yml").items():
        if config == "externally managed":
            externally_managed.append(name)
        else:
            raise ValueError("unimplemented")

    externally_managed = "|".join(map(re.escape, externally_managed))
    resources.manage("WorkerPool=proj-servo/(?!(%s)$).*" % externally_managed)


@appconfig.generators.register
async def roles(resources):
    resources.manage("Role=repo:github.com/servo/servo:.*")
    resources.manage("Role=hook-id:project-servo/.*")
    resources.manage("Role=project:servo:.*")
    for config in parse_yaml("roles.yml"):
        resources.add(Role(**config))


@appconfig.generators.register
async def clients(resources):
    resources.manage("Client=project/servo/.*")


@appconfig.generators.register
async def hooks(resources):
    resources.manage("Hook=project-servo/.*")


def parse_yaml(filename):
    return yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "config", filename)))
