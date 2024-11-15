- Feature Name: How to package and upgrade to Salt 3008.x
- Start Date: 2024-10-31

# Summary
[summary]: #summary

This RFC describes the preparation and strategy to upgrade Salt to the upcoming 3008.x release (LTS).

# Motivation
[motivation]: #motivation

The upstream Salt project is aiming the future 3008.x release (LTS) for Autumn 2024. As we want Uyuni and SUSE Manager to align to the latest LTS version from Salt project, we need to prepare the strategy to drive this upgrade.

Particularly, this new 3008.x LTS release is the first version after [the great module migration](https://salt.tips/the-great-salt-module-migration/), and lot of Salt modules have been purged from the main Salt package in favor of [Salt Extensions](https://github.com/salt-extensions), including for example, the `zypperpkg` and `transactional_update` modules. Moreover this new Sal 3008.x release is not working anymore with Python 3.6, which is currently the Python version in SLE15 Basesystem where the classic Salt package resides.

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
- virt (needed by virtualization-formula)
- ...

These are the minimum required extensions to be able to do basic operations in SUSE/openSUSE distributions and also allow basic operations on the context of SUSE Manager clients. We must maintain and support these builtin Salt Extensions.

This list could be reduced even more by just providing the `zypperpkg` and `transactional_update` modules and then providing the rest via `/usr/share/susemanager/salt/[_modules,_states,...]` in the Uyuni / SUSE Manager server.

Builtin Salt Extensions will be integrated into our main "openSUSE/salt" GitHub repo codebase for 3008.x, and provided as content of the main `python311-salt` package.

#### An example of the Git repo:
```
salt
|-- builin-extensions
|   |-- saltext-zypperpkg
|   |-- saltext-dpkg
|   |-- ...
...
```

The idea would be to include the releases for the different builtin extension directly inside our GH repo, as it was previously done with "tornado". We should take this oportunity also to take the ownership, migrate and create the official `saltext-zypperpkg` extension and probably some others.

These builtin extensions will be then placed in `/usr/lib/python3.11/site-packages/saltext/` when installing `python311-salt` so they are available for Salt.

**NOTE:** Depending on the maintaining workflow to use, the usage of `git submodule` would make it a bit tricky when it comes to generate patches (i.a. during bugfixing) for the single unified Salt codebase, as apparentely you cannot get an unified diff for the main repo + submodules.

Alternatively, we could create separated packages for each of those default Salt Extensions and then make add them as `Requires` for the `python311-salt` package. In that case, an official Salt Extensions must be created (if not existing) for each extension we want to have a package, and then taking the sources from the official extension repository. One Salt Extension, one RPM package.

### What about Salt Extensions packages?

Essentially there are some different approaches here:

1. Creating separated packages for each one of the Salt Extensions (potentially hundreds) -> maybe too cumbersome if we go with all of them, and probably not really needed.
2. Do not package Salt Extensions at all -> builtin extensions + manual customization.
3. Only package a reduced list of Salt Extensions -> we could consider some popular extensions that we should then maintain in the context of SLE.

With option 1, we do package and do support all those extensions we decide to have a package for. On the other hand, with option 2, we do only take care of maintaing and supporting the reduced list of builin extensions (actually integrated in the main `python311-salt` package), and then users and customers would need to rely on extending with their desired extensions coming from the community.

In case of packaging certain list of Salt Extensions, those will be available as RPM packages, allowing the ability to install those packaged ones in an system without access to internet or PyPI. Additionally, providing extensions via Salt Master file roots is also a valid option for disconnected setups.

## Customizing your Salt package

As described by Salt [here](https://salt.tips/the-great-salt-module-migration/), starting with Salt 3008, both Salt Master and Minion can be extended by using `salt-pip` or `pip.installed` to install the Salt Extensions packages (`saltext-*`). Similar to the extending mechanism we currently have for the Salt Bundle. This makes it easy to integrate the customization of your minions with Uyuni an SUSE Manager, as based on a Salt state.

If a Salt Extension is not existing yet (as most of the dropped modules are NOT yet migrated to Salt Extensions), they mention to provide them as custom modules in your Salt state tree (file_roots), i.a. `/srv/salt` as users alreayd do when extending Salt with their custom modules.

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

NOTE: SLMicro 6.0 works differently than SLE15, as it does contain Python 3.11 in the base channels.

#### Other OSes where we still ship the classic Salt package:
- SLE12 (Adv. System Administration Module): Do not upgrade to Salt 3008 - this module is already EOL and not included in LTSS. Salt Bundle only.
- Ubuntu 20.04 (client tools): Do not upgrade to Salt 3008 - drop the classic Salt package for the new 5.1 client tools. Salt Bundle only.
- RHEL8 and clones (client tools): Do not upgrade to Salt 3008 - drop the classic Salt package for the new 5.1 client tools. Salt Bundle only.

#### Salt Bundle:
The upgrade of Salt Bundle to 3008 will happen for all Uyuni and SUSE Manager supported client OSes via their respective client tools channels at the same time that we upgrade Salt in SLE15.

### New dependencies for Salt 3008.

There are new dependencies that are not available as part of "SLE-Module-Python3", and we will need to take it from Factory or some other SLE/ALP source to include them either in the "SLE-Module-Python3" (check with SLE PMs) or via the new "SLE-Module-Salt" module.

#### Runtime:
- `python-networkx` + its dependencies: `python-matplotlib`, `python-pandas`, `python-scipy`, `python-FontTools`)
- `python-tornado6`

#### BuildTime:
- `python-networkx` -> `python-pydot`, `python-pygraphviz`, `graphviz`
- `python-meson-python` -> `meson`, `patchelf`
- `python-pandas` -> `python-versioneer-toml`
- `python-scipy` -> `python-pythran`

A testing build project can be found [here](https://build.opensuse.org/project/show/home:PSuarezHernandez:branches:systemsmanagement:saltstack:products:next), based on the current upstream Salt `master` branch (target for 3008 release).

## Maintaining Salt

Given the irruption of Salt Extensions, we need to rethink the current workflow we use for maintaining Salt (and now also some of its extensions). In this regard, we want to improve our workflow, to make it simpler and adapted to the new Salt Extensions scenario and aligned with SUSE & OBS proposed workflows.

As this section has itself enough significance, it will be covered in a dedicated RFC around "New SCM workflow for Salt", so discussion around this topic can happen separetely to the present RFC.

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

The proposed plan:
- Prepare Salt 3006.0 package based on Python 3.11.
- Drop Salt from Basesystem / Server Application modules for SP7 before feature cut-off. (ECO needed)
- Create the new "SLE-Module-Salt" module for SP4/5/6/7 based on "SLE-Module-Python3", containing the current Salt 3006.0 based on Python 3.11.
- Deprecate Salt from Basesystem / Server Applicacion module in favor of Salt coming from "SLE-Module-Salt" for SP4/5/6. (ECO needed)
- Once 3008 is finally released, we can upgrade Salt in "SLE-Module-Salt" module.

## Salt version in Uyuni and SUSE Manager

The Uyuni and SUSE Manager server gets the Salt Master package from the OS repositories/channels (either Leap or SLE), and we have the restriction that Salt Master version must be always equal or higher than the Salt version in the minions.

Under these premises, depending on when Salt 3008 is released, these are the alternatives we have:

a) If Salt 3008 is ready before "last MU-1" for SUMA 4.3 (~February-March 2025?) -> Upgrade to Salt 3008 in SP4/5/6/7 in "last MU-1":
  - 4.3 LTS will contain 3008.
  - 5.0 gets 3008 around the middle of its lifecycle (Feb-March 2025).
  - 5.1 is released with 3008 (June 2025).
  - Salt Bundle (shared between 4.3 and 5.0) gets upgraded to 3008 (Feb-March 2025).
  - Salt Bundle (new client tools for 5.1) gets upgraded to 3008 (Feb-March 2025).
  - Uyuni will get automatically 3008 from SLE into Leap (Feb-March 2025).
  - Cons: potential bugs in inmature 3008.0 release and not much time for 3008.0 validation.

b1) If Salt 3008 is NOT ready when SUMA 4.3 LTS begins (June 2025) -> We keep Salt 3006.0 on SP4 until LTS ends (June 2026):
  - SP5/6/7 gets 3008 (after June 2025) -> probably no-go as that mean SP5/SP6 managed minions will break for 4.3 LTS.
  - 4.3 LTS cannot manage newer SPs with Salt 3008 (after June 2025).
  - 5.0 gets 3008 at some point after the middle of its lifecycle (after June 2025).
  - 5.1 is released with 3008 (June 2025).
  - Salt Bundle (shared between 4.3 and 5.0) is never upgraded to 3008 before 4.3 LTS is EOL (June 2026).
  - Salt Bundle (new client tools for 5.1) gets upgraded to 3008 (June 2025).
  - Uyuni will get automatically 3008 from SLE into Leap (June 2025).
  - Current upstream Salt 3006 EOL date is January 2026, but potentially extended if 3008 is delayed, so worst scenario we are 6 months in our own (probably less).

