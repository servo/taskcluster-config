import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import time

import jsone
import taskcluster
import tc


# Amazon provides an ovewhelming number of different Windows images,
# so it’s hard to find what’s relevant.
# Their console might show a paginated view like this:
#
# > ⇤ ← 1 to 50 of 13,914 AMIs → ⇥
#
# Let’s grep through this with the API:
#
# ```sh
# aws ec2 describe-images --owners amazon --filters 'Name=platform,Values=windows' \
#     --query 'Images[*].[ImageId,Name,Description]' --output table > /tmp/images
# < /tmp/images less -S
# ```
#
# It turns out that these images are all based on Windows Server,
# but their number is explained by the presence of many (all?) combinations of:
#
# * Multiple OS Version
# * Many available locales
# * *Full* (a.k.a. *with Desktop Experience*), or *Core*
# * *Base* with only the OS, or multiple flavors with tools like SQL Server pre-installed
#
# If we make some choices and filter the list:
#
# ```sh
# < /tmp/images grep 2016-English-Full-Base | less -S
# ```
#
# … we get a much more manageable handlful of images with names like
# `Windows_Server-2016-English-Full-Base-2018.09.15` or other dates.
#
# Let’s pick the most recent of those.
BASE_AMI_PATTERN = "Windows_Server-2019-English-Full-Base-*"

REGION = "us-west-2"

# Account ID for `moz-fx-tc-community-workers`
# https://github.com/mozilla/community-tc-config/pull/55/files#diff-13a616161132a2d2a028bac50f5cd928R18
TASKCLUSTER_AWS_USER_ID = "885316786408"


def main(image_id=None):
    tc_options = taskcluster.optionsFromEnvironment()
    if not image_id:
        with tempfile.TemporaryDirectory() as tmp:
            image_id = new_ami(tmp, tc_options)
    try_ami(image_id, tc_options)


def new_ami(tmp, tc_options):
    secrets = taskcluster.Secrets(tc_options)
    def set_secret(name, value):
        payload = {"secret": value, "expires": datetime.datetime(3000, 1, 1, 0, 0, 0)}
        secrets.set("project/servo/windows-administrator/" + name, payload)

    # Ensure we have appropriate credentials for writing secrets now
    # rather than at the end of the lengthy bootstrap process.
    set_secret("dummy", {})

    ps1 = os.path.join(os.path.dirname(__file__), "..", "config", "windows-first-boot.ps1")
    with open(ps1) as f:
        user_data = "<powershell>\n%s\n</powershell>" % f.read()

    cert = secrets.get("project/servo/windows-codesign-cert/latest")["secret"]
    pfx = cert["pfx"]["base64"]
    user_data = user_data.replace("REPLACE THIS WITH BASE64 PFX CODESIGN CERTIFICATE", pfx)
    log("Using code signning certificate created on", cert["created"])

    result = ec2(
        "describe-images", "--owners", "amazon",
        "--filters", "Name=platform,Values=windows", "Name=name,Values=" + BASE_AMI_PATTERN,
    )
    # Find the most recent
    base_ami = max(result["Images"], key=lambda x: x["CreationDate"])
    log("Found base image:", base_ami["Name"])

    key_name = "ami-bootstrap"
    ec2("delete-key-pair", "--key-name", key_name)
    result = ec2("create-key-pair", "--key-name", key_name)
    key_filename = os.path.join(tmp, "key")
    with open(key_filename, "w") as f:
        f.write(result["KeyMaterial"])

    result = ec2(
        "run-instances", "--image-id", base_ami["ImageId"],
        "--key-name", key_name,
        "--user-data", user_data,
        "--instance-type", "c4.xlarge",
        "--block-device-mappings",
        "DeviceName=/dev/sda1,Ebs={VolumeSize=75,DeleteOnTermination=true,VolumeType=gp2}",
        "--instance-initiated-shutdown-behavior", "stop"
    )
    assert len(result["Instances"]) == 1
    instance_id = result["Instances"][0]["InstanceId"]

    ec2_wait("password-data-available", "--instance-id", instance_id)
    password_result = ec2("get-password-data", "--instance-id", instance_id,
                          "--priv-launch-key", key_filename)

    log("Waiting for the instance to finish `first-boot.ps1` and shut down…")
    ec2_wait("instance-stopped", "--instance-id", instance_id)

    now = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H.%M.%S")
    image_id = ec2("create-image", "--instance-id", instance_id,
                   "--name", "win2016 bootstrap " + now)["ImageId"]

    set_secret(image_id, {"Administrator": password_result["PasswordData"]})
    log("Password available at https://community-tc.services.mozilla.com/secrets/"
        "project%2Fservo%2Fwindows-administrator%2F" + image_id)

    log("Creating image with ID %s …" % image_id)
    ec2_wait("image-available", "--image-ids", image_id)
    ec2("modify-image-attribute", "--image-id", image_id,
        "--launch-permission", "Add=[{UserId=%s}]" % TASKCLUSTER_AWS_USER_ID)

    log("Image available.")
    ec2("terminate-instances", "--instance-ids", instance_id)
    return image_id


