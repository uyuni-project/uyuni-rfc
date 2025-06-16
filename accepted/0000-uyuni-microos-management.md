- Feature Name: (fill with a unique ident, my_awesome_feature)
- Start Date: (fill with today's date, YYYY-MM-DD)

# Summary
[summary]: #summary

Improve the management of openSUSE MicroOS in Uyuni.

# Motivation
[motivation]: #motivation

MicroOS, or the downstream SLE Micro, is a different operating system than e.g. SLES. It is based on the same tools and packages, with few additions on top. These additions are few, but completely change the operating model.

The main idea is: **All changes go into a new btrfs snapshot. This new snapshot is "pending" until a reboot activates it.**

Until now, we tried to hide the differences in Uyuni and relied on Salt to do the *right thing*. This strategy was easy for us to use, but it did not work well. We need to change the approach we take with transactional systems.

# Detailed design
[design]: #detailed-design

## Uyuni differentiates between OS-unchanging and OS-altering operations
Instead of using the `transactional_update` executor, Uyuni calls either `state.apply` or `transactional_update.apply`. Uyuni is in full control of which states are applied in a new snapshot and which states are not. The SLS file is the smallest unit Salt can handle, there is no way to apply only parts of an SLS file inside a snapshot. Therefore, we split SLS files that currently mix OS-unchanging and OS-altering operations.

The operations below map to SLS files. The syntax used for operations in this document is the same that's used in for Salt `top.sls`.

### Multiple approaches to running operations

Uyuni's WebUI and API are changed to expose the different ways of running operations, based on the categorization below.

1. `state.apply <mods>`
2. `transactional_update.apply <mods>`
3. `transactional_update.apply <mods> activate_transaction=True`

Previously, everything used the first way (`state.apply`). To enable the new ways that use `transactional_update`, the Java code needs to be updated. The job result of `transcational_update.apply` is compatible with `state.apply`, only the function that's called needs to be changed.

Built-in operations that in the "OS-unchanging operations" section are executed with `state.apply`, "OS-altering operations" are executed with `transactional_update.apply`. Some operations, like those defined by users, need to ask the user how they should be executed.

The WebUI for custom states, recurring states, remote commands and oscap are changed to let the user decide which option should be used. The difference between 2. and 3. could be implemented with a checkbox.

Like the WebUI, the API needs to be adapted to allow the user to choose, e.g. how recurring states are applied.

### Uncategorized operations

- `virt.*`: About to be dropped
- `bootloader`: TODO
- `rebootifneeded` - The way this is written is incompatible with transactional systems

### OS-unchanging operations

These operations do not alter the system, i.e. they don't belong in a (new) snapshot. Uyuni applies them with `state.apply` for two reasons: structured output and no concurrency (`queue=True`).

- `ansible.runplaybook`
- `cocoattest.requestdata`
- `hardware.profileupdate`
- `images.*`
- `packages.profileupdate`
- `packages.redhatproductinfo`
- `srvmonitoring.status`
- `util.sync*`
- `util.systeminfo_full`
- `util.systeminfo`

#### Required Changes

- Extract installation steps in `cocoattest` to a new SLS
- Extract `dmidecode` installation steps in `hardware.profileupdate` to a new SLS

### OS-altering operations

These operations alter the operating system itself, i.e. they belong in a (new) snapshot. Uyuni applies them with `transactional_update.apply`, unless otherwise noted.

- `ansible`
- `appstreams.configure`
- `bootstrap` - special case, it's always applied with `state.apply` because Uyuni does not know if the target uses `transactional-update`
- `certs`
- `channels`
- `cleanup_minion`
- `cleanup_ssh_minion`
- `configuration.deploy_files` NOTE: reconfiguring a service through `/etc` is special as there is an overlayfs.
- `distupgrade`
- `packages.patch*`
- `packages.pkg*`
- `packages`
- `reboot`
- `services.docker`
- `services.kiwi-image-server`
- `services.reportdb-user`
- `services.salt-minion` REVIEW: Is all of this still needed? NOTE: `file.managed` in `/etc`
- `srvmonitoring.disable`
- `srvmonitoring.enable`
- `switch_to_bundle`
- `update-salt`
- `uptodate`
- `util.disable_fqdns_grain`: NOTE: configures in `/etc`, restarts a service (currently broken)
- `util.mgr_mine_config_clean_up`: NOTE: configures in `/etc`, restarts a service (currently broken)
- `util.mgr_rotate_saltssh_key`
- `util.mgr_start_event_grains` NOTE: configures in `/etc`
- `util.mgr_switch_to_venv_minion`

### Either OS-unchanging or OS-altering operations

These operations can be either OS-unchanging or OS-altering because they are to generic to know ahead of time. Users need to have control over the way these Salt states are applied.

-   `custom`
-   `custom_groups`
-   `custom_org`
-   `recurring`
-   `remotecommands`
-   `scap` NOTE: `remediate=True` is likely OS-altering

## Automatic reboots during bootstrapping

When bootstrapping a new system, Uyuni relies on information present on the client system to know what kind of system it is. This includes finding out if the new system is a transactional system. Bootstrapping happens with Salt SSH and `state.apply`. The bootstrap SLS file contains logic to install our Salt Minion package correctly on both traditionally-managed and transactional systems.

The bootstrap SLS file installs the Salt Minion package into the next snapshot. We need to reboot the Minion after installing this package.

### Add Inhibitor Lock to Salt SSH

Applications can set _inhibitor locks_ to block or delay system shutdown and sleep states. Salt SSH sets a _delay_ inhibitor lock to stop the system from rebooting immediately. Salt SSH has time to return job results back to the Salt Master, unless it takes longer than _InhibitDelayMaxSecs_. This config setting is specified in `logind.conf(5)` and can't be overridden by Salt SSH. The default is 5 seconds.

### Request a reboot without delay

With a delay lock taken, `bootstrap/init.sls` can request a reboot from systemd from the main process. The reboot will be delayed until Salt SSH execution terminates and releases the lock.

## Make state functions available for transactional systems

-   `service.enabled`: currently needs dbus, we need a way that does not require dbus for enabling the service
-   `service.disabled` currently needs dbus, we need a way that does not require dbus for enabling the service


# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?

  * obscure corner cases
  * will it impact performance?
  * what other parts of the product will be affected?
  * will the solution be hard to maintain in the future?

# Alternatives
[alternatives]: #alternatives

- What other designs/options have been considered?
- What is the impact of not doing this?

# Unresolved questions
[unresolved]: #unresolved-questions

- What are the unknowns?
- What can happen if Murphy's law holds true?
