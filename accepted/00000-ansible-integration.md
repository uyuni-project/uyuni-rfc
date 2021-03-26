- Feature Name: Ansible Integration
- Start Date: 2021-02-01
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

This RFC proposes how to integrate and manage your existing Ansible nodes in Uyuni with the help of Salt and its "Ansible-Gate" module. This means that you would be able to import Ansible inventories, their systems and also apply playbooks to these nodes using Uyuni.


# Motivation
[motivation]: #motivation

There are two main motivations for this:

1. A user might have some investment in Ansible in the past but wants to switch to Uyuni now.
This RFC would offer a transition path for that. The user can import the Ansible systems, start with the already existing playbooks, get familiar with Uyuni and then switch over. It is also possible to manage clients with Salt and Ansible in parallel.
2. Managing parts of the infrastructure in Ansible.
If it is not possible or not wanted to move everything to Salt, it is possible to just keep using Ansible for the few clients that cannot be transitioned.

This RFC is more focused on allowing users to import their existing Ansible environments into Uyuni, allow some basic operations, coexistence of Salt and Ansible managed infrastructure in Uyuni, eventually apply playbooks and also to provide an easy way to transition from Ansible to a fully-featured Salt minion managed system in Uyuni, rather than making Uyuni a top-featured UI to build your Ansible infrastructure from scratch.


# Detailed design
[design]: #detailed-design

There are three main parts/goals here, conceptually:

1) Collect data from an Ansible control node (Inventory / SSH Keys / Playbooks, etc) and import the hosts in the inventory as ANSIBLE systems in Uyuni.
2) Operate Ansible: Apply playbooks via control node node / Apply Salt commands & states directly to Ansible managed systems / Make Ansible system become a fully-featured Salt Minion.
3) Maintain Ansible infrastructure: Own Uyuni Playbook catalog, revisions, formulas.

## Collecting data from an Ansible control node

This section elaborates how Uyuni would do for gathering information for an Ansible control node. There are different scenarios that we can consider here:

1. Adding an external host Ansible control node:

The premise here is that there is already an existing and configured Ansible infrastructure somewhere and we want to import it into Uyuni. This Ansible control node is not even a registered system in Uyuni. The hosts defined on the inventory can be imported Uyuni and will be displayed as "Foreign/ANSIBLE" or "Salt/ANSIBLE", etc. The "ANSIBLE" system type means that host is being managed by an Ansible control node.

Here we're **not** primarely focused on building a new Ansible managed infrastructure from scratch using Uyuni.

2. Using the Uyuni server as the Ansible control node:

On this approach, the Uyuni server is our Ansible control node. We would need to provide the Ansible package to the SUSE Manager server channel.

Since the Ansible inventory in the Uyuni server would be initially empty, default at `/etc/ansible/hosts`, the user would add their Ansible managed hosts to the inventory and will take care of deploying the Ansible SSH keys to those systems, in order for Ansible to work. (For already registered systems, deploying the SSH key could be automated somehow)

