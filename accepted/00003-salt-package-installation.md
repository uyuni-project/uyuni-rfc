- Feature Name: Salt Package Installation
- Start Date: 2015-10-22
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

Admins need to manage the installed software on their servers (minions).

This RFC proposes a different paradigm to manage software on a minion, taking
full advantage of Salt states.

Instead of scheduling package installation jobs, the admin will edit a Salt state that specifies how the system should look like in terms of software. Once the Salt state is ready, Salt will take care of the rest.

# Motivation
[motivation]: #motivation

Having Salt as the engine of SUSE Manager allows us to perform various tasks in a
simpler way.

We can make software management a particular case of configuration management.

The use cases we will support:

* Installing from available packages
* Upgrading from available packages
* Rolling back to a previous set of packages
* Preventing that certain packages are installed

The expected outcome is:

* Multiple package operations including install, upgrade, locking, rollback, etc, can be reduced to a simple place
* Everything will be operated in a declarative view
* The representation of a Salt state will be in the database which can be manipulated, exported, etc
* Easier to build workflows. For example, an update model can easily be built out of:
  * a state with all packages set to "latest"
  * a cloned channel with tested updates

## Configuration Management

A Salt state containing package definitions can be associated with individual systems, however, because we are doing Configuration Management, such state could as well be part of a Group definition or a grain match.

# Detailed design
[design]: #detailed-design

## Package Salt state

A Salt state as represented in the SUSE Manager database is equivalent to, and can be compiled to, an SLS file.

* The package Salt state will be separated from the individual minions' states.
* One will be able to create a package Salt state with just a name.

From now on installing packages means altering the package Salt state - in other words which packages *should* be installed and which ones *should not*.

# Installation

Below is a description of _defined state_. This should be differentiated from a _single event_ or an _action_. A defined state is not a single one-time action, but instead it keeps persisting on the system, if applied. Therefore it is essentially a system lock to a particular state.

It should be differentiated between the **model of the database** and the **User Interface**, where the concepts may differ.

* The user has the list of available packages.
* The user can select for each package a state

The representation of the _model of the database_ should be seen as follows:

* Not managed
* Installed version
* Latest
* Removed (configuration preserved)
* Purged (configuration removed)

The representation of the _User Interface_ should be seen as follows:
* Not managed (no actions taken, no tracking to the package)
* Installed (additionally with a specific verion and the operator _attributes_)
* Absent

The policies of the state:
* "installed" can support operator attributes over the version attribute, like `<`, `<=`, `>`, `>=` and `=` to the specific version. Or it can be `latest` (version) from the UI prespective. If "latest" attribute is chosen in the UI among the version, near "installed" state, then the verision operator is invalid and cannot be selected.
* "absent" can be either just absent or absent with the only specific version, same to the "installed" operations, which means "anything but this version conditions".

UI example, when the package is installed latest:

```
Package     Version          State
-------------------------------------------------------------------
foo        [Latest     [v]  [Installed   [v]
           | 1.0         |  |Absent        |
           | 2.0         |  ----------------
           ---------------
```

UI example, when the package is installed with the specific version (condition appears):

```
Package     Version         Condition          State
-------------------------------------------------------------------
foo        [1.0        [v]  [Equal       [v]   [Installed   [v]
           | Latest      |  |More than     |   |Absent        |
           | 2.0         |  |Less than     |   ----------------
           ---------------  |Less or equal |
                            |More or equal |
                            ----------------
```


Because of the nature of defined state, each of these selectable options essentially are locks, like in `/etc/zypp/locks`. For example *installed* is actually a lock, which freezes the package version, even if something else is going to update it. An option *Absent* is also a lock, which prevents the package installation. If an _installed_ package selected to "Absent", it indirectly locks it to be uninstalled _and_ preserved this way. At this point there is no way to uninstal and keep a package unmanaged within one operation. In order to release such lock in cases when the package will be required as a dependency by something else, the policy should be explicitly changed from "Absent" to "Not managed".

Orphan packages are packages that aren't available in any channel and are just already installed on a managed system from various untracked sources. These orphan packages still can be managed by two options:
* Kept on the system ("Keep the current version" lock)
* Removed ("Absent")

## Upgrading packages

* At the same time, the user can "upgrade" each package entry in the state (or the whole list)
  keeping the same policy.

## Versioning

* Each time the state is saved, a new version will be created in the database, lets say SaltStatePackages table.
* The initial version is empty, but can be imported from the current list of the installed for a certain Minion.

## Relationship between states and individual systems

There will be a specific place to create package Salt states.

Every state can be then be applied to a group, minion list or grain match.

