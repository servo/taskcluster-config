#!/usr/bin/env python3

if __name__ == "__main__":
    import bootstrap

import os
os.environ.setdefault("TASKCLUSTER_ROOT_URL", "https://community-tc.services.mozilla.com/")


from tcadmin.appconfig import AppConfig
from tcadmin.resources import Role
import yaml


# All resources managed here should be "externally managed" in community-tc-config:
# https://github.com/mozilla/community-tc-config/blob/57615932e/generate/projects.py#L86-L96
appconfig = AppConfig()


@appconfig.generators.register
async def worker_pools(resources):
    resources.manage("WorkerPool=proj-servo/(?!ci$).*")


@appconfig.generators.register
async def roles(resources):
    resources.manage("Role=hook-id:project-servo/.*")
    resources.manage("Role=repo:github.com/servo/servo:.*")
    resources.manage("Role=project:servo:.*")
    for role in parse_yaml("roles.yml"):
        resources.add(Role(**role))


@appconfig.generators.register
async def clients(resources):
    resources.manage("Client=project/servo/.*")


@appconfig.generators.register
async def hooks(resources):
    resources.manage("Hook=project-servo/.*")


here = os.path.dirname(__file__)
config = os.path.join(here, "config")


def parse_yaml(filename):
    return yaml.safe_load(open(os.path.join(config, filename)))