b2) If Salt 3008 is NOT ready when SUMA 4.3 LTS begins (June 2025) -> We keep Salt 3006.0 for all SPs until LTS ends (June 2026):
  - 4.3 LTS is able to manage newer SPs, as they still have Salt 3006.0.
  - Once 4.3 LTS is EOL, we upgrade Salt 3008 in all SPs.
  - 5.0 does not get 3008 before its EOL. (June 2026).
  - 5.1 is released with Salt 3006.0 and gets 3008 in the middle of its lifecycle (June 2026).
  - 5.2 is released with 3008 (June 2026)
  - Salt Bundle (shared between 4.3 and 5.0) is never upgraded to 3008 before 4.3 LTS is EOL (June 2026).
  - Salt Bundle (new client tools for 5.1) gets upgraded to 3008 (June 2026).
  - Uyuni will get automatically 3008 from SLE into Leap (June 2026).
  - Current upstream Salt 3006 EOL date is January 2026, but potentially extended if 3008 is delayed, so worst scenario we are 6 months in our own (probably less).
  - As soon as 3008 is ready, we can start validating it during development of 5.2 before 4.3 LTS has ended.
  - Pros: more stable and mature Salt 3008.x package + more validation time for 3008.x.

Initial agreement has been made within the Team to follow option "b2".


