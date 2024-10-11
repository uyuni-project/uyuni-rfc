- Feature Name: MicroOS Management
- Start Date: 2026-02-23

# Summary
[summary]: #summary

Improve the management of [openSUSE MicroOS](https://microos.opensuse.org) and similar systems (e.g. openSUSE Leap Micro and SUSE
Linux Micro) in Uyuni.

# Detailed design
[design]: #detailed-design

## Uyuni does not use `transactional_update` executor anymore
The smallest unit Salt can handle is the SLS file. To control which SLS files are applied in a
transaction or not, Uyuni stops relying on the `transactional_update` executor. Instead, Uyuni either
calls `state.apply $list_of_sls_files` or `transactional_update.apply $list_of_sls_files`.

All internal states that interact with the live system are applied with `state.apply.`. Internal states
that change the operating system, e.g. by installing packages, are applied with
`transactional_update.apply`. Today, many of our SLS files combine installing and using packages. 
That does not fit the transactional model and we need to split these SLS files.

Custom states give users a lot of flexibility managing their systems, which makes it hard for Uyuni
to know how to apply custom states. To give some control to the user, we add a new config value:
`java.salt_custom_states_use_transactional_update = True`. This config value controls whether
`transactional_update.apply` is used for all custom states applied from the Java backend. The
default is `true`, which is the same behavior as today, to keep backwards-compatibility with
existing SLS files.

### Internal States Filesystem Structure
Up to now, we bundle prerequisites (e.g. package installations) with the main part in SLS files.
Since that does not work on transactional, we're now using the following structure:

``` text
hardware/
        prereq.sls
        profileupdate.sls
ansible/
        prereq.sls
        runplaybook.sls
```

### Internal States Application
The Java backend maintains a list of SLS files in the `SaltParameters` class. This catalog will be
enhanced with a hard-coded mapping of SLS files to the respective Salt function (`state.apply` or
`transactional_update.apply`).

Some states need to be split into two SLS files, one for prerequisites and a second for the actual
work. The Java backend code first trigger the prerequisites state. When that job returns
successfully, Uyuni reacts with the "actual work" state without any further user interaction.

### Internal States - `state.apply`
- `actionachains.{startssh,resumessh}`
- `ansible.runplaybook`
- `bootstrap.set_proxy`
- `cleanup_minion` (works with both)
- `cleanup_ssh_minion`
- `hardware.profileupdate`
- `hardware.virtprofile`
- `images.*`
- `packages.profileupdate`
- `packages.redhatproductinfo`
- `proxy.apply_proxy_config`
- `reboot`
- `services.docker`
- `services.kiwi-image-server`
- `services.reportdb-user`
- `services.salt-minion`
- `srvmonitoring.disable`
- `srvmonitoring.enable`
- `srvmonitoring.status`
- `supportdata.gather` (new)
- `util.disable_fqdns_grain`
- `util.mgr_mine_config_clean_up`
- `util.mgr_rotate_saltssh_key`
- `util.mgr_start_event_grains`
- `util.sync*`
- `util.systeminfo`
- `util.systeminfo_full`

### Internal States - `transactional_update.apply`
- `ansible.prereq` (renamed from `init.sls`)
- `certs`
- `channels` (installs packages)
- `cleanup_minion` (works with both)
- `distupgrade`
- `hardware.prereq` (new)
- `packages.patch*`
- `packages.pkg*`
- `packages.prereq` (renamed from `init.sls`)
- `services.docker_prereqs`
- `services.kiwi-image-server_prereqs`
- `services.reportdb-user_prereqs`
- `services.salt-minion_prereqs`
- `supportdata.prereq` (renamed from `init.sls`)
- `switch_to_bundle.mgr_switch_to_venv_minion`
- `update-salt`
- `util.mgr_switch_to_venv_minion`


### Unsupported Internal States
Not all internal states we have make sense on MicroOS / SUSE Linux Micro. These states are unsupported.

- `appstreams.configure` - only useful for RHEL systems
- `bootstrap.remove_traditional_stack` - traditional stack was never supported on these systems
- `cocoattest.requestdata`- only supports SLES 15 SP6
- `rebootifneeded` - The way this is written is incompatible with transactional systems
- `uptodate` - The way this is written is incompatible with transactional systems

### Configurable States (`java.salt_custom_states_use_transactional_update`)
These states could either be applied with `state.apply` or `transactional_update.apply`. The Java
backend code consults `java.salt_custom_states_use_transactional_update` to decide how to apply them.

-   `custom`
-   `custom_groups`
-   `custom_org`
-   `recurring`
-   `remotecommands`

### Required Changes
- Extract `dmidecode` installation steps in `hardware.profileupdate` to `hardware.prereq`
- Split `services.*` states and extract package installation steps

