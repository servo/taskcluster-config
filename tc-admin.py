#!/usr/bin/env python3

if __name__ == "__main__":
    import bootstrap

import os
os.environ.setdefault("TASKCLUSTER_ROOT_URL", "https://community-tc.services.mozilla.com/")


from tcadmin.appconfig import AppConfig
from tcadmin.resources import Role


appconfig = AppConfig()


@appconfig.generators.register
async def define_resources(resources):
    # https://github.com/mozilla/community-tc-config/pull/34/files#diff-0e8019c85dcac0b955401c427a3c4921R86-R96
    resources.manage("Client=project/servo/.*")
    resources.manage("WorkerPool=proj-servo/(?!ci$).*")
    resources.manage("Hook=project-servo/.*")
    resources.manage("Role=hook-id:project-servo/.*")
    resources.manage("Role=repo:github.com/servo/.*")
    resources.manage("Role=project:servo:.*")

    resources.add(Role(
        roleId="repo:github.com/servo/servo:branch:*",
        description="Scopes granted for push events to any branch of servo/servo",
        scopes=(
            "assume:project:servo:decision-task/trusted",
        ),
    ))