Assuming the Ansible inventory is properly created and SSH keys are deployed, the user can operate it from the command line, but Uyuni can also operate it via Salt runner call (since we're on the Uyuni server and not in a minion). Example:

```console
# salt-run salt.cmd ansible.playbooks name=example_playbook.yml
```

This means, playbooks can be triggered via CLI by the user, but also via "salt-api" so Uyuni is also easily able to trigger playbooks executions.

Once we have a "Playbook catalog" in the UI, and Uyuni would trigger playbook executions we would need to implement of course a new type of action: `ApplyPlaybook`, which should expose the playbook to the Salt "file_roots" so it's available for Ansible when running.

3. Adding an Ansible control node from a registered minion:

This scenario refers to the posibility of adding an Ansible control node from a registered system. Similarly to the previous scenarios but in this case, the Ansible control node is a registered system in Uyuni.

### ansible-gatherer

This is the component that takes care of collecting the inventory, host and playbooks from a given Ansible control node.

Therefore, there might be more than one Ansible control node host, even the Uyuni server, proxy or a registered system, could act at some point as an Ansible control node. Since data sources, and type of sources (e.g. single host, AWX API) might be multiple, this RFC proposes an approach similarly to what Uyuni does for handling "Virtual Host Managers (VHM)". This means, using a Python tool, in this case called something like "ansible-gatherer", which is plugin-based (so easily allows implementing different sources of Ansible inventories). This tool would be called via an Uyuni Java schedule, like the "virtual-host-gatherer", passing the necessary information (parameters, type of host, etc) to reach the Ansible control node and collect the necessary information.

- Python / Plugin-based (most skeleton reusable from virtual-host-gatherer implementation)
- Example plugins:
  * file-based (own Uyuni server): (inventory label, remote inventory path, optional remote playbook path)
  * external host SSH (user/pass): (inventory label, host, username, password, port, remote inventory path, remote playbook path)
  * external host SSH key: (inventory label, local ssh key, host, port, remote inventory path, remote playbook path)
  * AWX API (...)
  * A system already registered in Uyuni.

This tool would receive a JSON input with the necessary information to feed the corresponding plugin and will return a JSON output with collected information.

Output example:

```json
{
	"inventory-label": "my-ansible-control-node",
        "hosts": [
		"my-ansible-managed-system1.foo.bar",
		"my-ansible-managed-system2.foo.bar",
		"my-ansible-managed-system3.foo.bar"
	],
	"local_stored_inventory": "/var/lib/spacewalk/ansible/inventory-label/inventory.yaml",
	"optional_local_stored_playbooks": [
		"/var/lib/spacewalk/ansible/inventory-label/playbooks/playbook1.yaml",
		"/var/lib/spacewalk/ansible/inventory-label/playbooks/playbook2.yaml",
		"/var/lib/spacewalk/ansible/inventory-label/playbooks/playbook3.yaml"
	]
}
```

As you can see, besides of reporting the hosts from the Ansible inventory, the idea is that we also stored it locally in the Uyuni server in order to being able to reuse it later to target those hosts with "salt-ssh" directly from the Uyuni server.

In short, we would gather, for instance:
- Ansible inventory (hosts)
- Ansible SSH keys referenced in the inventory
- Playbooks under specified "remote playbook path" (to be displayed in the UI - readonly mode - not editable)

This would be stored under `/var/lib/spacewalk/ansible/inventory-label/` path in the Uyuni server. At the time of processing the inventory file by "ansible-gatherer", it needs to be tailored to adapt the path of the SSH keys to the local path in the Uyuni server. As done in script from Ansible Integration PoC [here](https://github.com/meaksh/uyuni-hacks/blob/master/scripts/ansible/import_systems_from_ansible_controller.py).

With this information, Java is able to proceed creating these systems in Uyuni, as "Foreign / ANSIBLE" system type.

- If any of those systems is already existing with "ANSIBLE" system type, then nothing to do
- If the system is already registered but not with "ANSIBLE" system type, then add "ANSIBLE" system type.

Of course, we need some new tables in the database, at least something like:

```
"suseAnsibleController" (label, type, org_1)
"suseAnsibleControllerConfig" (control_node_id, parameter, value)
"suseAnsibleControllerSystem" (system_id, control_node_id)
"suseAnsibleControllerPlaybook" (control_node_id, local_path, content?)
```

And also create the new "ANSIBLE" system type, which should be an addon-system type compatible with Salt, Foreign and, in case this doesn't need any extra effors, maybe also for a potential "Management/ANSIBLE" (traditional client) system type. Here is the [SQL script](https://github.com/meaksh/uyuni-hacks/blob/master/scripts/ansible/add_ansible_entitleme.sql) used for PoC demo. It's also needed to adapt the rhn databaste functions implemented in the DB.

NOTE: The profile for a system with registered in Uyuni as "Foreign/ANSIBLE" does not look like as the one Salt/Traditional system, since most of the Uyuni features (channels, software profile, etc) are not implemented for neither "Foreign" nor "ANSIBLE" system types. In order to get the entire portfolio of Uyuni features for Salt minion, this "Foreign/ANSIBLE" systems would need to be transitioned to "Salt/ANSIBLE" minion.

Notice also that the Ansible control node is not listed as systems list page, since there is not system entry for it, it would be shown in the respective new UI page for managing Ansible control nodes.

#### New UI tabs & pages

* Ansible
* Ansible / Ansible control nodes list
* Ansible / Add new Ansible control node
* Ansible / View Ansible control node information & and visualize playbooks (would also allow triggering playbooks via "salt-ssh" in the control node)
* Systems / Systems list / Ansible (show only Ansible systems and its control node)

or even create a new entry level on the menu as "Automation", something like:

* Automation / Ansible / ...
* Automation / Salt / ...
* Automation / Remote commands

## Operating Ansible

This part describes different expectations/features to implement in order to execute certain operation in your Ansible infrastructure.

#### Run playbooks in an Ansible control node node
Each Ansible control node node contains an Ansible inventory together with all different playbooks and files used together with the playbooks. The targets for the different tasks of a playbook are defined inside the playbook yaml file itself and not externally like Salt does for the states.

This is an example of Ansible playbook:

```yaml
---
- name: update web servers
  hosts: webservers
  remote_user: root

  tasks:
  - name: ensure apache is at the latest version
    yum:
      name: httpd
      state: latest
  - name: write the apache config file
    template:
      src: /srv/httpd.j2
      dest: /etc/httpd.conf

- name: update db servers
  hosts: databases
  remote_user: root

  tasks:
  - name: ensure postgresql is at the latest version
    yum:
      name: postgresql
      state: latest
  - name: ensure that postgresql is started
    service:
      name: postgresql
      state: started
```

As you can see, this playbook is defining different tasks to execute on different "hosts" groups. Those groups are of course defined in the Ansible inventory (default at /etc/ansible/hosts).

The execution of a given playbooks is done in the corresponding Ansible control node, which contains the inventory and the hosts definition.

The playbooks available to apply on each Ansible control node, are the ones exposed by "ansible-gatherer" and ultimately, in the future, playbooks created and maintained in Uyuni (via future Ansible playbook catalog) that would be then pushed to the control node node.

At the time of running a playbook from the Ansible control node, Uyuni is able to do it by reaching the control node and operating it using "salt-ssh" when it's an external host. If the control node is the Uyuni server or a registered minion we don't necessarily need to use "salt-ssh".

Some examples here:

Option 1)
- SaltSSH to Ansible control node via Salt state (or execution module):

```yaml
execute_ansible_playbook:
  ansible.playbooks:
    - name: /some/path/in/my/ansible/control/node/playbook_1.yaml
```

Option 2)
- SaltSSH to Ansible control node to apply Salt state (playbook coming from Uyuni):

