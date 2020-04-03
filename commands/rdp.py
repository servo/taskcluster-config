import sys
import taskcluster
import subprocess


def main(task_id_or_url, *extra_client_args):
    prefix = "https://community-tc.services.mozilla.com/tasks/"
    if task_id_or_url.startswith(prefix):
        task_id = task_id_or_url[len(prefix):]
    else:
        task_id = task_id_or_url

    options = taskcluster.optionsFromEnvironment()
    queue = taskcluster.Queue(options)
    rdp_info = queue.getLatestArtifact(task_id, "project/servo/rdp-info")

    supported_clients = [
        ["xfreerdp", "/v:{host}:{port}", "/u:{username}", "/p:{password}"],
    ]
    for arg_templates in supported_clients:
        args = [template.format(**rdp_info) for template in arg_templates] + list(extra_client_args)
        if executable_is_in_path(args[0]):
            return subprocess.run(args).returncode

    print("Couldn’t find a supported RDP client installed.")
    print("Supported: " + ", ".join(args[0] for args in supported_clients))


def executable_is_in_path(executable):
    process = subprocess.run(["which", executable], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process.returncode == 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