There will be one state named after an specific minion that will be always applied only to that specific minion. When the user edits the Software tab of a minion, she will be editing this state. This is for convenience to avoid having to create N states for N minions and then assign them N times. This state would be the lower end of the chain.

## SLS file generation

The layout of SLS files is specified in [RFC#00005 Salt State Tree](https://github.com/SUSE/susemanager-rfc/blob/master/text/00005-salt-state-tree.md).

Once the package Salt state is saved, the corresponding SLS file will be generated:

* `/srv/susemanager/salt/susemanager/packages-$id.sls`

Where $id is the name of the state, which can be a minion name.

SUSE Manager will ship `/usr/share/susemanager/salt/susemanager/packages.sls` in case supporting code/state is needed.

When the highstate is applied, the packages will get installed, removed etc.

## Handling the External Tools
[exttools]: #exttools

Zypper, YaST or any software component that is using `libzypp` can operate packages and therefore change content on the managed machine. If that happens, the SUSE Manager and Salt should know that the state of the client machine (minion) has been changed outside of the Salt's defined state and synchronize with it.

### Requirements
[extrequirements]: #extrequirements

Handling the synchronization should meet the following requirements:

1. Should not cause issues and/or interfere with the existing operations of Zypper, YaST or any software component, using `libzypp` in any ways
2. Should reliably track package changes at least at `libzypp` level
3. Should minimize traffic and computation at the server side

### Cookie File
[cookie]: #cookie

Cookie file is a temporary file that serves for designating the state of the package set is in "dirty" state, where check needs to be done. The cookie file should be same as `libzypp` one:

```
  <checksum> <Unit time>
```
Checking the cookie file is merely to detect if the line had changed.
Path to the cookie file is used the same place where `libzypp` places its own, e.g.: `/var/cache/salt/minion/rpmdb.cookie`

### Tracking RPM Package Set Changes

In order to track package set changes within the components that are using `libzypp`, two different components are proposed:

1. A `libzypp` commit plugin, which generates data, covering the transaction begin and end and saves this data in the Cookie File.
2. A Salt Beacon that is firing an event, based on the data, left in the Cookie File by the plugin in the Step 1.

Process from the `libzypp` plugin side at the end of the transaction it should place in the Cookie File the following:

1. Checksum of the RPM Berkeley database files, located in `/var/lib/rpm/Packages` path
2. Timestamp when the transaction has ended

Process from the Salt Minion Beacon side:

1. Periodically check the content of the Cookie File
2. Save timestamp into its context (memory)
3. In case cookie data (the entire line) has been changed (or appeared at all), the event to the Master is fired

This de-coupled approach allows us to achieve:

* Plugin from the `libzypp` side will not block anything, since the plugin is not relying on any configuration and networking
* If Beacon blocks Minion at any reason, this issue stays isolated to the Minion component and is not affecting any component that is using `libzypp`
* No need to ship `libzypp` plugin in a separate package and extra-manage it

### Configuration of The Components

The plugin for the `libzypp` is shipped within the `salt-minion` package and installed as `/usr/lib/zypp/plugins/commit/susemanager`.
The corresponding Salt Beacon is shipped within the `susemanager-sls` package and installed on the SUSE Manager side to the `_beacons` the same way as other SUSE Manager-only components. The reason not including it to the `salt-minion` package is for easier client-side management and distribute it with the `susemanager-sls` package instead.

Configuration of the Beacon is possible in two ways:

1. Dropping a file to `/etc/salt/minion.d`
2. Add configuration data to the pillars

Pillar configuration is chosen due the fact that the pillar data behaves like a remote NFS mount: completely controlled from the server, reflecting everywhere. An example configuration of such Beacon, e.g. called "pkgsetmonitor" would be the following:

```
beacons:
  pkgsetmonitor:
    cookie: /var/cache/salt/minion/rpmdb.cookie
    interval: 5
```

Another way of the configuration is possible by simply a dropping config overlay as `/etc/salt/minion.d/suma_beacons.conf`.

# Status Display

When orphan packages are managed (either kept the current version or kept removed), they are by definition *unstable*, because there is no way to update them from a channel. System is considered *inconsistent* as long as kept orphan package is no longer installed or version changed manually.

# Drawbacks
[drawbacks]: #drawbacks

* Generation of SLS files may be time consuming

# Alternatives
[alternatives]: #alternatives

* A different alternative is to offer a similar software tab like the current one that translates directly to pkg.install calls.

# Unresolved questions
[unresolved]: #unresolved-questions

* When will the SLS file be generated?
  * at save time
  * scheduled
* When creating generic states
  * from which channels to show packages?
  * do we need channel assignment in the state?
  * Do we just treat packages as strings and always relative to the assigned channels?
