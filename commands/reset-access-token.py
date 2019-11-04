import sys
import taskcluster


def main(client_id):
    assert client_id.startswith("project/servo/")

    print("Client ID: `%s`" % client_id)
    print("Creating a new access token will invalidate the current one.")
    if input("Continue? [y/n] ") != "y":
        return 1

    options = taskcluster.optionsFromEnvironment()
    result = taskcluster.Auth(options).resetAccessToken(client_id)

    key = "project/servo/tc-client/" + client_id[len("project/servo/"):]
    secret = {"client_id": client_id, "access_token": result["accessToken"]}
    payload = {"secret": secret, "expires": result["expires"]}
    taskcluster.Secrets(options).set(key, payload)


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
