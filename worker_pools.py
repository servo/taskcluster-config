# Based on https://github.com/mozilla/community-tc-config/blob/master/generate/workers.py

import json
import hashlib


def aws(min_capacity, max_capacity, regions, capacity_per_instance_type):
    return {
        "providerId": "community-tc-workers-aws",
        "config": {
            "minCapacity": min_capacity,
            "maxCapacity": max_capacity,
            "launchConfigs": [
                {
                    "capacityPerInstance": capacity_per_instance,
                    "region": region,
                    "launchConfig": {
                        "ImageId": ami_id,
                        "InstanceType": instance_type,
                        "InstanceMarketOptions": {"MarketType": "spot"},
                    }
                }
                for region, ami_id in regions.items()
                for instance_type, capacity_per_instance in capacity_per_instance_type.items()
            ],
        }
    }


def aws_windows(**yaml_input):
    tc_admin_params = aws(**yaml_input)
    generic_worker_config = {
        "ed25519SigningKeyLocation": "C:\\generic-worker\\generic-worker-ed25519-signing-key.key",
        "taskclusterProxyExecutable": "C:\\generic-worker\\taskcluster-proxy.exe",
        "livelogExecutable": "C:\\generic-worker\\livelog.exe",
        "workerTypeMetadata": {},
        "sentryProject": "generic-worker",
        "wstAudience": "communitytc",
        "wstServerURL": "https://community-websocktunnel.services.mozilla.com",

        "checkForNewDeploymentEverySecs": 600,
        "idleTimeoutSecs": 14400,
        "shutdownMachineOnIdle": True,
    }
    for launch_config in tc_admin_params["config"]["launchConfigs"]:
        # Use a copy of `genric_worker_config` here so they each get their own `deploymentId`
        launch_config["workerConfig"] = {"genericWorker": {"config": dict(generic_worker_config)}}
        launch_config_bytes = json.dumps(launch_config, sort_keys=True).encode("utf8")
        deployment_id = hashlib.sha256(launch_config_bytes).hexdigest()
        launch_config["workerConfig"]["genericWorker"]["config"]["deploymentId"] = deployment_id
    return tc_admin_params
