- Feature Name: SSH Push Next Level
- Start Date: 2016-07-29
- RFC PR: [#39](https://github.com/SUSE/susemanager-rfc/pull/39)

# Summary
[summary]: #summary

Using [Salt SSH] (https://docs.saltstack.com/en/latest/topics/ssh/) we can
provide a method of managing systems completely based on the SSH protocol. This
will enable users to target systems that are located outside of their company's
firewalls (systems that cannot *see* the server) while there is no need to
install any additional agent besides `sshd`. Still all the advanced config
management features that are supported for regular Salt clients (where
`salt-minion` is installed) will be supported as well.

# Motivation
[motivation]: #motivation

These are the advantages of the new SSH push feature compared to the old one as
implemented in SUSE Manager right now (based on the traditional stack):

- Managing systems using Salt SSH does not require any client side agents
besides `sshd` (no `rhnsd`, no `salt-minion`)
- All features that are available with the regular master/minion based approach
will be supported for SSH managed systems as well

# Detailed Design
[design]: #detailed-design

## System Registration

Systems to be managed via SSH can be registered using the existing bootstrapping
UI. An additional option should be added to select this method like e.g. a new
checkbox saying "Manage system completely via SSH".

Instead of applying the bootstrap state that would install and setup the
`salt-minion` agent we can synchronously perform the system registration in
terms of gathering all the software and hardware inventory using the salt SSH
client. This will result in a fully registered system with all the details ready
for further management.

In case it turns out to be too slow to query the list of packages and hardware
details in a synchronous way we can still consider falling back to registering a
minimal system while scheduling the initial update of the hardware and package
profiles for asynchronous execution.

Tasks to get us there:

- Refactor the current registration code so that it can be reused in a
synchronous context **or** rewrite a Salt SSH based version of it
- Deploy the susemanager SSH key (`~/.ssh/id_susemanager`) for authentication,
generate first if necessary
- Trigger SSH based registration from a new API endpoint that is called when
user selects system to be managed via SSH

## Contact Methods

The existing client *contact methods* can be reused in the context of Salt
systems. The following contact methods are currently available (these are labels
in the database):

- `default`
- `ssh-push`
- `ssh-push-tunnel`

In case of regular minions `default` is to be interpreted as `Salt` while for
traditional systems it means `Pull`. For SSH managed systems either of the
`ssh-push*` contact methods (with or without tunnel) can be used.

Tasks to get us there:

- Unhide the contact method in the UI for Salt entitled systems but make it
read only since we cannot easily migrate systems from `default` to `ssh-push` or
the other direction
- Let `default` appear as `Default` in the UI or show `Salt`/`Pull` depending on
the system's base entitlement
- Set the contact method correctly during minion bootstrapping

## Management

Executing management tasks (actions scheduled in SUSE Manager) via Salt SSH is
very similar to what the existing SSH push feature does:

1. Connect to the managed system via SSH
2. Perform the task (e.g. install a patch, remove a package, ...)
3. Close the connection when the task is done

This is a synchronous process explicitly requiring that we keep the connection
to the client open until the task is actually done, especially because the
asynchronous SSH client is actually [unimplemented in Salt]
(https://github.com/saltstack/salt/blob/develop/salt/client/ssh/client.py#L167).

Therefore it makes sense to reuse the existing SSH push taskomatic code that
already supports queueing and multi-threading with a configurable maximum number
of simultaneous connections to clients. This is currently backed by a job in
taskomatic that is scheduled to run once every minute to find candidate systems
that either:

1. Have a pending job that should be executed, or
2. Have not checked in for a long time

When a system is identified as a candidate, a worker thread is started that will
actually take care of executing the currently pending actions, in this case
using Salt SSH. System checkin can be done by simply executing a `test.ping` and
updating the checkin timestamp on success.

Tasks to get us there:

- Modify the driver class (`SSHPushDriver`) to create a Salt worker in case the
candidate system has a minion id
- Implement the new Salt SSH worker (`SSHPushWorkerSalt`) that will actually
figure out what is the currently pending tasks and execute those via Salt SSH
- Set the status of the corresponding actions based on the results
- Implement system checkin by calling `status.uptime` and updating the value
in the DB together with the kernel version (like the traditional checkin)

## Tunnel Setup

The first iteration of this feature should for simplicity leave out the topic
of tunneling other traffic (especially for accessing the package repositories)
via the SSH connection.

Tasks to get us there:

- In the bootstrapping UI allow users to enable tunneling separately OR just use
tunnel mode per default (always set the `ssh-push-tunnel` contact method)
- Setup tunneling during registration as with the old SSH push feature, e.g.
modify `/etc/hosts` via a state so that the `127.0.0.1` line contains the
hostname of SUSE Manager
- When calling Salt SSH via the API make sure to setup remote port forwards
correctly (requires the respective patch in Salt!)

## Special Features

### Remote Commands

The remote commands UI allows to execute commands on minions without creating
actions in the schedule. In order to support systems managed via Salt SSH the
preview should consider those and list them transparently. Actual commands can
then be executed using the `--raw-shell` option of Salt SSH.

Tasks to get us there:

- Adapt the preview to take Salt SSH systems into account
- Execute the command using the `--raw-shell` option of Salt SSH

# Drawbacks
[drawbacks]: #drawbacks

Why should we *not* do this?

# Alternatives
[alternatives]: #alternatives

## Use `salt-call` instead of Salt SSH

Instead of using Salt SSH we could have the server logging in to the managed
system (as with the existing SSH push) and call `salt-call` there to execute
modules or apply states, then transfer the results back to the server. For us
there is the following advantages though when using Salt SSH:

- We are not the ones to implement the SSH connection layer (using the poorly
documented Jsch Java library)
- The results are automatically transferred back to the server, we do not need
to take care of that
- There is no need to install `salt-minion` on the managed system, any system
with SSH access (and python installed) can be managed

# Unresolved Questions
[unresolved]: #unresolved-questions

- Q: Will it work to manage systems using the described method via a SUSE
Manager Proxy? How exactly are we going to do that?
- A: TODO
- Q: Would it make sense to install `salt-minion` on these clients (install, not
run) just to get the correct packages/code on the host instead of transferring
it again and again via Salt SSH to the target?
- A: Maybe, even though the standalone Salt environment per default is copied
only once and then reused for subsequent calls. Salt SSH rosters however allow
to specify the target system's storage directory for Salt components via a
[parameter]
(https://docs.saltstack.com/en/latest/topics/ssh/roster.html#thin-dir).
