- Feature Name: How to package and upgrade to Salt 3008.x
- Start Date: 2024-10-31

# Summary
[summary]: #summary

This RFC describes the preparation and strategy to upgrade Salt to the upcoming 3008.x release (LTS).

# Motivation
[motivation]: #motivation

The upstream Salt project is aiming the future 3008.x release (LTS) for Autumn 2024. As we want Uyuni and SUSE Manager to align to the latest LTS version from Salt project, we need to prepare the strategy to drive this upgrade.

Particularly, this new 3008.x LTS release is the first version after [the great module migration](https://salt.tips/the-great-salt-module-migration/), and lot of Salt modules have been purged from the main Salt package in favor of [Salt Extensions](https://github.com/salt-extensions), including for example, the `zypperpkg` and `transactional_update` modules.

At this point in time, only few modules have been already migrated to Salt Extensions, a lot of other modules are still waiting at [community-extensions-holding repository](https://github.com/salt-extensions/community-extensions-holding) to be migrated.

The purpose of this RFC is to define:
- Salt and Salt Extensions packaging strategy.
- How to customize the Salt package with more extensions.
- New dependencies required for Salt.
- How to release Salt 3008.x to SLE.
- How to maintain Salt 3008.x going forward.

# Detailed design
[design]: #detailed-design

## Packaging

Due the great module purge, we need to rethink the way we package Salt, as lot of the modules are been dropped and Salt Extensions are stepping in now.

As upstream Salt project wants to drops the support from their side in favor of [community driven support](https://github.com/salt-extensions#what-are-salt-extensions) and lifecycle for the different Salt Extensions, this raises the question about which of them do we want to include and support.

At the time of writting this RFC, most of the modules dropped from the Salt core are not yet migrated to Salt Extensions, therefore nobody from the community has claimed their ownership yet.

### Builtin Salt Extensions

There are a couple of Salt Extensions that we want to have integrated by default in our main `python311-salt` package. These are:
- zypperpkg
- dpkg
- transactional_update
- openscap
- docker / dockerng
- ...

These are the minimum required extensions to be able to do basic operations in SUSE/openSUSE distributions and also allow basic operations on the context of SUSE Manager clients. We must maintain and support these builtin Salt Extensions.

This list could be reduced even more by just providing the `zypperpkg` and `transactional_update` modules and then providing the rest via `/usr/share/susemanager/salt/[_modules,_states,...]` in the Uyuni / SUSE Manager server.

Builtin Salt Extensions will be integrated into our main "openSUSE/salt" GitHub repo codebase for 3008.x, and provided as content of the main `python311-salt` package.

Alternatively, we could create separated packages for each of those default Salt Extensions and then make add them as `Requires` for the `python311-salt` package. In that case, an official Salt Extensions must be created (if not existing) for each extension we want to have a package, and then taking the sources from the official extension repository. One Salt Extension, one RPM package.

### What about Salt Extensions packages?

Essentially there are some different approaches here:

1. Creating separated packages for each one of the Salt Extensions (potentially hundreds) -> maybe too cumbersome if we go with all of them, and probably not really needed.
2. Do not package Salt Extensions at all -> builtin extensions + manual customization.
3. Only package a reduced list of Salt Extensions -> we could consider some popular extensions that we should then maintain in the context of SLE.

With option 1, we do package and do support all those extensions we decide to have a package for. On the other hand, with option 2, we do only take care of maintaing and supporting the reduced list of builin extensions (actually integrated in the main `python311-salt` package), and then users and customers would need to rely on extending with their desired extensions coming from the community.

In case of packaging certain list of Salt Extensions, those will be available as RPM packages, allowing the ability to install those packaged ones in an system without access to internet or PyPI. Additionally, providing extensions via Salt Master file roots is also a valid option for disconnected setups.

## Customizing your Salt package

As described by Salt [here](https://salt.tips/the-great-salt-module-migration/), starting with Salt 3008, both Salt Master and Minion can be extended by using `salt-pip` or `pip.installed` to install the Salt Extensions packages (`saltext-*`). Similar to the extending mechanism we currently have for the Salt Bundle.

If an extension is not existing (as most of the dropped modules are NOT yet migrated to Salt Extensions), they mention to provide them as custom modules in your Salt state tree (file_roots).

As mentioned above, we would be probably providing a main Salt package containing some builtin extensions already there that at least covers basic operations.

## Releasing the new Salt

Salt 3008 won't support Python 3.6, so we cannot use the main Python 3.6 interpreter from SLE15 or Leap15, we need to make it to be based on Python 3.11.

Besides of adapting the Salt specfile to build using Python 3.11, by using singlespec adaptations at https://github.com/openSUSE/salt-packaging/pull/96 (and related PRs), we need to take some actions when it comes to how this new version would be distributed in SLE15 and Leap15:

#### SLE15:
- A new custom "SLE-Module-Salt" module (inherited from SLE-Module-Python3) will be created for SLE15SP4/5/6/7.
- The new Salt 3008.x package will be shipped via the new "SLE-Module-Salt" together with its any new dependency which is not part of the "SLE-Module-Python3" module.
- The old Salt 3006.0 package in SLE15SP4/5/6 will be deprecated in favor of the new version coming in the new "SLE-Module-Salt".
- The old Salt 3006.0 package will be dropped from SLE15SP7 Basesystem and Server Application modules before SLE15SP7 feature cutoff.

#### Leap15:
- Python 3.11 is already available in Leap.
- The new Salt and any new dependencies will get into Leap from SLE.

### New dependencies for Salt 3008.

There are new dependencies that are not available as part of "SLE-Module-Python3", and we will need to take it from Factory or some other SLE/ALP source to include them either in the "SLE-Module-Python3" (or via the new "SLE-Module-Salt" module.

#### Runtime:
- `python-networkx` + its dependencies: `python-matplotlib`, `python-pandas`, `python-scipy`, `python-FontTools`)
- `python-tornado6`

#### BuildTime:
- `python-networkx` -> `python-pydot`, `python-pygraphviz`, `graphviz`
- `python-meson-python` -> `meson`, `patchelf`
- `python-pandas` -> `python-versioneer-toml`
- `python-scipy` -> `python-pythran`

A testing build project is here: https://build.opensuse.org/project/show/home:PSuarezHernandez:branches:systemsmanagement:saltstack:products:next
Based on the current upstream Salt `master` branch (target for 3008 release)

## Maintaining Salt

TBD

# Drawbacks
[drawbacks]: #drawbacks

The current Salt version used in Uyuni and SUSE Manager is `3006.0` LTS (together with SUSE patches). The EOL for 3006 LTS is currently set by upstream to January 31st 2026.

We should move the Salt version to 3008.x (LTS) at some point before 3006.x is EOL, in order to be covered by Salt upstream support.

If we don't upgrade eventually to the next supported LTS version of Salt, then we would be in our own having to maintain and backport potential security issues detected by Salt into this upstream unsupported version. We want to avoid this situation as much as we can.

Our ultimately goal is to have the Salt version used in Uyuni and SUSE Manager always aligned with the latest upstream supported LTS version of Salt.

# Alternatives
[alternatives]: #alternatives

Since Salt 3008.x release has been delayed and it is not yet fully clear when it would be, there are some risks that we cannot proceed with the upgrade to Salt 3008.x within some important deadlines when it comes to SUSE Manager and SLE.

1. Stick to the current Salt 3006.0 forever -> no go.
2. Stick to Salt 3006.0 until 3008 is released -> this will be the way to go if 3008.x is not released on time.

**IMPORTANT: Since we want to drop the Salt 3006.0 from the Basesystem and Server Application modules for SLE 15 SP7 (based on Python 3.6), in favor of a new Salt based on Python 3.11, even if 3008 is delayed we should NOT compromise the SLE 15 SP7 feature cutoff deadline to implement the new "SLE-Module-Salt" module even if it still provides 3006.0 version**

# Unresolved questions
[unresolved]: #unresolved-questions

- TBD
