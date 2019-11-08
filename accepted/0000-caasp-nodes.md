- Feature Name: CaaSP nodes action locking
- Start Date: 2019-10-28
- RFC PR: TBD-change filename

# Summary
[summary]: #summary

This RFC describes the special handling that Uyuni/SUSE Manager must implement to manage CaaS Platform nodes.

# Motivation
[motivation]: #motivation

<!-- - Why are we doing this?
- What use cases does it support?
- What is the expected outcome?

Describe the problem you are trying to solve, and its constraints, without coupling them too closely to the solution you have in mind. If this RFC is not accepted, the motivation can be used to develop alternative solutions. -->

Any node of a CaaS Platform cluster can be registered to Uyuni/SUSE Manager.
Registering a CaaS Platform node to Uyuni/SUSE Manager brings the following notable advantages:

- The user can see the patch level status of the CaaS Platform nodes (at the packages level, not at the container level - the latter is called "[container staging](https://confluence.suse.com/display/~dmacvicar/Container+Staging+Breakout)" and it is outside of the scope of this RFC)
- The user can perform configuration management operations using Salt from Uyuni/SUSE Manager
- The user can assign a different set of channels (with channel staging and/or CLM filters) to different clusters and manually control from Uyuni/SUSE Manager which version of CaaS Platform gets automatically installed in its CaaSP clusters<sup>1</sup>.

However, if the user does some specific actions on any node of the cluster via Uyuni/SUSE Manager, the cluster may result temporarily or permanently unusable or broken.
This RFC describes how Uyuni/SUSE Manager can prevent the user to perform these kinds of actions on the CaaS Platform nodes.

# Detailed design
[design]: #detailed-design

<!-- This is the bulk of the RFC. Explain the design in enough detail for somebody familiar with the product to understand, and for somebody familiar with the internals to implement.

This section should cover architecture aspects and the rationale behind disruptive technical decisions (when applicable), as well as corner-cases and warnings. Whenever the new feature creates new user interactions, this section should include examples of how the feature will be used. -->
## Terminology

In this RFC, we will use:

