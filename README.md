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


## Quick Start

If you would like to propose a change to Servo’s configuration of the Community-TC deployment,
you are in the right spot.
You should already have an understanding of the resources you would like to modify.
See the [Taskcluster Documentation](https://community-tc.services.mozilla.com/docs)
or consult with the Servo team or the Taskcluster team if you need assistance.

Ensure you have `python3` and `virtulenv` executables in your `$PATH` and run:

```
./tc-admin.py diff
```

(Alternatively,
install the tc-admin [`tc-admin`](https://github.com/taskcluster/tc-admin) app some other way
and use it from this directory.)

This will show you the current difference between what's defined in your local repository
and the runtime configuration of the deployment.
Most of the time, there should be no difference.

After making a change in the configuration,
you can examine the results by running `./tc-admin.py diff` again.
If you are adding or removing a number of resources,
you can use `--ids-only` to show only the names of the added or removed resources.
See `./tc-admin.py --help` for more useful command-line tricks.
