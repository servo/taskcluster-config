import datetime
import json
import os
import subprocess
import tempfile


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
BASE_AMI_PATTERN = "Windows_Server-2016-English-Full-Base-*"

REGION = "us-west-2"
WORKER_TYPE = "servo-win2016"

# Account ID for `moz-fx-tc-community-workers`
# https://github.com/mozilla/community-tc-config/pull/55/files#diff-13a616161132a2d2a028bac50f5cd928R18
TASKCLUSTER_AWS_USER_ID = "885316786408"


def main(tmp):
    base_ami = most_recent_ami(BASE_AMI_PATTERN)
    print("Starting an instance with base image:", base_ami["ImageId"], base_ami["Name"])

    key_name = "ami-bootstrap"
    ec2("delete-key-pair", "--key-name", key_name)
    result = ec2("create-key-pair", "--key-name", key_name)
    key_filename = os.path.join(tmp, "key")
    with open(key_filename, "w") as f:
        f.write(result["KeyMaterial"])

    ps1 = os.path.join(os.path.dirname(__file__), "..", "config", "first-boot.ps1")
    with open(ps1) as f:
        user_data = "<powershell>\n%s\n</powershell>" % f.read()
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

    ec2("create-tags", "--resources", instance_id, "--tags",
        "Key=Name,Value=TC %s base instance" % WORKER_TYPE)

    print("Waiting for password data to be available…")
    ec2_wait("password-data-available", "--instance-id", instance_id)
    result = ec2("get-password-data", "--instance-id", instance_id,
                 "--priv-launch-key", key_filename)
    print("Administrator password:", result["PasswordData"])

    print("Waiting for the instance to finish executing first-boot.ps1 and shut down…")
    ec2_wait("instance-stopped", "--instance-id", instance_id)

    now = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H.%M.%S")
    image_id = ec2("create-image", "--instance-id", instance_id,
                   "--name", "TC %s %s" % (WORKER_TYPE, now))["ImageId"]
    print("Started creating image with ID %s …" % image_id)

    ec2_wait("image-available", "--image-ids", image_id)
    ec2("modify-image-attribute", "--image-id", image_id,
        "--launch-permission", "Add=[{UserId=%s}]" % TASKCLUSTER_AWS_USER_ID)

    print("Image available. Terminating the temporary instance…")
    ec2("terminate-instances", "--instance-ids", instance_id)


def most_recent_ami(name_pattern):
    result = ec2(
        "describe-images", "--owners", "amazon",
        "--filters", "Name=platform,Values=windows", "Name=name,Values=" + name_pattern,
    )
    return max(result["Images"], key=lambda x: x["CreationDate"])


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


def try_ec2(*args):
    try:
        return ec2(*args)
    except subprocess.CalledProcessError:
        return None


def ec2(*args):
    args = ["aws", "ec2", "--region", REGION, "--output", "json"] + list(args)
    output = subprocess.check_output(args)
    if output:
        return json.loads(output)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        main(tmp)
