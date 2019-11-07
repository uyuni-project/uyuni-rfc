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

- The user can see the patch level status of the CaaS Platform nodes (at the packages level, not at the container level - the latter is container staging and it is outside of the scope of this RFC)
- The user can perform configuration management operations using Salt from SUSE Manager
- The user can assign different set of channels (with channel staging and/or CLM filters) to different clusters and manually control from Uyuni/SUSE Manager which version of CaaS Platform gets automatically installed in its CaaSP clusters. <sup>1</sup>.

However, if the user does some specific actions on any node of the cluster via Uyuni/SUSE Manager, the cluster may result temporarily or permanently unusable or broken.
This RFC describes how Uyuni/SUSE Manager can prevent the user to perform these kind of actions on the CaaS Platform nodes.

# Detailed design
[design]: #detailed-design

<!-- This is the bulk of the RFC. Explain the design in enough detail for somebody familiar with the product to understand, and for somebody familiar with the internals to implement.

This section should cover architecture aspects and the rationale behind disruptive technical decisions (when applicable), as well as corner-cases and warnings. Whenever the new feature creates new user interactions, this section should include examples of how the feature will be used. -->
## Terminology

In this RFC, we will use:

* Bootstrap/registration in the Uyuni/SUSE Manager context: registering a node to Uyuni/SUSE Manager via the usual methods
* CaaS Platform node: any node that comprises the cluster, either a control plane node or a worker node

At the time of writing, registering a CaaS Platform node to Uyuni/SUSE Manager has to be manually performed by the user via the usual methods:

* Bootstrap script
* UI: Systems > Bootstrapping
* `bootstrap` XMLRPC call
* Not usual but still possible and more hacky: mass bootstrap via salt-ssh and a user-generated roster file

## Assumptions

We assume that the user is registering the CaaS Platform nodes as Salt clients.
We also assume that the registration of every CaaS Platform node to Uyuni/SUSE Manager is already done by the user using the aforementioned methods.
We additionally assume that the user has already created an activation key and associated it with the bootstrap method he selected, and the registered CaaS Platform nodes are registered correctly and with the proper CaaS Platform channel(s) assigned.

It is also implied that:

- Ahe forbidden operations on a CaaS Platform node are described in the Uyuni/SUSE Manager documentation
- The user can craft a Salt state that executes one of the forbidden operation and breaks the cluster. This possibility is outside the scope of the RFC.

NOTE: It is outside of this RFC to discuss automatic registration methods of the CaaS Platform nodes.

## Technical description of the problem