* CaaS Platform node: any node that comprises the cluster, either a control plane node or a worker node
* Bootstrap/registration in the Uyuni/SUSE Manager context: registering a node to Uyuni/SUSE Manager via [the documented methods](https://opensource.suse.com/doc-susemanager/suse-manager/client-configuration/registration-overview.html).
At the time of writing, registering a CaaS Platform node to Uyuni/SUSE Manager has to be manually performed by the user with:
  * Bootstrap script
  * UI: Systems > Bootstrapping
  * `bootstrap` XMLRPC call
  * Not usual but still possible and hackier: mass bootstrap via salt-ssh and a user-generated roster file

## Assumptions

We assume that:
* The user is registering the CaaS Platform nodes as Salt clients
* The registration of every CaaS Platform node to Uyuni/SUSE Manager is already completed by the user using the aforementioned methods
* The user has already created an activation key and associated it with the onboarding. The CaaS Platform nodes are registered correctly and with the proper CaaS Platform channel(s) assigned.

NOTE: It is outside of this RFC to discuss automatic registration methods of the CaaS Platform nodes.

## Technical description of the problem

### The forbidden actions

[`skuba-update`](https://documentation.suse.com/suse-caasp/4/single-html/caasp-admin/#_base_os_updates) systemd timer will take care of [patching](https://github.com/SUSE/skuba/blob/master/skuba-update/skuba_update/skuba_update.py#L301-L305) all installed packages locally to every node of the cluster and optionally reboot the node if `zypper` signals that a reboot is required.

Uyuni/SUSE Manager does not offer the possibility to reboot a registered CaaS Platform node.

In general, patch and package upgrade/removal are safe operations for a CaaS Platform cluster: on the next trigger of `skuba-update`, if there are packages that required a reboot, `skuba-update` will orchestrate the reboot.

Package upgrade/removal and patch apply is not a problem if issued from Uyuni/SUSE Manager, unless the involved packages of the action are one of the following:

- kubernetes-kubeadm
- kubernetes-kubelet
- kubernetes-client
- cri-o
- cni-plugins

NOTE: [installing NEW (not already installed) packages is allowed](https://documentation.suse.com/suse-caasp/4/single-html/caasp-admin/#_existing_cluster).

At the time of the writing, Uyuni/SUSE Manager or Salt cannot forbid the package operations based on the target packages (there is no such kind of granularity).

### Actions to forbid

Decision criteria:

* Either Uyuni/SUSE Manager allows patching and package upgrade/removal or it does not allow those operations.
* Additionally, the list of the "forbidden" packages above may vary with time and with CaaS Platform upgrades. Currently, there is no programmatic way to gather a list of those packages from a CaaS Platform cluster. What if Uyuni/SUSE Manager hardcodes that list of packages and the list changes? An update of Uyuni/SUSE Manager would be required.

For the reasons above, Uyuni/SUSE Manager should not interfere with these actions to avoid breaking the cluster. The following actions should not be executed from Uyuni/SUSE Manager:

- System reboot
- Package upgrade
- Package removal
- Patch apply
- Package installation from API<sup>2</sup>

NOTE: It is also implied that the [forbidden operations on a CaaS Platform node are also described in the Uyuni/SUSE Manager documentation](https://github.com/SUSE/doc-susemanager/pull/882/files).

Let's now describe how Uyuni/SUSE Manager implements each of the aforementioned actions for a Salt client.

#### System reboot

A reboot is triggered by calling the Salt module `system.reboot` on the target minion.

#### Package upgrade

A package upgrade is scheduled using Salt `state.apply` with the [pkginstall state](https://github.com/uyuni-project/uyuni/blob/master/susemanager-utils/susemanager-sls/salt/packages/pkginstall.sls).

#### Package removal

A package removal is scheduled using Salt `state.apply` with the [pkgremove state](https://github.com/uyuni-project/uyuni/blob/master/susemanager-utils/susemanager-sls/salt/packages/pkgremove.sls).

#### Patch apply

A patch apply is scheduled using Salt `state.apply` with the [patch install state](https://github.com/uyuni-project/uyuni/blob/master/susemanager-utils/susemanager-sls/salt/packages/patchinstall.sls).

#### Package installation from API

A package installation from API is scheduled using Salt `state.apply` with the [pkginstall state](https://github.com/uyuni-project/uyuni/blob/master/susemanager-utils/susemanager-sls/salt/packages/pkginstall.sls).

## Design

### Identifying a CaaS Platform node

To identify a CaaS Platform node it is enough to check if the `patterns-caasp-` pattern is installed. In the future, we might think to add a check for all CaaS Platform workloads to be installed as well.

Internally to Uyuni/SUSE Manager, storing that a node is a CaaS Platform node can be fulfilled by adding a new system entitlement (e.g. `caasp_node`) to the node.

### Action locking

The main concept is to lock the aforementioned actions for the system types that are CaaS Platform nodes.
This can be achieved in two ways:

- Minion blackout
- Uyuni/SUSE Manager action locking

#### Minion blackout

The idea is that, by default, every node that is a `caasp_node` system type is in blackout mode after bootstrap (blackout would be achieved programmatically or via a Salt Formula).
[Minion blackout](https://docs.saltstack.com/en/latest/topics/blackout/) works by blocking every command targeting the minion, except for a whitelist of functions allowed during the blackout.

In the Uyuni/SUSE Manager case, the white list must contain:

- `test.ping`
- `state.apply` (for running `packages.profileupdate` required for "Update Package List" and see the patch level of the system)
- other functions that Uyuni/SUSE Manager needs to achieve all other operations

Whitelisting `state.apply` for getting the package list also allows the forbidden operations described above that make use of `state.apply`.
If we do not whitelist `state.apply`, then Uyuni/SUSE Manager cannot:

- Check and display the patch level of the CaaS Platform node
- Apply Salt states

We have two options:

- CaaS Platform module in Salt
- Minion blackout disable/enable

##### CaaS Platform module in Salt

If Uyuni/SUSE Manage uses a different function name to invoke package operations on a CaaS Platform node rather than relying on `state.apply`, then minion blackout is a solution.
In fact, as the Salt whitelisting algorithm filters by the function name, the white list would be:

- `test.ping`
- `caasp.info_installed`: returns the installed packages on the node
- `caasp.pkginstall`: install a package on the node
- other functions that Uyuni/SUSE Manager needs to achieve all other operations

All other functions are in blackout mode.

This solutions needs:
- Modifications in Uyuni/SUSE Manager [SaltServerActionService](https://github.com/uyuni-project/uyuni/blob/master/java/code/src/com/suse/manager/webui/services/SaltServerActionService.java): if the targeted minion is a `caasp_node` system type, switch the corresponding Salt operation to use the `caasp.*` Salt module
- Implementation (and upstream) of a Salt module that lives under the `caasp.*` namespace

Value of this solution:
* It can work with plain Salt
* It protects from `pkg.install` (and others) usage against the forbidden operations
* Requires code changes in Uyuni/SUSE Manager and Salt
* This workflow does not constitute a radical change for a user

##### Minion blackout disable/enable

One step back: the minion blackout white list only contains:

- `test.ping`

The idea would be that when the user needs to issue any action on the CaaS Platform node from Uyuni/SUSE Manager, there is the possibility to:

1. Temporarily disable minion blackout from Uyuni/SUSE Manager using a Salt formula.
2. The user then executes any action that was intended for the CaaS Platform node.
3. Finally, minion blackout is enabled again:
    - Manually by the user
    - Automatically, as a hook after every action issued by the user
    - Automatically, in a timely fashion (e.g. after 10 minutes)

The functionality would be used also for troubleshooting and installing troubleshooting tools and issuing commands.

The risk of breaking the cluster by issuing any forbidden operation is still present while the blackout is disabled.

Value of this solution:
* Easy and quick to implement
* The user can still break its cluster by issuing any forbidden action while the cluster is not in the blackout
* The Workflow for the user is different and mechanical, can lead to errors

#### Uyuni/SUSE Manager action locking

The idea is that Uyuni/SUSE Manager must restrict the following features:

- Reboot a system:
  - If the targeted minion is a `caasp_node` system type, the action for rebooting a system:
    - Must be hidden from the UI and the corresponding action must fail: code paths `/systems/details/RebootSystem`, `/systems/ssm/misc/RebootSystem`, `ActionChainManager#scheduleRebootAction`, `ActionChainManager#scheduleRebootActions`
    - The corresponding action must fail if scheduled via XMLRPC: `SystemHandler#scheduleReboot`
- Package upgrade:
  - If the targeted minion is a `caasp_node` system type, the action for upgrade a package:
    - Must be hidden from the UI and the corresponding action must fail: code paths `/systems/details/packages/UpgradableList`, `systems/ssm/PackageUpgrade`, `ActionChainManager#schedulePackageUpgrade`, `ActionChainManager#schedulePackageUpgrades`
    - The corresponding action must fail if scheduled via XMLRPC: [`SystemHandler#schedulePackageInstall`]
- Package removal:
  - If the targeted minion is a `caasp_node` system type, the action for removing a package:
    - Must be hidden from the UI and the corresponding action must fail: `/systems/details/packages/RemoveConfirm`, `systems/ssm/PackageRemove`, `ActionChainManager#schedulePackageRemoval`, `ActionChainManager#schedulePackageRemoval`
    - The corresponding action must fail if scheduled via XMLRPC: `SystemHandler#schedulePackageRemove`
- Patch apply:
  - If the targeted minion is a `caasp_node` system type, the action for applying a patch:
    - Must be hidden from the UI and the corresponding action must fail: `/systems/details/ErrataList.do`, `/systems/ssm/ListErrata`, `ErrataManager#applyErrata`
    - The corresponding action must fail if scheduled via XMLRPC: [`SystemHandler#scheduleApplyErrata`]

Value of this solution:
* This workflow does not constitute a radical change for a user
* Change does not involve Salt, the user can still break its cluster by issuing Salt commands
* Requires changes in Uyuni/SUSE Manager core code

# Drawbacks
[drawbacks]: #drawbacks

<!-- Why should we **not** do this?

  * obscure corner cases
  * will it impact performance?
  * what other parts of the product will be affected?
  * will the solution be hard to maintain in the future? -->

The user can craft a Salt state that executes one of the forbidden operations and breaks the cluster. This possibility is outside the scope of the RFC.

# Alternatives
[alternatives]: #alternatives

<!-- - What other designs/options have been considered?
- What is the impact of not doing this? -->

## Future work

In the future, we can team up with cluster providers and ask to `skuba` and other [cluster provider managers](https://trello.com/c/2X01ypO4/10-cluster-awarenesss-workshop-suse-manager-caasp-ha-cap-ses#comment-5dc1bc4567c6031ae57bcb04) to implement all these forbidden actions that require special handling. In that case, Uyuni/SUSE Manager can remove all the specific features described in this RFC and offload the task to the cluster provider manager.

# Unresolved questions
[unresolved]: #unresolved-questions

<sup>1</sup> `skuba-update` is a `systemd` timer that is already running on CaaSP cluster nodes and _automatically_ [manages the patching of all the packages installed in the nodes](https://github.com/SUSE/skuba/blob/master/skuba-update/skuba_update/skuba_update.py#L301-L305).
It relies on the patches that are in the system repositories that, in turn, comes from Uyuni/SUSE Manager (if the system is registered).
Uyuni/SUSE Manager does not need to interact with `skuba-update` in any way.
<sup>2</sup>While it is not possible to install a non-installed package on the target system from the UI, is it possible to upgrade an already installed package by requesting an installation of it from the API. Example:
```
ec2-user@ip-172-31-8-0:~> rpm -qa | grep -i bzip2
bzip2-1.0.6-29.2.x86_64

spacecmd {SSM:0}> system_installpackage 172.31.8.0 bzip2
172.31.8.0:
bzip2-1.0.6-30.8.1.x86_64

Start Time: 20191108T11:05:04

Install these packages [y/N]:
```
