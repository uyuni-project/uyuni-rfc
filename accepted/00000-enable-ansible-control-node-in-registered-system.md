- Feature Name: Enable Ansible control node management for registered systems
- Start Date: 2021-04-07

# Summary
[summary]: #summary

This RFC is describes how to manage an Ansible control node and integrate your Ansible managed infrastructure with Uyuni. This means that you would be able to display Ansible inventories, their systems and also apply playbooks to these Ansible managed nodes using Uyuni.

# Motivation
[motivation]: #motivation

There are two main motivations for this:

1. A user might have some investment in Ansible in the past but wants to switch to Uyuni now.

This RFC would offer a transition path for that. The user can register their Ansible control node, play with the already existing playbooks, get familiar with Uyuni and then switch over. It is also possible to manage clients with Salt and Ansible in parallel.

2. Managing parts of the infrastructure in Ansible.

If it is not possible or not wanted to move everything to Salt, it is possible to just keep using Ansible for the few clients that cannot be transitioned.


# Detailed design
[design]: #detailed-design

### Asumptions:
- In order to operate an Ansible control node, import the inventory or perform any other Ansible related task, the Ansible control node system **must** be already registered as Salt client (normal or SSH) in Uyuni.
- For a registered system, we can enable "Ansible control node" system property. In the same way we're doing, i.a. for "Virtualization Host".


### New system property: "Ansible control node"

We're creating a new "system type" in the database: "Ansible control node". When this property is set for a registered minion, the highstate will ensure:

- The "ansible" package is installed on the system.
- (Optional) The Uyuni SaltSSH key is deployed on this Ansible control node (even if this is a normal minion), so we later can perform "salt-ssh" operations using the Ansible control node as SSH proxy to reach the Ansible managed client to operate (i.a. to trigger bootstrapping). If we do not deploy the Uyuni SaltSSH key, we couldn't use the Ansible control node as SSH proxy when running "salt-ssh".

For systems which has this new "addon" Ansible control node system type, a new "tab" is shown in the system overwiew page: "Ansible"

This new "Ansible" tab in the System overview will:

- Live collect the Ansible inventory from the system. (similar to what we do in the highstate page - live rendering). By default, the inventory if collected from "/etc/ansible/hosts" file, but this page should also allow to define an alternative location for the inventory. (This info can be mapped as pillar data, so can be consumed in the corresponding SLS file that collects the inventory)
- Show the systems that are part of this Ansible control node inventory - grouped by onboarding status
- Bootstrap a selection (from None to All) of the Ansible managed clients
- A list of the available playbooks on this Ansible control node under a given path - this could be also be another page/subtab.
- Ultimately, allow to trigger the execution of those playbooks via the UI

#### How to identify if a gathered Ansible managed system is already registered in Uyuni?

- At the time of collecting the Ansible inventory, we only know about the "fqdn" of the Ansible managed client, so only chance at this point if trying to match the new client with an already existing client with the same fqdn.

#### What happen if a gathered Ansible managed system is already registered as traditional client?

- TBD: In this case we do match the system and allow to trigger the bootstrap/migration to a Salt minion in an easy way.


### Triggering playbook executions in an Ansible control node

After exploring the Ansible control node, inventory and playbooks, we can allow Uyuni to trigger the execution of one of those playbooks via a simple Salt state to execute in that control node:

```yaml
execute_ansible_playbook:
  ansible.playbooks:
    - name: /some/path/in/my/ansible/control/node/playbook_1.yaml
```

We would need to create a new type of Action in Uyuni for "running a playbook". We want this action to appear in the system event history for the Ansible control node.


### Shipping Ansible for SLE15+

At the time of writing this RFC, Ansible is not shipped in SLE15 any SP. In order to allow a posible Ansible control node running on SLE, we would need to ship Ansible probably in the SLE15 client tools channels.

- Which version to ship? Probably Ansible 2.9, which is currently packaged for Leap, and we have it also in Factory: https://build.opensuse.org/package/show/openSUSE:Factory/ansible