def log(*args):
    now = datetime.datetime.now().replace(microsecond=0)
    print(now.isoformat(sep=" "), *args)


def ec2_wait(*args):
    # https://docs.aws.amazon.com/cli/latest/reference/ec2/wait/password-data-available.html
    # “It will poll every 15 seconds until a successful state has been reached.
    #  This will exit with a return code of 255 after 40 failed checks.”
    while True:
        try:
            return ec2("wait", *args)
        except subprocess.CalledProcessError as err:
            if err.returncode != 255:
                raise


def ec2(*args):
    args = ["aws", "ec2", "--region", REGION, "--output", "json"] + list(args)
    output = subprocess.check_output(args)
    if output:
        return json.loads(output)


def try_ami(ami_id, tc_options):
    pool = tc.parse_yaml("worker-pools.yml")["win2016"]
    pool.pop("kind")
    pool = tc.aws_windows(**pool)
    pool = dict(description="", emailOnError=False, owner="nobody@mozilla.com", **pool)

    now = datetime.datetime.now().replace(microsecond=0).isoformat()
    worker_type = "tmp-" + re.sub("[-:T]", "", now)
    pool_id = "proj-servo/" + worker_type

    task = {h["hookId"]: h for h in tc.parse_yaml("hooks.yml")}["daily"]["task"]
    task["metadata"]["name"] = "Trying new Windows image " + ami_id
    task["metadata"]["source"] = \
        "https://github.com/servo/taskcluster-config/blob/master/commands/try-ami.py"
    task["payload"]["env"]["SOURCE"] = task["metadata"]["source"]
    task["payload"]["env"]["TASK_FOR"] = "try-windows-ami"
    task["payload"]["env"]["GIT_REF"] = "refs/heads/master"
    task["payload"]["env"]["NEW_AMI_WORKER_TYPE"] = worker_type
    task["created"] = {"$eval": "now"}
    task = jsone.render(task, {})
    task_id = taskcluster.slugId()

    wm = taskcluster.WorkerManager(tc_options)
    queue = taskcluster.Queue(tc_options)
    wm.createWorkerPool(pool_id, pool)
    try:
        queue.createTask(task_id, task)
        task_view = "https://community-tc.services.mozilla.com/tasks/"
        log("Created " + task_view + task_id)
        while 1:
            time.sleep(2)
            result = queue.status(task_id)
            state = result["status"]["state"]
            if state not in ["unscheduled", "pending", "running"]:
                log("Decision task:", state)
                break

        # The decision task has finished, so any other task should be scheduled now
        while 1:
            tasks = []
            def handler(result):
                for task in result["tasks"]:
                    if task["status"]["taskId"] != task_id:
                        tasks.append((task["status"]["taskId"], task["status"]["state"]))
            queue.listTaskGroup(result["status"]["taskGroupId"], paginationHandler=handler)
            if all(state not in ["unscheduled", "pending"] for _, state in tasks):
                for task, _ in tasks:
                    log("Running " + task_view + task)
                break
            time.sleep(2)
    finally:
        wm.deleteWorkerPool(pool_id)


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
