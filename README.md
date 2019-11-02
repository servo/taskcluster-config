# Taskcluster configuration for Servo

This repository is loosely based on
[community-tc-config](https://github.com/mozilla/community-tc-config).

It defines a tool to manage the parts specific to the Servo project of the runtime configuration
for the Taskcluster deployment at https://community-tc.services.mozilla.com/.
It uses [`tc-admin`](https://github.com/taskcluster/tc-admin) to examine and update the deployment.
See that library's documentation for background on how the process works.


## Background

A Taskcluster deployment has a collection of resources such a
[roles](https://community-tc.services.mozilla.com/docs/manual/design/apis/hawk/roles),
[hooks](https://community-tc.services.mozilla.com/docs/reference/core/hooks), and
[worker pools](https://community-tc.services.mozilla.com/docs/reference/core/worker-manager),
that define its behavior.
These can all be managed via the Taskcluster API,
but managing them by hand is error-prone and difficult to track over time.
This tool exists to manage those resources in a controlled, observable way.
It does so by making API calls to determine the current state,
examining this repository to determine the desired state,
and then "applying" the necessary changes to get from the former to the latter.


## Making changes

If you would like to propose a change to Servo’s configuration of the Community-TC deployment,
you are in the right spot.
You should already have an understanding of the resources you would like to modify.
See the [Taskcluster Documentation](https://community-tc.services.mozilla.com/docs)
or consult with the Servo team or the Taskcluster team if you need assistance.

Ensure you have `python3` and `virtulenv` executables in your `$PATH` and run:

```
./mach tc diff
```

This will show you the current difference between what's defined in your local repository
and the runtime configuration of the deployment.
Most of the time, there should be no difference.

After making a change in the configuration,
you can examine the results by running `./mach tc diff` again.
If you are adding or removing a number of resources,
you can use `--ids-only` to show only the names of the added or removed resources.
See `./mach tc --help` for more useful command-line tricks.

Once the configuration diff looks good, submit a pull request with your changes.


## Deploying changes

This requires creatin a new "client" with administrative access:

* Navigate to https://community-tc.services.mozilla.com/profile
* If not already signed in, click the "Sign in" button on the top right, then "Sign in with GitHub"
* Take note of your browsing session’s client ID. It should look like `github/291359|SimonSapin`
* Check that `assume:project-admin:servo` is listed under "Scopes"
* Navigate to https://community-tc.services.mozilla.com/auth/clients/create
* Pick an ID for the new client that starts with yours, followed by `/` and some identifier.
  For example, `github/291359|SimonSapin/cli`.
* Pick an expiration date that seems appropriate.
* Copy-paste `assume:project-admin:servo` into the scopes given to this new client.
* Create the client with the "Save" icon at the bottom right.
* In your terminal, set environment variables with the chosen ID
  and the token that shows up (only once!) after creating the client.

```sh
export TASKCLUSTER_CLIENT_ID="github/291359|SimonSapin/cli"
export TASKCLUSTER_ACCESS_TOKEN="xxxxxx-yyyyyy-zzzzzz"
```

Check again that the diff looks good:

```
./mach tc diff
```

Then deploy:

```
./mach tc apply
```