| Scenario | Description | Salt 3008 Release | SUMA 4.3 LTS (SP4) | SP5 | SP6 | SP7 | SUMA 5.0 | SUMA 5.1 | SUMA 5.2 | Salt Bundle (4.3/5.0) | Salt Bundle (5.1) | Uyuni |
|---|---|---|---|---|---|---|---|---|---|---|---|---| 
| A | Upgrade all to 3008 early. | Before Feb-Mar 2025 | 3008 | 3008 | 3008 | 3008 | 3008 | 3008 | 3008 | 3008 | 3008 | 3008 |
| B1 | Keep 3006 on 4.3 LTS (SP4), upgrade later SPs. | After June 2025 | 3006 | 3008 | 3008 | 3008 | 3006 (initially) upgraded to 3008 in mid-lifecycle | 3008 | 3008 | 3006 | 3006 (initially) gets 3008 after June 2025 | 3008 |
| B2 | Keep 3006 on all SPs, and upgrade all to 3008 after 4.3 LTS ends.| After June 2025 | 3006 | 3006 | 3006 | 3006 | 3006 | 3006 (initially) upgraded to 3008 in mid-lifecycle after June 2025 | 3008 | 3006 | 3006 (initially) upgraded to 3008 after June 2026 | 3006 (initially) gets 3008 in June 2026| 


# Unresolved questions
[unresolved]: #unresolved-questions

- Would lifecycle of "SLE-Module-Python3" module for the different SPs of SLE15 affect us somehow, either from SLE PM or Maintenance side?
