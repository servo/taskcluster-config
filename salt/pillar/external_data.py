import urllib
import taskcluster


CACHE = {}


def ext_pillar(_minion_id, _pillar, *_args):
    if not CACHE:
        secrets = taskcluster.Secrets(taskcluster.optionsFromEnvironment())
        CACHE["credentials"] = secrets.get("project/servo/tc-client/worker/macos/1")["secret"]

        url = "https://raw.githubusercontent.com/servo/saltfs/master/admin/files/ssh/%s.pub"
        CACHE["ssh_keys"] = [urllib.urlopen(url % name).read() for name in [
            "jdm",
            "manishearth",
            "simonsapin",
        ]]
    return CACHE
