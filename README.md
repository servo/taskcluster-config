# Taskcluster configuration for Servo CI

This repository contains tools and configuration for Servo’s use of
[Taskcluster](https://community-tc.services.mozilla.com/docs/) for testing pull requests.

As much as possible of the configuration is kept “in tree”
[in the `servo/servo` repository](https://github.com/servo/servo/tree/master/etc/taskcluster)
so that changes (for example `apt install`’ing a new system dependency in a `Dockerfile`)
can be made in the same pull request that relies on them.
This reduces the need for coordination across multiple repositories.
See also the `README` there for more on Servo’s testing workflow.

Some other parts of the configuration are not practical to deploy automatically
when merging a pull request, and require semi-manual steps. They are kept here.


## Requirements

Ensure that you have `python3` and `virtulenv` executables in your `$PATH`.
The commands below will automatically create a virtual environment
and install Python dependencies in it.


## `./mach tc`: Taskcluster [roles], [clients], [worker pools], and [hooks]

[roles]: https://community-tc.services.mozilla.com/docs/manual/design/apis/hawk/roles
[clients]: https://community-tc.services.mozilla.com/docs/manual/access-control/api#clients
[hooks]: https://community-tc.services.mozilla.com/docs/reference/core/hooks
[worker pools]: https://community-tc.services.mozilla.com/docs/reference/core/worker-manager

A Taskcluster deployment has a collection of resources such a
that define its behavior.
These can all be managed via the Taskcluster API,
but managing them by hand is error-prone and difficult to track over time.
This tool exists to manage those resources in a controlled, observable way.
It does so by making API calls to determine the current state,
examining this repository to determine the desired state,
and then “applying” the necessary changes to get from the former to the latter.

Servo shares the [Community TC](https://community-tc.services.mozilla.com/)
deployment of Taskcluster with a number of other projects.
This tool manages the Servo-specific parts of the configuration.
It is inspired by
[community-tc-config](https://github.com/mozilla/community-tc-config)
(which manages the non-project-specific parts)
and uses [`tc-admin`](https://github.com/taskcluster/tc-admin)
to examine and update the deployment.
See that library’s documentation for background on how the process works.


### Making changes

You should already have an understanding of the resources you would like to modify.
See the [Taskcluster Documentation](https://community-tc.services.mozilla.com/docs)
or consult with the Servo team or the Taskcluster team if you need assistance.

First, run:

```
./mach tc diff
```

(See [Requirements](#requirements) if this doesn’t work.)

This will show you the current difference between what’s defined in your local repository
and the runtime configuration of the deployment.
Most of the time, there should be no difference.

Next, make your changes to `config/*.yml` or `commands/tc.py`.
Examine the results by running `./mach tc diff` again.
If you are adding or removing a number of resources,
you can use `--ids-only` to show only the names of the added or removed resources.
See `./mach tc --help` and `./mach tc <subcommand> --help` for more useful command-line tricks.

Once the configuration diff looks good, submit a pull request with your changes.


### Deploying changes

Check again that the configuration diff looks good:

```
./mach tc diff
```

Then, deploy them in a terminal that has [administrative Taskcluster credentials](
#obtaining-administrative-Taskcluster-credentials):

```
./mach tc apply
```

If no errors is printed, the changes take effect immediately.


## `./mach new-ami`: creating a new VM image for Windows workers

Unlike for Linux workers where the Taskcluster team manages a VM image that runs Docker containers
and gives us full control (including `root` privileges) within task-specific Docker images,
we manage a custom Windows VM image for Servo.
This lets us for example control which version or [which components](
https://github.com/servo/taskcluster-config/blob/f921dc11/windows/first-boot.ps1#L79-L85)
of MSVC are installed.

(Note that MSVC needs to be installed system-wide,
but for tools that don’t we prefer user-local [task-specific installations](
https://github.com/servo/servo/blob/8abc272d/etc/taskcluster/decisionlib.py#L491-L516)
that can be managed in-tree.)

This tool builds a new AMI (Amazon Machine Image) by
picking the most recent Amazon-provided AMI for a given configuration of Windows
(see `BASE_AMI_PATTERN` in `commands/new-ami.py`),
and starting a temporary instance with that AMI and a PowerShell script to run on first boot.
When the script finishes, the instance shuts itself down and the tool takes a snapshot.

In addition to [common requirements](#requirements)
this tool requires the
[`aws` command-line tool](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-welcome.html),
configured with credentials to some AWS account that will be use for the temporary instance
and then storage of the new AMI.


## Instructions

First, make your changes to `commands/new-ami.py` or `config/windows-first-boot.ps1`.

**Note**: when incrementing the version number in some download URL,
double-check whether the base name of the file has changed
to make sure that the URL as a whole is valid.

Run `./mach new-ami`.
This can take at least half an hour to complete.
The output includes:

* Possibly some `Waiter […] Max attempts exceeded` messages. They are safe to ignore.
* A `Password available` line with the URL of an entry in Taskcluster’s Secrets service.
  That entry contains the password for Windows user `Administrator` in the new image.
  That password can be use for remote login through RDP,
  which is usually not necessary but can be useful for example
  to read `generic-worker`’s log file if an instance is running without picking up tasks.
* A `Creating image` line with the image’s identifier.
  Copy this identifier into `config/worker-pools.yml`
  and use the `./mach tc` tool (see above) to deploy the new image.
* A `Running` line with the URL of a task testing the new image.
  Check that this task is running as expected before deploying an image.


## `./mach salt`: system configuration of macOS workers

Unlike Linux or Windows workers which run in short-lived VMs provisioned on demand
from AWS or GCP cloud providers,
Servo’s macOS workers run a dedicated hardware managed long-term by Macstadium.

This tool manages the configuration of those machine.
Note that tasks run a user-local install of [Homebrew](https://brew.sh/)
with [in-tree `Brewfile`s](https://github.com/servo/servo/tree/master/etc/taskcluster/macos),
while on the other hand installing XCode requires manual GUI interaction through VNC.
So this tool mostly manages [generic-worker](https://github.com/taskcluster/generic-worker),
which interacts with Taskcluster to pick up and run tasks.

This tool uses SaltStack in
[agentless](https://docs.saltstack.com/en/getstarted/ssh/index.html) mode
to manage the configuration of those machines.
In addition to [administrative Taskcluster credentials](
#obtaining-administrative-Taskcluster-credentials),
it requires an SSH key that has been previously been deployed.

The command-line interface is that of `salt-ssh`.
For example, check that all machines are reachable and responsive:

```
./mach salt '*' test.ping
```

After modifying files under the `salt/` directory,
see what changes *would* be made on each machine without actually changing anything:

```
./mach salt '*' state.apply test=True
```

Applying changes to all machines:

```
./mach salt '*' state.apply
```

… or to only one machine:

```
./mach salt mac3 state.apply
```


### (Re)deploying a macOS worker

* Place an order or file a ticket with MacStadium to get a new hardware or reinstall an OS.

* Change the administrator password to one generated with
  `</dev/urandom tr -d -c 'a-zA-Z' | head -c 8; echo`
  (this short because of VNC),
  and save it in the shared 1Password account.

* Give the public IPv4 address a DNS name through Cloudflare.

* Add a corresponding entry in the `salt/roster` file.

* Log in through VNC, and run `xcode-select --install`.

* Still in VNC, install the jdk8 package from http://adoptopenjdk.net

* Install an initial SSH key into `/Users/administrator/.ssh/authorized_keys`
  and `/var/root/.ssh/authorized_keys`.


## `./mach reset-access-token`: making Taskcluster credentials for programmatic access

The `./mach tc` command can manage “clients”, which is useful for granting them scopes,
but does not manage their (secret) access token at all.
This tool resets the access token of a given client and stores it in the Secrets service,
where it can be accessed programmatically for example by `./mach salt`.

```
./mach reset-access-token project/servo/EXAMPLE
```


## `./mach kill-workers`: manually terminating cloud workers

The configuration of a given short-lived cloud instance on AWS or GCP usually doesn’t change.
Instead we start new ones with a different configuration,
but that can leave the previous instances still picking up tasks for a while.

In the case of Windows instances running `generic-worker`,
the `deploymentId` mechanism means that instances *should* shut themselves down
with a few minutes after a worker pool configuration change.

As a last resort, this tool uses `worker-manager`’s API to instruct it
to forcibly terminate all or one cloud instances in a given worker pool.
Any task currently running on those workers will fail.

```
./mach kill-workers win2016-staging
```


## Obtaining administrative Taskcluster credentials

* Navigate to https://community-tc.services.mozilla.com/profile
* If not already signed in, click the “Sign in” button on the top right, then “Sign in with GitHub”
* Take note of your browsing session’s client ID. It should look like `github/291359|SimonSapin`
* Check that `assume:project-admin:servo` is listed under “Scopes”
* Navigate to https://community-tc.services.mozilla.com/auth/clients/create
* Pick an ID for the new client that starts with yours, followed by `/` and some identifier.
  For example, `github/291359|SimonSapin/cli`.
* Pick an appropriate expiration date.
* Copy-paste `assume:project-admin:servo` into the scopes given to this new client.
* Create the client with the “Save” icon at the bottom right.
* In your terminal, set environment variables with the chosen ID
  and the token that shows up (only once!) after creating the client.
  For example:

  ```sh
  export TASKCLUSTER_CLIENT_ID="github/291359|SimonSapin/cli"
  export TASKCLUSTER_ACCESS_TOKEN="xxxxxx-yyyyyy-zzzzzz"
  ```
