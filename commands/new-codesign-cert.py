"""
Generate a certificate for code signing on Windows.
The `new-ami` command installs that certificate in the system-wide trust store of Windows VMs.

See https://github.com/servo/servo/pull/25661

"""

import base64
import datetime
import os
import subprocess
import sys
import taskcluster
import tempfile


def main():
    with open("/etc/ssl/openssl.cnf") as f:
        config = f.read()
    config += (
        "[v3_req]\n"
        "basicConstraints = critical,CA:FALSE\n"
        "keyUsage = digitalSignature\n"
        "extendedKeyUsage = critical,codeSigning"
    )
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        with open("config", "w") as f:
            f.write(config)
        now = datetime.datetime.now()
        run("""
            openssl req
            -x509
            -sha256
            -nodes
            -days 730
            -newkey rsa:4096
            -subj /CN=Allizom
            -extensions v3_req
            -batch

            -config config
            -keyout key.pem
            -out cert.pem
        """)
        run("""
            openssl pkcs12
            -export
            -passout pass:

            -inkey key.pem
            -in cert.pem
            -out servo.pfx
        """)
        with open("servo.pfx", "rb") as f:
            pfx = f.read()

    value = {"pfx": {"base64": base64.b64encode(pfx)}, "created": now}

    tc_options = taskcluster.optionsFromEnvironment()
    secrets = taskcluster.Secrets(tc_options)
    for name in [now.strftime("%Y-%m-%d_%H-%M-%S"), "latest"]:
        payload = {"secret": value, "expires": datetime.datetime(3000, 1, 1, 0, 0, 0)}
        secrets.set("project/servo/windows-codesign-cert/" + name, payload)

    print(
        "https://community-tc.services.mozilla.com/secrets/"
        "project%2Fservo%2Fwindows-codesign-cert%2Flatest"
    )


def run(whitespace_separated_args):
    subprocess.run(whitespace_separated_args.split(), check=True)


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
