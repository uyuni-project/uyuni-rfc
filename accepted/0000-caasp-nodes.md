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
* Bootstrap/registration in the Uyuni/SUSE Manager context: registering a node to Uyuni/SUSE Manager via [the documented methods<sup>4</sup>](https://opensource.suse.com/doc-susemanager/suse-manager/client-configuration/registration-overview.html).
At the time of writing, registering a CaaS Platform node to Uyuni/SUSE Manager has to be manually performed by the user.

## Assumptions

We assume that:
* The user has already created an activation key and associated it with the onboarding. The CaaS Platform nodes are registered correctly and with the proper CaaS Platform channel(s) assigned. The
* The user is registering the CaaS Platform nodes as Salt clients
* The registration of every CaaS Platform node to Uyuni/SUSE Manager is already completed by the user using the aforementioned methods
activation key is needed to have `skuba-update` automatically patch the cluster with the latest patches available<sup>1</sup>.

NOTE: It is outside of this RFC to discuss automatic registration methods of the CaaS Platform nodes.

## Technical description of the problem

### The forbidden actions

#### Patch and power management actions

[`skuba-update`](https://documentation.suse.com/suse-caasp/4/single-html/caasp-admin/#_base_os_updates) systemd timer will take care of [patching](https://github.com/SUSE/skuba/blob/master/skuba-update/skuba_update/skuba_update.py#L301-L305) all installed packages locally to every node of the cluster and optionally reboot the node if `zypper` signals that a reboot is required.
In the case that a patch that requires reboot has been installed by Uyuni/SUSE Manager before `skuba-update` applies it, then the node will not be tagged as pending a reboot action.<sup>2</sup>.

For the reasons above, Uyuni/SUSE Manager must not offer the possibility to issue the following actions on a registered CaaS Platform node:

* Reboot a system
* Apply a patch
* Mark a system to automatically install patches
* Issue any power management action via Cobbler
* Perform an SP migration

#### Forbidden packages related actions

Special handling needs to be taken with the packages that are included in the `SUSE-CaaSP-Node` pattern:

- `caasp-config`
- `cri-o`
- `kubernetes-client`
- `kubernetes-kubeadm`
- `kubernetes-kubelet`
- `patterns-base-basesystem`
- `patterns-caasp-Node-x.y`<sup>5</sup>
- `skuba-update`
- `supportutils-plugin-suse-caasp`

and their dependencies<sup>3</sup>. At the time of writing, it is not easy to [build the dependency tree using plain `zypper`](https://stackoverflow.com/questions/12183757/reverse-dependency-generation-with-zypper) (it will be available with `zypper` 1.14.33) and it is not clear (from the CaaS Platform side) whether a forbidden package dependency should be considered forbidden as well. For example, `iptables` is a dependency of `cri-o`, but `cri-o` does not specify which versions of `iptables` are supported.

To be on the safe side, Uyuni/SUSE Manager must not offer the possibility to issue the following actions on a registered CaaS Platform node:

* Upgrade a package
* Remove a package

NOTE: [installing NEW (not already installed and not conflicting with already installed) packages is allowed](https://documentation.suse.com/suse-caasp/4/single-html/caasp-admin/#_existing_cluster).

### Description of current implementation

Let's now describe how Uyuni/SUSE Manager implements each of the aforementioned actions for a Salt client.

#### System reboot

A reboot is triggered by calling the Salt module `system.reboot` on the target minion.

#### Patch apply

A patch apply is scheduled using Salt `state.apply` with the [patch install state](https://github.com/uyuni-project/uyuni/blob/master/susemanager-utils/susemanager-sls/salt/packages/patchinstall.sls).

#### Mark a system to automatically install patches

Automatic patch installation is implemented at the Uyuni/SUSE Manager level by automatically apply a patch whenever it is available (this action falls into the above one).

#### Issue any power management action via Cobbler

All the power management actions are scheduled via [Cobbler commands](https://cobbler.github.io/manuals/2.8.0/3/1/3_-_Systems.html).

#### Perform an SP migration

An SP migration is scheduled using Salt `state.apply` with the [distupgrade state](https://github.com/uyuni-project/uyuni/blob/master/susemanager-utils/susemanager-sls/salt/distupgrade/init.sls).

#### Package upgrade

A package upgrade is scheduled using Salt `state.apply` with the [pkginstall state](https://github.com/uyuni-project/uyuni/blob/master/susemanager-utils/susemanager-sls/salt/packages/pkginstall.sls).

As a special case when issuing a package upgrade, a package installation from API is scheduled using Salt `state.apply` with the [pkginstall state](https://github.com/uyuni-project/uyuni/blob/master/susemanager-utils/susemanager-sls/salt/packages/pkginstall.sls).
While it is not possible to install a non-installed package on the target system from the UI, is it possible to upgrade an already installed package by requesting an installation of it from the API. Example:
```
ec2-user@ip-172-31-8-0:~> rpm -qa | grep -i bzip2
bzip2-1.0.6-29.2.x86_64

spacecmd {SSM:0}> system_installpackage 172.31.8.0 bzip2
172.31.8.0:
bzip2-1.0.6-30.8.1.x86_64

Start Time: 20191108T11:05:04

Install these packages [y/N]:
```

#### Package removal

A package removal is scheduled using Salt `state.apply` with the [pkgremove state](https://github.com/uyuni-project/uyuni/blob/master/susemanager-utils/susemanager-sls/salt/packages/pkgremove.sls).

#### Limitations

At the time of writing, Uyuni/SUSE Manager or Salt cannot forbid the package operations based on the target packages (there is no such kind of granularity).
As a future implementation, Uyuni/SUSE Manager _might_ consider adding another level of granularity: filter actions depending on the argument passed (e.g. forbid install of a package when the package is `kubernetes-kubeadm`).

NOTE: It is also implied that the [forbidden operations on a CaaS Platform node are also described in the Uyuni/SUSE Manager documentation](https://github.com/SUSE/doc-susemanager/pull/882/files).

## Design

### Identifying a CaaS Platform node

To identify a CaaS Platform node it is enough to check if the `patterns-caasp-Node-.*`<sup>5</sup> pattern is installed. In the future, we might think to add a check for all CaaS Platform workloads to be installed as well.

Internally to Uyuni/SUSE Manager, storing that a node is a CaaS Platform node can be fulfilled by adding a new system entitlement (e.g. `caasp_node`) to the node.

### Action locking

Given all the considerations above, the following action must not be scheduled by Uyuni/SUSE Manager for a CaaS Platform node:

* Reboot a system
* Apply a patch
* Mark a system to automatically install patches
* Issue any power management action via Cobbler
* Perform an SP migration
* Upgrade a package
* Remove a package
* Install a package (via API only)

The first step is to block these actions at the Salt level, and later at the Uyuni/SUSE Manager level.
Why Salt first? To be compliant with plain Salt and to protect the CaaS Platform node from `modules.pkg.remove` issued by the user via the Salt command line.

### Step 1: action blocking at Salt level

The idea is that, by default, every node that is a `caasp_node` system type is not allowed to perform some Salt commands.

This can be achieved in two ways:
* [Minion blackout](https://docs.saltstack.com/en/latest/topics/blackout/) works by blocking every command targeting the minion, except for a whitelist of functions allowed during the blackout. It can be useful to individually allow `modules.state.apply`. When changing blackout state, a `saltutil.refresh_pillar` has to be issued on the minion.
* [Module whitelisting](https://docs.saltstack.com/en/latest/ref/configuration/minion.html#whitelist-modules): work by blocking all the Salt modules except the ones whitelisted. It can be useful to globally allow a module, e.g. `modules.state`. When changing whitelist configuration, a `salt-minion` daemon restart has to be issued on the minion.

The allowed list of commands must contain:

- `test.ping`
- `state.apply` (for running `packages.profileupdate` required for "Update Package List" and see the patch level of the system)
- other functions that Uyuni/SUSE Manager needs to achieve all other operations

Given that the first interesting execution module for Uyuni/SUSE Manager is `state.apply`, we are considering minion blackout instead of module whitelisting. If the number of functions within a module will grow, a switch (or a complementary addition) to module whitelisting can be considered in the future.

Whitelisting `state.apply` for getting the package list also allows the forbidden operations described above that make use of `state.apply`.

In this iteration, Uyuni/SUSE Manager automatically set the blackout for a `caasp_node` minion upon registration by issuing the correct pillar. This means that a `caasp_node` will not be able to:

- Check and display the patch level of the CaaS Platform node
- Apply Salt states
- Issue any other Salt operation

unless the blackout is temporarily disabled.

The workflow for the user that needs to issue any action on the CaaS Platform node from Uyuni/SUSE Manager is then modified to:

1. Temporarily disable minion blackout from Uyuni/SUSE Manager using a Salt formula.
2. The user then executes any action that was intended for the CaaS Platform node.
3. Finally, minion blackout is enabled again:
    - Manually by the user
    - Automatically, as a hook after every action issued by the user
    - Automatically, in a timely fashion (e.g. after 10 minutes)

The functionality would be used also for troubleshooting and installing troubleshooting tools and issuing commands.

The risk of breaking the cluster by issuing any forbidden operation is still present while the blackout is disabled.

NOTE: every action issued by the user while the minion is in the blackout will still be scheduled and subsequently fail when picked up by Salt.

### Step 2: allowed list of arguments

In the second iteration, [minion blackout will be modified to allow a list of arguments for the allowed function](https://github.com/saltstack/salt/blob/c157cb752a6843e58826588110bcd3c67ef8bc86/salt/minion.py#L1625-L1638). In our specific case, Salt blackout will allow individual states to be applied during the blackout:

```
minion_blackout_whitelist:
- state.apply:
  - packages.pkginstall
  - packages.profileupdate
  - channels.disablelocalrepos
  - channels
  - hardware.profileupdate
  - ...
- test.ping
- pillar.get
- mgractionchains.resume
 ```

This patch will allow us to cherry-pick the actions (and hence the corresponding Salt states) that Uyuni/SUSE Manager is allowed to run on CaaS Platform nodes.
The minion will always be in the blackout and the Salt formula to disable the blackout will only be used for troubleshooting.

The patch can be upstreamed to Salt.

Note that an user can also issue any forbidden package upgrade by calling `state.apply packages.pkginstall`. But `packages.pkginstall` is an Uyuni/SUSE Manager internal state file, it should not be used by users.

NOTE: every action issued by the user that is a forbidden action will still be scheduled and subsequently fail when picked up by Salt.

### Step 3: forbid the actions at the Uyuni/SUSE Manager level

The idea is that Uyuni/SUSE Manager must restrict the following features:

- Reboot a system:
  - If the targeted minion is a `caasp_node` system type, the action for rebooting a system:
    - Must be hidden from the UI and the corresponding action must not be scheduled: code paths `/systems/details/RebootSystem`, `/systems/ssm/misc/RebootSystem`, `ActionChainManager#scheduleRebootAction`, `ActionChainManager#scheduleRebootActions`
    - The corresponding action must fail if scheduled via XMLRPC: `SystemHandler#scheduleReboot`
- Patch apply:
  - If the targeted minion is a `caasp_node` system type, the action for applying a patch:
    - Must be hidden from the UI and the corresponding action must not be scheduled: `/systems/details/ErrataList.do`, `/systems/ssm/ListErrata`, `ErrataManager#applyErrata`
    - The corresponding action must fail if scheduled via XMLRPC: [`SystemHandler#scheduleApplyErrata`]
- Mark a system to automatically install patches:
  - If the targeted minion is a `caasp_node` system type:
    - The checkbox for "Automatic application of relevant patches" must be hidden in the system details (`systems/details/Edit.do`, `/systems/ssm/misc`) and the corresponding property must not be set
    - The API call to enable auto updates must fail (`SystemHandler#setDetails`)
- Issue any power management action via Cobbler:
  - If the targeted minion is a `caasp_node` system type:
    - The "Power Management" page must be hidden (`/systems/details/kickstart/PowerManagement.do`, `/systems/ssm/provisioning/PowerManagementOperations`)) and the corresponding action must not be scheduled
    - Cobbler must fail when scheduling a power management action [to achieve this result, the IPMI module can be disabled at the Uyuni/SUSE Manager level upon bootstrap of CaaS Platform nodes]
- Perform an SP migration:
 - If the targeted minion is a `caasp_node` system type:
    - The SP migration page must be hidden (`/systems/details/SPMigration.do`) and the corresponding action must not be scheduled
- Package upgrade:
  - If the targeted minion is a `caasp_node` system type, the action for upgrade a package:
    - Must be hidden from the UI and the corresponding action must not be scheduled: code paths `/systems/details/packages/UpgradableList`, `systems/ssm/PackageUpgrade`, `ActionChainManager#schedulePackageUpgrade`, `ActionChainManager#schedulePackageUpgrades`
    - The corresponding action must fail if scheduled via XMLRPC: [`SystemHandler#schedulePackageInstall`]
- Package removal:
  - If the targeted minion is a `caasp_node` system type, the action for removing a package:
    - Must be hidden from the UI and the corresponding action must not be scheduled: `/systems/details/packages/RemoveConfirm`, `/ystems/ssm/PackageRemove`, `ActionChainManager#schedulePackageRemoval`, `ActionChainManager#schedulePackageRemoval`
    - The corresponding action must fail if scheduled via XMLRPC: `SystemHandler#schedulePackageRemove`

While this approach changes the underlying Java core of Uyuni/SUSE Manager, notable advantages come in terms of:

* Usability: forbidden actions cannot be issued from the UI, compared to the previous iteration where those actions were scheduled and subsequently fail.
* Performance: the forbidden actions will not be scheduled and picked up by Salt to fail as in the previous iteration, but rather will not be scheduled and not pollute the Salt bus with useless information.

# Drawbacks
[drawbacks]: #drawbacks

<!-- Why should we **not** do this?

  * obscure corner cases
  * will it impact performance?
  * what other parts of the product will be affected?
  * will the solution be hard to maintain in the future? -->

The user can craft a Salt state that executes one of the forbidden operations and break the cluster. This event is outside the scope of the RFC.

# Alternatives
[alternatives]: #alternatives

<!-- - What other designs/options have been considered?
- What is the impact of not doing this? -->

## CaaS Platform module in Salt

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

## Package locking at `zypper` level

Package locking of the forbidden packages is not really an option: in that case, `skuba-update` is not able to patch the forbidden packages.

## Future work

### Cluster provider manager

In the future, we can team up with cluster providers and ask to `skuba` and other [cluster provider managers](https://trello.com/c/2X01ypO4/10-cluster-awarenesss-workshop-suse-manager-caasp-ha-cap-ses#comment-5dc1bc4567c6031ae57bcb04) to implement all these forbidden actions that require special handling.
For example, `skuba-update` can expose a `patch` action: in that case, Uyuni/SUSE Manager can remove all the specific features described in this RFC and offload the task to the cluster provider manager.

### Disallowing packages at Salt level

It still has to be researched but if possible with plain Salt and eventually Jinja to block the actions related to the forbidden packages inside the Salt state files. The list of packages would be hardcoded in Uyuni/SUSE Manager, with the limitations already discussed<sup>3</sup>.

# Unresolved questions
[unresolved]: #unresolved-questions

- Docker/Kiwi build hosts: is it not tested by CaaS Platform QA to have Docker or Kiwi installed on a CaaS Platform node. It is a non-desirable situation. For the time being, let's consider it as a forbidden action.
- There are potential other actions that can be issued and deal with forbidden actions or forbidden packages: in this RFC we are targeting the most obvious actions to forbid and in future work we can close any holes that might have been left out.
<hr />


<sup>1</sup> `skuba-update` is a `systemd` timer that is already running on CaaSP cluster nodes and _automatically_ [manages the patching of all the packages installed in the nodes](https://github.com/SUSE/skuba/blob/master/skuba-update/skuba_update/skuba_update.py#L301-L305).
It relies on the patches that are in the system repositories that, in turn, comes from Uyuni/SUSE Manager (if the system is registered).
Uyuni/SUSE Manager does not need to interact with `skuba-update` in any way.

<sup>2</sup> The kernel package is a good example of such a case. The first goal of `skuba-update` is to patch the underlying Kubernetes system with information about rebooting. The benefit for the user is to see that kind of information directly with `kubectl get nodes`.

<sup>3</sup> At the time of writing, there is not a programmatic way to list all forbidden packages from `skuba-update`. This requirement would be ideal to avoid a release whenever the list of forbidden packages changes. The capability of having the list of forbidden packages programmatically will not be implemented in `skuba-update` in the future, as the list is hard to keep up (from the CaaS Platform perspective).

<sup>4</sup> As a not complete list:
* Bootstrap script
* UI: Systems > Bootstrapping
* `bootstrap` XMLRPC call
* Not usual but still possible and hackier: mass bootstrap via salt-ssh and a user-generated roster file

<sup>5</sup> The pattern is a moving target: `patterns-caasp-Node-x.y` -> `patterns-caasp-Node-x.y-x.(y+1)` -> `patterns-caasp-Node-x.y+1`