### States not yet categorized
- `bootstrap.autoinstall`
- `channels.gpg-keys`
- `scap` NOTE: `remediate=True` is likely OS-altering
- `configuration.*` depends on path to the deployed/analyzed file

## Automatic reboots during bootstrapping
Uyuni bootstraps new systems through different mechanisms: `state.apply` over Salt SSH, running a
bash script, or by reacting to a newly connected Salt Minion. During the bootstrap procedure, Uyuni
installs the Salt Bundle on the client. This requires a reboot of transactional systems.

### `state.apply` over Salt SSH
This is the mechanism used when users navigate to "Systems > Bootstrapping" in the WebUI.

Uyuni targets the new system with Salt SSH and always uses `state.apply` to apply the `bootstrap`
state. This is required because Uyuni relies on information collected on the client system to know
what kind of system it is. This includes finding out if the new system is a transactional system.
The `bootstrap`state install our Salt Bundle package correctly on both traditionally-managed and
transactional systems.

Triggering a reboot over Salt SSH has one problem: rebooting before Salt finishes loses the job data
of the `bootstrap` state. This can be avoided by systemd feature called "Inhibitor Lock", which can
delay a shutdown request while Salt SSH runs.

#### Add Inhibitor Lock to Salt SSH
Applications can set _inhibitor locks_ to block or delay system shutdown and sleep states. Salt SSH
will be changed to set a _delay_ inhibitor lock to stop the system from rebooting immediately. Salt
SSH has time to return job results back to the Salt Master, unless it takes longer than
_InhibitDelayMaxSecs_. This config setting is specified in `logind.conf(5)` and can't be overridden
by Salt SSH. The default is 5 seconds. When Salt SSH requires more than 5 seconds to return the job
data, we still lose it and can't proceed with the bootstrapping procedure.

#### Request a reboot
With a delay inhibitor lock taken, the `bootstrap` state requests a reboot from systemd. Systemd
will accept the request immediately but delay the shutdown until the Salt SSH execution terminates
and releases the inhibitor lock.

### Bootstrap script
The bootstrap bash script already handles rebooting the system after installing the Salt Bundle.

### "Salt-initiated" bootstrap
This method is used by users with large environments. They often have their own custom OS images and
want to bootstrap new systems with little manual intervention.

This bootstrap only needs to install the Salt Bundle when it is executed with the Salt Minion from
the distribution. As part of the bootstrap procedure, a Salt highstate will replace the installed
Salt Minion package with our Salt Bundle package. Users are advised to include the Salt Bundle into
their OS images to avoid the reboot after switching from the distribution's Salt Minion to Salt Bundle. 

## Expose System Snaphot information in Uyuni

openSUSE distributions and their commercial downstream distributions (e.g. SUSE Linux Enterprise)
use btrfs for their root file system. openSUSE MicroOS is designed around btrfs snapshots. Uyuni's
WebUI and API will be enhanced to show snapshot information of all managed systems that use btrfs snapshots.

Salt includes an execution module to interact with `snapper`, a snapshot management tool for btrfs
snapshots. In particular, `snapper.list_snapshots` and `snapper.diff` expose information about
available snapshots and how they differ.

To store snapshot information, the database table`rhnServer` gets new columns:
  ```sql
  active_snapshot     NUMERIC,
  default_snapshot    NUMERIC,
  snapshots           NUMERIC[]
  ```
NOTE: snapshots is an array instead of its own table because we don't need to store metadata about each snapshot

Salt's `snapper.list_snapshots` gets improved to include `active` and `default` keys that indicate
if a snapshot is currently active and/or the snapshot the next system boot will use.


# Bug Fixes
## Make state functions available for transactional systems
`service.enabled` and `service.disabled` currently need a dbus connection. Dbus is not available
inside a transaction since transactions must not be able to break the live system.

The `service`state module will be changed to work without a dbus connection for these operations.

## Snapper is not Python 3 compliant
`changed_files` returns a `dict_keys` view instead of a list.

# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?
* More work for us maintaining SLS files with the new layout, as we need to think were to put different states
* We don't know if all features need to work for transactional systems since they are managed differently.

# Alternatives
[alternatives]: #alternatives

- Full control over custom states for the user. Requires changes to the WebUI / API and database
  schema. This is something we could do later if the global config approach is not enough.
- Support for two system states ("live" and "next") in the database, WebUI and API. This would allow
  users to know not only what the current live system looks like, but also how it will look like
  after a reboot. This is a lot of work, everything expects a system to be in a singular state all the time.
- Make sure a small subset of SLS files work on transactional systems and document the rest as unsupported.

# Unresolved questions
[unresolved]: #unresolved-questions

- What are the unknowns?
- What can happen if Murphy's law holds true?