```yaml
execute_ansible_playbook:
  ansible.playbooks:
    - name: salt://ansible_playbooks/org_1/inventory-label/playbook-1.yaml
```

The option 1 is refers to executing a playbook which is already stored and maintained in the Ansible control node. On the other hand, option 2 would work in an scenario where the maintenance of the Playbooks are done in Uyuni, so we need to make the Ansible control node to get the generated playbook by Uyuni from the Salt file roots.

Of course, in case the Ansible control node is a registered minion or even the Uyuni server, we would not necessary require to execute Salt SSH in order to apply a playbook, just a normal Salt job or runner execution

The SSH credentials to use in both cases to reach the Ansible control node would be the same that "ansible-gatherer" is using.

### Execute Salt commands & states to Ansible systems
The "ansiblegate" module of Salt also allows "salt-ssh" to reuse an Ansible inventory to reach those systems that are being managed by Ansible and execute Salt commands on it.

Example:

```console
# salt-ssh --ssh-option='ProxyCommand="/usr/bin/ssh -i /srv/susemanager/salt/salt_ssh/mgr_ssh_id -o StrictHostKeyChecking=no -o User=root -W %h:%p uyuni-ansible-control-node.tf.local"' --roster=ansible --roster-file=/var/cache/ansible/ansible-inventory.yaml -N webserver1 grains.items
```

On this example, we pass `roster=ansible` and then we pass the Ansible inventory as `roster_file`. With `-N` we set the Ansible group to target, in this case `webservers`. We use `ProxyCommand` here because we want the SSH connection jumps via the Ansible control node (in case some firewall). The SSH credentials for the final `webservers` would be taken from the Ansible inventory.

Note that, in terms of performance, targetting Ansible systems using Salt means doing SSH connections via "salt-ssh".


### Transition to a fully-featured minion
Since we're able to reuse the inventory, it's easy to trigger the "bootstrap" (default or SSH) state in an Ansible managed system to easily onboard this system as fully-featured minion. This could be done with a "salt-ssh" call like:

```console
# salt-ssh --ssh-option='ProxyCommand="/usr/bin/ssh -i /srv/susemanager/salt/salt_ssh/mgr_ssh_id -o StrictHostKeyChecking=no -o User=root -W %h:%p uyuni-ansible-control-node.tf.local"' --roster=ansible --roster-file=/var/cache/ansible/ansible-inventory.yaml -N webserver1 state.apply certs,bootstrap pillar='{"mgr_server": "uyuni-srv.tf.local", "minion_id": "uyuni-ansible-sles15sp1-2.tf.local"}'
```

In esence, we apply the same states that we do at the time of Boostrapping a new minion via the UI, passing the necessary information as pillar data.

The Java part that reacts to the minion startup event needs to be adjusted to take care of the system type migration and proper minion onboarding when the system is "Foreign/ANSIBLE" and needs to transition to "Salt/ANSIBLE".

