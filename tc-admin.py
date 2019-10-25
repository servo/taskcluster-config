#!/usr/bin/env python3

if __name__ == "__main__":
    import bootstrap

import os
os.environ.setdefault("TASKCLUSTER_ROOT_URL", "https://community-tc.services.mozilla.com/")


import os
import yaml
from tcadmin.appconfig import AppConfig
from tcadmin.resources import Role


appconfig = AppConfig()

here = os.path.dirname(__file__)
config = os.path.join(here, "config")


def parse_yaml(filename):
    return yaml.load(open(os.path.join(config, filename)))


@appconfig.generators.register
async def define_resources(resources):
    # https://github.com/mozilla/community-tc-config/pull/34/files#diff-0e8019c85dcac0b955401c427a3c4921R86-R96
    resources.manage("Client=project/servo/.*")
    resources.manage("WorkerPool=proj-servo/(?!ci$).*")
    resources.manage("Hook=project-servo/.*")
    resources.manage("Role=hook-id:project-servo/.*")
    resources.manage("Role=repo:github.com/servo/.*")
    resources.manage("Role=project:servo:.*")

    for role in parse_yaml("roles.yml"):
        resources.add(Role(**role))
