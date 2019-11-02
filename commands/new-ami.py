import os
import json
import datetime
import subprocess


BASE_AMI_PATTERN = "Windows_Server-2016-English-Full-Base-*"
REGION = "us-west-2"
WORKER_TYPE = "servo-win2016"

# Account ID for `moz-fx-tc-community-workers`
# https://github.com/mozilla/community-tc-config/pull/55/files#diff-13a616161132a2d2a028bac50f5cd928R18
TASKCLUSTER_AWS_USER_ID = "885316786408"


def main():
    base_ami = most_recent_ami(BASE_AMI_PATTERN)
    print("Starting an instance with base image:", base_ami["ImageId"], base_ami["Name"])

    key_name = "%s_%s" % (WORKER_TYPE, REGION)
    key_filename = key_name + ".id_rsa"
    ec2("delete-key-pair", "--key-name", key_name)
    result = ec2("create-key-pair", "--key-name", key_name)
    write_file(key_filename, result["KeyMaterial"].encode("utf-8"))

    user_data = b"<powershell>\n%s\n</powershell>" % read_file("first-boot.ps1")
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
                 "--priv-launch-key", here(key_filename))
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


def read_file(filename):
    with open(here(filename), "rb") as f:
        return f.read()


def write_file(filename, contents):
    with open(here(filename), "wb") as f:
        f.write(contents)


def here(filename):
    return os.path.join(os.path.dirname(__file__), "..", "windows", filename)


if __name__ == "__main__":
    main()