[`skuba-update`](https://documentation.suse.com/suse-caasp/4/single-html/caasp-admin/#_base_os_updates) systemd timer will take care of [patching](https://github.com/SUSE/skuba/blob/master/skuba-update/skuba_update/skuba_update.py#L301-L305) all installed packages locally to every node of the cluster and optionally reboot the node if zypper signals that a reboot is required.

In general, patch and package upgrade/removal are safe operations for a CaaS Platform cluster unless the involved packages is one of the following:

- kubernetes-kubeadm
- kubernetes-kubelet
- kubernetes-client
- cri-o
- cni-plugins

At the time of the writing, Uyuni/SUSE Manager or Salt cannot forbid the package operations based on the target packages.
We should decide with an in or out approach: either Uyuni/SUSE Manager allows patching and package upgrade/removal or it does not allow those operations.

Additionally, the list of the "forbidden" packages above may vary with time and with CaaS Platform upgrades.
Currently, there is no programmatic way to gather a list of those packages from a CaaS Platform cluster.

What if Uyuni/SUSE Manager hardcodes that list of packages and the list changes? An update of Uyuni/SUSE Manager would be required.

For the reasons above, Uyuni/SUSE Manager should not interfere with these actions to avoid breaking the cluster. The following actions should not be executed from Uyuni/SUSE Manager:

- System reboot
- Package upgrade
- Package removal
- Patch apply

NOTE: [installing NEW (not already installed) packages is allowed](https://documentation.suse.com/suse-caasp/4/single-html/caasp-admin/#_existing_cluster).

Let's now describe how Uyuni/SUSE Manager implements each of the aforementioned actions for a Salt client.

### System reboot

A reboot is triggered by calling the Salt module `system.reboot` on the target minion.

### Package upgrade

A package upgrade is scheduled using Salt `state.apply` with the [pkginstall state](https://github.com/uyuni-project/uyuni/blob/master/susemanager-utils/susemanager-sls/salt/packages/pkginstall.sls).

### Package removal

A package removal is scheduled using Salt `state.apply` with the [pkgremove state](https://github.com/uyuni-project/uyuni/blob/master/susemanager-utils/susemanager-sls/salt/packages/pkgremove.sls).

### Patch apply

A patch apply is scheduled using Salt `state.apply` with the [patch install](https://github.com/uyuni-project/uyuni/blob/master/susemanager-utils/susemanager-sls/salt/packages/patchinstall.sls).

## Design

### Identifying a CaaS Platform node

To identify a CaaS Platform node it is enough to check if the `patterns-caasp-` pattern is installed.
To subsequentially identify a CaaS Platform node, we can add a system entitlement (e.g. `caasp_node`).

### Action locking

The main concept is to lock the aforementioned actions for the system types that are CaaS Platform nodes.
This can be achived in two ways:

- Minion blackout
- Uyuni/SUSE Manager action locking

#### Minion blackout

By default, every node that is a `caasp_node` system type is in blackout mode (issued with a Salt pillar - this can be achived programmatically or via a Salt Formula).
[Minion blackout](https://docs.saltstack.com/en/latest/topics/blackout/) works by blocking every command targeting the minion, except for a whitelist of functions allowed during blackout.

In the Uyuni/SUSE Manager case, the white list must contain:

- `test.ping`
- `state.apply` (for running `packages.profileupdate` required for "Update Package List" and see the patch level of the system)
- other functions that Uyuni/SUSE Manager needs to achieve all other operations

Whitelisting `state.apply` for getting the package list whitelists automatically the possibility of invoking all the operations described above that make use of `state.apply`.
If we do not whitelist `state.apply`, then Uyuni/SUSE Manager cannot:

- Check and display the patch level of the CaaS Platform node
- Apply Salt states

We have two options here:
- CaaS Platform module in Salt
- Minion blackout disable/enable

##### CaaS Platform module in Salt

If Uyuni/SUSE Manage uses a different mechanism to invoke package operations on a CaaS Platform node rather than relying on `state.apply`, then minion blackout can work.
In fact, the white list contains:

- `test.ping`
- `caasp.info_installed`: returns the patch level of the node
- `caasp.pkginstall`: install a package on the node
- other functions that Uyuni/SUSE Manager needs to achieve all other operations

All other functions are in blackout mode.

This path needs:
- Modifications in Uyuni/SUSE Manager [SaltServerActionService](https://github.com/uyuni-project/uyuni/blob/master/java/code/src/com/suse/manager/webui/services/SaltServerActionService.java): if the targeted minion is a `caasp_node` system type, switch the corresponding Salt operation to use the `caasp.*` Salt module
- Implementation (and upstream) of a Salt module that lives under the `caasp.*` namespace

Value of this solution: Salt will be able to offer a CaaS Platform-specific module, but development time requested will soar.

##### Minion blackout disable/enable

One step back: the minion blackout white list only contains:

- `test.ping`

When the user needs to issue any action on the CaaS Platform node from Uyuni/SUSE Manager, there is the possibility to temporarily disable minion blackout from Uyuni/SUSE Manager.
The user then executes any action that was intended for the CaaS Platform node.

Finally, minion blackout is enabled again:

- Manually by the user
- Automatically, as a hook after every action issued by the user
- Automatically, in a timely fashion (e.g. after 10 minutes)

The risk of breaking the cluster by issuing any forbidden operation is still present while the blackout is disabled.

Value of this solution: easy and quick to implement; the workflow for the user is mechanical and the user can still break its cluster.

#### Uyuni/SUSE Manager action locking

Uyuni/SUSE Manager must introduce the following features:

- Reboot a system:
  - If the targeted minion is a `caasp_node` system type, the action for rebooting a system:
    - Must be hidden from the UI and the corresponding action must fail: `/systems/details/RebootSystem`, `/systems/ssm/misc/RebootSystem`, `ActionChainManager#scheduleRebootAction`, `ActionChainManager#scheduleRebootActions`
    - The corresponding action must fail if scheduled via XMLRPC: `SystemHandler#scheduleReboot`
- Package upgrade:
  - If the targeted minion is a `caasp_node` system type, the action for upgrade a package:
    - Must be hidden from the UI and the corresponding action must fail: `/systems/details/packages/UpgradableList`, `systems/ssm/PackageUpgrade`, `ActionChainManager#schedulePackageUpgrade`, `ActionChainManager#schedulePackageUpgrades`
    - The corresponding action must fail if scheduled via XMLRPC: [`SystemHandler#scheduleUpgrade`]
- Package removal:
  - If the targeted minion is a `caasp_node` system type, the action for removing a package:
    - Must be hidden from the UI and the corresponding action must fail: `/systems/details/packages/RemoveConfirm`, `systems/ssm/PackageRemove`, `ActionChainManager#schedulePackageRemoval`, `ActionChainManager#schedulePackageRemoval`
    - The corresponding action must fail if scheduled via XMLRPC: `SystemHandler#schedulePackageRemove`
- Patch apply:
  - If the targeted minion is a `caasp_node` system type, the action for applying a patch:
    - Must be hidden from the UI and the corresponding action must fail: `/systems/details/ErrataList.do`, `/systems/ssm/ListErrata`, `ErrataManager#applyErrata`
    - The corresponding action must fail if scheduled via XMLRPC: [`SystemHandler#scheduleApplyErrata`]

Value of this solution: can be reused for other system types, it does not affect the workflow of the customer.

# Drawbacks
[drawbacks]: #drawbacks

<!-- Why should we **not** do this?

  * obscure corner cases
  * will it impact performance?
  * what other parts of the product will be affected?
  * will the solution be hard to maintain in the future? -->

The presented solutions do not cover any customized Salt state or remote action that the user may issue and still destroy the cluster.

# Alternatives
[alternatives]: #alternatives

<!-- - What other designs/options have been considered?
- What is the impact of not doing this? -->

In the future, the `skuba` [cluster provider manager](https://trello.com/c/2X01ypO4/10-cluster-awarenesss-workshop-suse-manager-caasp-ha-cap-ses#comment-5dc1bc4567c6031ae57bcb04) may be used to implement all these specific actions that require a special handling. In that case, Uyuni/SUSE Manager can remove all the specific features descibed in this RFC and offload the task to the cluster provider manager.

# Unresolved questions
[unresolved]: #unresolved-questions

<sup>1</sup> `skuba-update` is a systemd timer that is already running on CaaSP cluster nodes and _automatically_ [manages the patching of all the packages installed in the nodes](https://github.com/SUSE/skuba/blob/master/skuba-update/skuba_update/skuba_update.py#L301-L305).
It relies on the patches that are in the system repositories that, in turn, comes from Uyuni/SUSE Manager (if the system is registered).
Uyuni/SUSE Manager does not interact in any way with `skuba-update`.
