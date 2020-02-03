- Feature Name: Auto-disable skuba-update upon system bootstrap
- Start Date: 2020-02-03
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

Disable skuba-update upon registration to Uyuni/SUSE Manager.

# Motivation
[motivation]: #motivation

<!-- - Why are we doing this?
- What use cases does it support?
- What is the expected outcome?

Describe the problem you are trying to solve, and its constraints, without coupling them too closely to the solution you have in mind. If this RFC is not accepted, the motivation can be used to develop alternative solutions. -->

`skuba-update` is a systemd timer running on every CaaS Platform cluster node: it automatically updates the local system.
This RFC describes what modifications Uyuni/SUSE Manager must introduce in order to accomodate user-defined patching of a SUSE CaaS Platform cluster node.

# Detailed design
[design]: #detailed-design

[`skuba-update`](https://documentation.suse.com/suse-caasp/4/single-html/caasp-admin/#_base_os_updates) is a `systemd` timer that is running locally on each CaaSP cluster node. Its objective is to _automatically_ [patch installed packages on a system](https://github.com/SUSE/skuba/blob/master/skuba-update/skuba_update/skuba_update.py#L325-L329) by calling `zypper patch`.
It relies on the patches that are in the system repositories, provided by Uyuni/SUSE Manager after the registration.
`skuba-update` is configured as a [daily realtime timer](https://github.com/SUSE/skuba/blob/master/skuba-update/skuba_update/skuba-update.timer#L6).

Uyuni/SUSE Manager is be the central administrative point to install patch and updates for users. Uyuni/SUSE Manager fits into the "maintenance window" concept as it offers the possibility to schedule update actions on all system updates during the maintenance window.
The maintenance windows are used for predictability, SLA and many other user-defined metrics.

`skuba-update`'s automatic update falls out of the user-defined schedule and does not fit into the maintenance window concept.
In the following sections we are going to describe:

- How Uyuni/SUSE Manager must disable the automatic installation of patches via `skuba-update`
- How Uyuni/SUSE Manager must wire `skuba-update` to manual patch installs

## Disable skuba-update

Upon onboarding, as soon as Uyuni/SUSE Manager detects that the system is part of a cluster node, Uyuni/SUSE Manager applies an additional Salt state to [add the `--annotate-only` option to `skuba-update` configuration file](https://documentation.suse.com/suse-caasp/4.0/html/caasp-admin/_cluster_updates.html#_disabling_automatic_updates).

## Manual patch installs

`skuba-update` can be called manually to invoke `zypper patch` and the subsequent maintenance actions (defined by CaaS Platform) issued on a node in case an installed patch requires a system reboot.
For this reason, Uyuni/SUSE Manager must invoke `skuba-update` to install available patches on a system because of post-install actions already defined by `skuba-update`.
`skuba-update` does not offer the possiblity of specifying which available patches should be installed: all available patches are going to be installed.
Uyuni/SUSE Manager must directly call `skuba-update` and not its associated system service as the latter would just annotate the available updates and exit (as per Uyuni/SUSE Manager configuration of `skuba-update` service).
`skuba-update` does not offer any API at the time of writing.
There are some changes that Uyuni/SUSE Manager must introduce to emphasize that all patches are going to be installed.
In the next sections we are going to describe these changes.

### User interface: Software > Patches

When showing a single CaaS Platform system, the checkboxes for every available patch shown in Software > Patches must be all selected and disabled. When the user selects "Apply Patches", a new Salt state that calls `skuba-update` has to be dispatched by SaltServerActionService (only if the system if a CaaS Platform system).
The same applies when showing a group of systems in System Set Overview in regards to patching.

### User interfaces: Patches > Patch list

When selecting a patch in Patches > Patch list and showing all affected systems, if one of the systems is a CaaS Platform node then its associated checkbox must be disabled: it should not be possible to individually install a single patch on this system.

### API

The API for `ErrataManager.applyErrata` must be enriched to support a generic patch action to install all available patches. In the case of a CaaS Platform, the existing API calls (that require a list of errata IDs to be passed as argument) should fail in case an errata ID is passed, and resort to the new Salt state described above when no errata ID is passed.

# Drawbacks
[drawbacks]: #drawbacks

<!-- Why should we **not** do this?

  * obscure corner cases
  * will it impact performance?
  * what other parts of the product will be affected?
  * will the solution be hard to maintain in the future? -->

- Patch install is global via `skuba-update`: there is not the possibility of pin-pointing the install of a single patch but rather all available patches will be installed when calling `skuba-update`. This drawback can be mitigated by carefully promoting patches via [Content Lifecycle Management](https://documentation.suse.com/external-tree/en-us/suma/4.0/suse-manager/administration/content-lifecycle.html).
- User experience: the behavior of the automatic updates changes automatically when a CaaS Platform node is registered to Uyuni/SUSE Manager: the documentation of Uyuni/SUSE Manager must clearly state that `skuba-update` is going to be disabled.

# Alternatives
[alternatives]: #alternatives

<!-- - What other designs/options have been considered?
- What is the impact of not doing this? -->

# Unresolved questions
[unresolved]: #unresolved-questions

- Should Uyuni/SUSE Manager restore `skuba-update` timer when the system is unregistered from Uyuni/SUSE Manager?
<!-- - What are the unknowns?
- What can happen if Murphy's law holds true? -->
