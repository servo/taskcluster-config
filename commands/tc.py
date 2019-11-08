from tcadmin.appconfig import AppConfig
from tcadmin.main import main
from tcadmin.resources import Client, Hook, Role, WorkerPool
import hashlib
import json
import os
import re
import yaml


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
        elif kind == "static":
            pass
        else:
            builder = {
                "aws_windows": aws_windows,
            }[kind]
            pools.append(WorkerPool(
                workerPoolId="proj-servo/" + name,
                description="Servo `%s` workers" % name,
                owner="servo-ops@mozilla.com",
                emailOnError=False,
                **builder(**config)
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
    for config in parse_yaml("clients.yml"):
        resources.add(Client(**config))


@appconfig.generators.register
async def register_hooks(resources):
    resources.manage("Hook=project-servo/.*")
    for config in parse_yaml("hooks.yml"):
        resources.add(Hook(**config))


def parse_yaml(filename):
    return yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "..", "config", filename)))


# Based on https://github.com/mozilla/community-tc-config/blob/master/generate/workers.py


AWS_CONFIG = parse_yaml("aws.yml")


def launch_configs(worker_config, regions, capacity_per_instance_type, security_groups):
    return [
        {
            "capacityPerInstance": capacity_per_instance,
            "region": region,
            "workerConfig": worker_config,
            "launchConfig": {
                "ImageId": ami_id,
                "InstanceType": instance_type,
                "InstanceMarketOptions": {"MarketType": "spot"},
                "Placement": {"AvailabilityZone": az},
                "SubnetId": subnet_id,
                "SecurityGroupIds": [
                    AWS_CONFIG["region " + region]["security groups"][security_group]
                    for security_group in security_groups
                ],
            }
        }
        for region, ami_id in regions.items()
        for az, subnet_id in AWS_CONFIG["region " + region]["subnets by AZ"].items()
        for instance_type, capacity_per_instance in capacity_per_instance_type.items()
    ]


def aws_windows(min_capacity, max_capacity, **kwargs):
    generic_worker_config = parse_yaml("windows-generic-worker.yml")
    configs = launch_configs(
        worker_config={"genericWorker": {"config": generic_worker_config}},
        security_groups=["no-inbound", "rdp"],
        **kwargs
    )
    # Update the same mutable dict object that is also referenced in each launch config dict:
    hashed = hashlib.sha256(json.dumps(configs, sort_keys=True).encode("utf8")).hexdigest()
    generic_worker_config["deploymentId"] = hashed[:16]
    return {
        "providerId": "community-tc-workers-aws",
        "config": {
            "minCapacity": min_capacity,
            "maxCapacity": max_capacity,
            "launchConfigs": configs,
        }
    }


if __name__ == "__main__":
    main(appconfig)
