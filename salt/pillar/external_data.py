import os
import taskcluster
import urllib
import yaml


CACHE = {}


def ext_pillar(minion_id, _pillar, *_args):
    if not CACHE:
        secrets = taskcluster.Secrets(taskcluster.optionsFromEnvironment())
        CACHE["credentials"] = secrets.get("project/servo/tc-client/worker/macos/1")["secret"]

        url = "https://raw.githubusercontent.com/servo/saltfs/master/admin/files/ssh/%s.pub"
        CACHE["ssh_keys"] = [urllib.urlopen(url % name).read() for name in [
            "jdm",
            "manishearth",
            "simonsapin",
        ]]

        CACHE["workers"] = read_yaml("worker-pools.yml")["macos"]["workers"]

    worker = CACHE["workers"][minion_id]
    disabled = {"disabled": True, None: False}[worker]
    return dict(disabled=disabled, **CACHE)


def read_yaml(filename):
    return yaml.safe_load(open(os.path.join(
        os.path.dirname(__file__), "..", "..", "config", filename)))
