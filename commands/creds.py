import click
import html
import os
import sys
import taskcluster
import urllib.parse
import urllib.request
import webbrowser
import wsgiref.simple_server


DEFAULT_ROOT_URL = "https://community-tc.services.mozilla.com/"
DEFAULT_SCOPES = ["assume:project-admin:servo"]


@click.command()
@click.option("-p", "--port", default=0,
              help="Port number to listen to. Zero selects on at random.")
@click.option("-n", "--name", default="cli",
              help="An identifier to include in the client ID")
@click.option("-d", "--description", default="Temporary client for use on the command line",
              help="The new client’s description")
@click.option("-e", "--expires", default="2d",
              help="How much time until the credentials expire")
@click.option("-s", "--scopes", default=DEFAULT_SCOPES, multiple=True,
              help="Which Taskcluster scopes to grant to the new client")
def creds(port, name, description, expires, scopes):
    """
    Create a new Taskcluster “client” for command-line use,
    and print environment variables with its credentials.

    Use it like this:

    $ eval `./mach creds`
    """
    root_url = os.environ.get("TASKCLUSTER_ROOT_URL", DEFAULT_ROOT_URL)
    client_id = None
    access_token = None
    missing_scopes = None
    def wsgi_app(environ, start_response):
        nonlocal client_id
        nonlocal access_token
        nonlocal missing_scopes
        query = urllib.parse.parse_qs(environ['QUERY_STRING'])
        client_id, = query["clientId"]
        access_token, = query["accessToken"]

        auth = taskcluster.Auth({
            "rootUrl": root_url,
            "credentials": {"clientId": client_id, "accessToken": access_token},
        })
        missing_scopes = set(scopes) - set(auth.currentScopes()["scopes"])
        if missing_scopes:
            start_response("401 Unauthorized", [("Content-Type", "text/html")])
            return [b"""
                <!doctype html>
                <title>Missing scopes</title>
                <h1>You have successfully signed in,
                    but are missing some of the requested scopes</h1>
                <ul>
            """ + "\n".join(
                ("<li><code>%s</code></li>" % html.escape(scope))
                for scope in sorted(missing_scopes)
            ).encode("utf-8")]

        start_response("200 OK", [("Content-Type", "text/html")])
        return [b"""
            <!doctype html>
            <title>Sign-In Successful</title>
            <h1>You have successfully signed in</h1>
            <p>You may now close this tab.</p>
        """]

    with wsgiref.simple_server.make_server("127.0.0.1", port, wsgi_app) as httpd:
        # Disable logging
        httpd.RequestHandlerClass.log_message = lambda *a, **k: None

        query = urllib.parse.urlencode([
            ("scope", scope)
            for scope in scopes
        ] + [
            ("expires", expires),
            ("description", description),
            ("name", "%s-%s" % (name, taskcluster.slugId()[:6])),
            ("callback_url", "http://localhost:%s" % httpd.server_address[1]),
        ])
        url = "%sauth/clients/create?%s" % (root_url, query)

        sys.stderr.write("Listening on %s:%s\n" % httpd.server_address)
        sys.stderr.write("Opening %s\n" % url)
        webbrowser.open(url)

        while client_id is None or access_token is None:
            httpd.handle_request()

    sys.stderr.write("Exporting TASKCLUSTER_CLIENT_ID and TASKCLUSTER_ACCESS_TOKEN\n")
    print("export TASKCLUSTER_CLIENT_ID='%s'" % client_id)
    print("export TASKCLUSTER_ACCESS_TOKEN='%s'" % access_token)

    if missing_scopes:
        sys.stderr.write("The new client is missing scopes:\n")
        for scope in sorted(missing_scopes):
            sys.stderr.write("* %s\n" % scope)
        sys.exit(1)


if __name__ == "__main__":
    creds()