Considerations and other discussions about shipping Ansible in SLE, the support level, etc, can be discussed outside this RFC since it's out of the main focus of the general Ansible integration in Uyuni.


## Next Steps:

### Easy bootstrap of Ansible managed clients that are not yet registered as Salt minion

After collecting the inventory, and matching the existing registered systems, there are probably some Ansible managed clients that are not yet even registered in Uyuni at all. For these systems, via the "Ansible" tab of the registered Ansible control node, we allow to bootstrap a selection of them as Salt minion (or SSH minion), from None to All.

At this point, Uyuni doesn't know how to reach those systems, we only know their "fqdns" according to the Ansible inventory, but the Ansible inventory in the control node should contain information about how to reach them via ssh. The idea here is the following:

In order to bootstrap and trigger the registration of these systems, we have few alternatives:

#### Use "salt-ssh" from Uyuni directly to the "fqdns" of the Ansible managed clients:

* We previously need to fetch the corresponding SSH key that is used to connect to this particular host by Ansible.
* Then we would reuse this key as SSH credentials to trigger the bootstrap on that host.
* Downside: Uyuni needs to have direct access to the Ansible managed clients to bootstrap

#### Use "salt-ssh" from Uyuni using the Ansible control node as SSH proxy:

* We do not necessary need to fetch the corresponding SSH key, but we need to have the Uyuni SaltSSH deployed on the Ansible control node to access it
* The SSH key to connect the Ansible managed client referenced in the Ansible inventory is used to build the ProxyCommand to use in "salt-ssh".

NOTE: It needs to be clarified in the documentation that `ansible_ssh_private_key_file` needs to be defined in the Ansible inventory of your Ansible control node.

* Once we have this, we can trigger the bootstrap of those systems by calling "salt-ssh" like this:

```console
# salt-ssh --ssh-option='ProxyCommand="/usr/bin/ssh -i /srv/susemanager/salt/salt_ssh/mgr_ssh_id -o StrictHostKeyChecking=no -o User=root -W %h:%p uyuni-ansible-control-node.tf.local"' --roster=ansible --roster-file=/var/cache/ansible/ansible-inventory.yaml -N webserver1 state.apply certs,bootstrap pillar='{"mgr_server": "uyuni-srv.tf.local", "minion_id": "uyuni-ansible-sles15sp1-2.tf.local"}'
```
In esence, we apply the same states that we do at the time of Boostrapping a new minion via the UI, passing the necessary information as pillar data.

* Another example of usage (without using the ansible roster/targetting):

```console
# salt-ssh --ssh-option='ProxyCommand="/usr/bin/ssh -i PATH_TO_SALT_SSH_KEY_IN_THE_UYUNI_SERVER -o StrictHostKeyChecking=no -W %h:%p uyuni-stable-ansible-controller.tf.local /usr/bin/ssh -i PATH_TO_THE_SSH_KEY_IN_ANSIBLE_CONTROL_NODE uyuni-stable-ansible-opensuse152-2.tf.local" -o StrictHostKeyChecking=no' uyuni-stable-ansible-opensuse152-2.tf.local test.ping
```

Since the onboarding problem / massive onboarding, might raise some extra considerations, it would be desired to create an extra RFC to discuss the onboarding problem separately from this initial RFC.


# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?

  * obscure corner cases
  * will it impact performance? Bootstrapping Ansible managed clients might take some time since "salt-ssh" is involved.
  * what other parts of the product will be affected?
  * will the solution be hard to maintain in the future?


# Alternatives
[alternatives]: #alternatives

- What other designs/options have been considered?

  * An alternative approach based on VHM/"ansible-gatherer" is discussed [in this other RFC](https://github.com/uyuni-project/uyuni-rfc/pull/53)
  In this alternative approach, the Ansible control node does not require to be a registered system in Uyuni to operate it.

- What is the impact of not doing this?


# Unresolved questions
[unresolved]: #unresolved-questions

- What are the unknowns?
- What can happen if Murphy's law holds true?
