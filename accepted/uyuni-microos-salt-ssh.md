- Feature Name: Salt SSH for transactional OSes
- Start Date: TODO

# Summary
[summary]: #summary

Uyuni users may choose to manage minions by using Salt SSH, for example due to network constraints. However, currently, systems that are based on transactional update, i.e. openSUSE MicroOS or SUSE Linux Micro (TU minions), do not support management via Salt SSH.

This RFC describes improvements for Salt SSH such that Uyuni can fully control TU minions by using Salt SSH.

# Motivation
[motivation]: #motivation

Uyuni users want feature parity of contact methods between TU minions and non-TU minions. Currently, users can use the Salt, Push via SSH (Salt SSH), or Push via SSH tunnel (Salt SSH proxy) contact methods to control their deployed non-TU minions. However, for TU minions, we support only the Salt method.

Enabling Salt SSH for TU minions is important, for example, for partially air gapped environments, where system administrators can provide a trusted bridge (SSH proxy) for Uyuni to reach the TU minion and update it as necessary.

# Detailed design
[design]: #detailed-design

## Current State

Currently, when Uyuni bootstraps a minion by using Salt SSH, Uyuni deploys a Salt client into `/var/tmp/venv-salt-minion`.
When Salt SSH makes a `state` call to a client, for example `state.sls example-sls-filename`, it additionally compiles the `example-sls-filename` state (and all its dependencies, such as files used by the state) into a tar file, and deploys it to a generated location in `/var/tmp`, such as `/var/tmp/.root_12345_salt/salt_state.tgz` (together with other data, such as external modules, grain info, etc).

TU minions are different from non-TU minions in that they mount some partitions as read-only, for example `/etc`. To modify such partitions, users use the `transactional-update` command.

The `transactional-update` command temporarily mounts the partitions as read-write, and after the modifications are done, it creates a new BTRFS snapshot that is activated upon restart (or upon using `transactional-update apply`).

Note that Salt SSH relies on both file systems for functions that modify the read-only file system:

- The filesystem outside of a transaction (OOT) contains both the Salt client, and, more importantly, the `salt_state.tgz` file.
- The filesystem inside of a transaction (IAT) requires both the Salt client and the `salt_state.tgz` because the execution must happen in a transaction.

This poses a problem: on TU systems, Salt needs to coordinate files between the IAT and OOT filesystems.

## Solution

There are two Salt modules that modify the filesystem:

- `state` (e.g. `state.apply`)
- `transactional_update` (e.g. `transactional_update.apply`)

Users should use the `state` module modify OOT filesystem, and the `transactional_update` module to modify the IAT filesystem.

Because `state` module will not use transactions, it requires no changes for Salt SSH to work.
However, the `transactional_update` module requires:

1. a Salt SSH wrapper to prepare and transfer the `salt_state.tgz` file
2. to implement the `pkg` function, which executes the `salt_state.tgz` file
3. to implement a synchronization mechanism that copies Salt and the `salt_state.tgz` file into the transaction

Steps 1. and 2. for the `transactional_module` are equivalent to the `state` module:

1. [state's SSH wrapper](https://github.com/openSUSE/salt/blob/openSUSE/release/3006.0/salt/client/ssh/wrapper/state.py)
2. `transactional_module` can delegate execution to `state.pkg` once in a transaction with all the necessary files

For step 3, this RFC proposes the following mechanism:

- When `transactional_update.pkg` function is called, it first deploys itself from whatever location Salt initially is on a minion (e.g. `/var/tmp/.root_12345_salt`) to `/var/cache`.
  - In case of a traditional Salt, `transactional_update` generates a thin Salt client into `/var/cache`.
  - In case of a Salt Bundle (`venv-salt-minion`), `transactional_update` copies the directory from which Salt is currently executed, e.g. `/var/tmp/venv-salt-minion` to `/var/cache`. Consequently, `transactional_update` must also fix the shebangs in the new `/var/cache` copy.

> [!NOTE]
> In TU systems, the `/var/cache` location is shared between the IAT and OOT filesystems, which is why it serves as a synchronization point.

- After deploying a copy of Salt into `/var/cache`, `transactional_update` also copies the `salt_state.tgz` file to `/var/cache`.
- Then, the Salt process outside of a transaction (_Salt_OOT_) starts a new Salt process inside of a transaction (_Salt_IAT_), which now executes `state.pkg`.
- After the Salt_IAT process finishes, it passes the execution result to Salt_OOT.
- Salt_OOT deletes the Salt copy from the `/var/cache` location, and returns execution result to Salt master.

# Drawbacks
[drawbacks]: #drawbacks

- Greater resource requirements: each execution of Salt SSH deploys a Salt client to the temporary `/var/cache` location, executes a new Salt process, and removing the temporary Salt client at the end of the execution. This means increased storage footprint (both RAM and disk), as well as added CPU cycles related to copying and cleaning up Salt.

# Alternatives
[alternatives]: #alternatives

- Not supporting Salt SSH on TU systems.
- We considered alternative approaches to synchronizing the Salt_IAT and Salt_OOT instances, for example via a socket.

# Unresolved questions
[unresolved]: #unresolved-questions