NOTE: So far, those systems that are registered as "Foreign/ANSIBLE" are not necessary been ever contacted by Uyuni yet, this means we do not have the real `machine-id`, which is not part of the Ansible inventory, and which needed to do a proper matching while onboarding the new minion. This means, before triggering the "Bootstrap" of an Ansible client, the `machine-id` needs to be properly set to the registered system. Easily done by(executing a command on the Ansible system before executing the "boostrap" state.

For those systems that are "Foreign/ANSIBLE" we should enable some "Migration to Minion" tab that allows the user to trigger the bootstrap states via "salt-ssh" to convert this Ansible system into a fully-featured minion.


## Maintain your Ansible infrastructure using Uyuni
This section is more like the next level of the Ansible integration in Uyuni. So far, we have been focus on visualize your Ansible infrastrucutre in Uyuni and so some basic operations, like triggering playbooks in the control node or migrate to minion.

This sections exposes lot of different possibilities in case that we really want to make Uyuni an UI for mantaining your playbooks and Ansible infrastructure. Maybe this is not really want we want for Uyuni, since there might be already better tools for this and it's opening a whole new world. In any case, some ideas that might be explored are:

- Maintain your own Ansible Playbooks catalog in the Uyuni server: Playbook catalog (like Configuration State Channels)
  * This would require, of course UI and DB investment. The idea would be to maintain the Ansible catalog inside the Uyuni server and push the playbook directly to the control node or the Ansible systems.
  * Some questions: Which inventory / hosts groups and Ansible control node to use here for running the playbooks? Uyuni server as the Ansible control node?

- Ansible Playbooks with Forms
  * Similarly to what we currently have for Salt with "Formulas with Forms". Prefilled playbooks + some metadata to render the forms to filling the required information. This rendered playbook can be exposed via Salt fileserver as described above so the corresponding control node is able to fetch it.


#### New UI tabs & pages

- TBD

# Defining a MVP
[mvp]: #mvp

This is a suggestion of implementation roadmap:

### Step 0: The basic: gathering from an Ansible control node
- Implement "ansible-gatherer" to gather from external host (SSH key based).
- UI to add Ansible control nodes (reused from "Virtual Host Manager").
- Push Ansible package to SLE15 clients tools to allow having SLE control nodes.
- Inventory can be synced with Uyuni (add "Foreign/ANSIBLE" and "Salt/ANSIBLE", ...)

### Step 1: Operating an Ansible control node
- Trigger the playbooks from Ansible control node using "salt-ssh".
- Transition from "Foreign/ANSIBLE" to "Salt/ANSIBLE".

### Step 2: Enhancing the UI and introducing custom Playbook catalog
- Remote commands for "Foreign/ANSIBLE" systems.
- Uyuni Playbook catalog.
- Improve "Visualization" features.

### Step 3: Support multiple Ansible control node
- Enhance "ansible-gatherer" to deal with different sources of Ansible control nodes
- New UI pages and DB changes to deal with different control nodes.
- Enhance "Playbook catalog" for different sources of Ansible control nodes.

### Step 4:
- Whatever comes next

## Shipping Ansible for SLE15+

At the time of writing this RFC, Ansible is not shipped in SLE15 any SP. In order to allow a posible Ansible control node running on SLE, we would need to ship Ansible probably in the SLE15 client tools channels.

- Which version to ship? Probably Ansible 2.9, which is currently packaged for Leap, and we have it also in Factory: https://build.opensuse.org/package/show/openSUSE:Factory/ansible

Considerations and other discussions about shipping Ansible in SLE, the support level, etc, can be discussed outside this RFC since it's out of the main focus of the general Ansible integration in Uyuni.

# Drawbacks
[drawbacks]: #drawbacks

Allowing Ansible clients in Uyuni sounds great, but at the same time, we need to think that Uyuni and its features are really based and tied to Salt. Allowing some basic integration, like collecting your Ansibles managed clients and expose them in Uyuni, operating your Ansible control node and some other things like easily migration to Salt minion are really cool and feasible featus, I think we should really think if we want to make Uyuni a tool that allows you to build, maintain and operate your Ansible infrastructure from scratch.

Other consideration are:

- Issue with Salt and Ansible 2.9: https://github.com/ansible/ansible/issues/70357#issuecomment-685755182 (fixed already by: https://github.com/saltstack/salt/pull/59746)

Why should we **not** do this?

  * obscure corner cases
  * will it impact performance?
  * what other parts of the product will be affected?
  * will the solution be hard to maintain in the future?

# Alternatives
[alternatives]: #alternatives

* Interfacing AWX.

An alternative would be to use the API of AWX. While this would mean that all options of AWX would be available, it would also mean that we would need to make sure to always stay compatible with all versions used by users, breaking changes could be introduced by AWX and some features might even need to be implemented in AWX first before being able to use them in Uyuni.

# Unresolved questions
[unresolved]: #unresolved-questions

* Ansible version to ship with SLE?
* Where should we move from here? Full integration of Ansible features? Moving Ansible integration to Spacewalk core? Fully interfacing AWX?

Objective of this RFC is only running Ansible playbooks form the Uyuni Server. We are not trying to replace Salt as the foundation of Uyuni but only adding Ansible as a sidecar.
