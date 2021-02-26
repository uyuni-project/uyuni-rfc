- Feature Name: Ansible-Gate
- Start Date: 2021-02-01
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

This RFC proposes how to integrate and manage your existing Ansible nodes in Uyuni with the help of Salt and its "Ansible-Gate" module. This means that you would be able to import Ansible inventories, their systems and also apply playbooks to these nodes using Uyuni.


# Motivation
[motivation]: #motivation

There are two main motivations for this:

1. A user might have some investment in Ansible in the past but wants to switch to Uyuni now.
This RFC would offer a transition path for that. The user can import the Ansible systems, start with the already existing playbooks, get familiar with Uyuni and then switch over. It is also be possible to manage clients with Salt and Ansible in parallel.
2. Managing parts of the infrastructure in Ansible.
If it is not possible or not wanted to move everything to Uyuni, it is possible to just keep using Ansible for the few clients that cannot be transitioned.

This RFC is more focus on allowing users to import their existing Ansible environments into Uyuni, allow some basic operations, coexistance of Salt and Ansible managed infrastructure in Uyuni, eventually apply playbooks and also to provide an easy way to transition from Ansible to a fully-featured Salt minion managed system in Uyuni, rather than making Uyuni a top-featured UI to build your Ansible infrastructure from scratch.

_Describe the problem you are trying to solve, and its constraints, without coupling them too closely to the solution you have in mind. If this RFC is not accepted, the motivation can be used to develop alternative solutions._


# Detailed design
[design]: #detailed-design

There are two main parts/goals here, conceptually:

1) Collect data from an Ansible controller (Inventory / SSH Keys / Playbooks, etc) and import the hosts in the inventory as ANSIBLE systems in Uyuni.
2) Operate Ansible: Apply playbooks via controller node / Apply Salt commands & states directly to Ansible managed systems / Make Ansible system become a fully-featured Salt Minion.
3) Maintain Ansible infrastructure: Own Uyuni Playbook catalog, revisions, formulas.

## Collecting data from Ansible

The premise here is that there is already an existing Ansible infrastructure somewhere and we want to import it into Uyuni. We're **not** primarely focused on building a new Ansible managed infrastructure from scratch using Uyuni.

Therefore, there might be more than one Ansible controller host, or even the Uyuni server could act at some point as an Ansible controller. Since data sources, and type of sources (i.a. single host, AWX api) might be multiple, this RFC proposes an approach similarly to what Uyuni does for handling "Virtual Host Managers (VHM)". This means, using a Python tool, in this case called something like "ansible-gatherer", which is plugin-based (so easily allow implementing different sources of Ansible inventores). This tool would be called via an Uyuni Java schedule, like the "virtual-host-gatherer", passing the necessary information (parameters, type of host, etc) to reach the Ansible controller and collect the necessary information.

This approach I think would also make some Python and UI code reusable from "Virtual Host Managers".

### ansible-gatherer

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
	"inventory-label",
        "hosts": {
		"my-ansible-managed-system1.foo.bar",
		"my-ansible-managed-system2.foo.bar",
		"my-ansible-managed-system3.foo.bar"
	},
	"local_stored_inventory": "/var/lib/spacewalk/ansible/inventory-label/inventory.yaml",
	"optional_local_stored_playbooks": {
		"/var/lib/spacewalk/ansible/inventory-label/playbooks/playbook1.yaml",
		"/var/lib/spacewalk/ansible/inventory-label/playbooks/playbook2.yaml",
		"/var/lib/spacewalk/ansible/inventory-label/playbooks/playbook3.yaml"
	}
}
```

As you can see, besides of reporting the hosts from the Ansible inventory, the idea is that we also stored it locally in the Uyuni server in order to being able to reuse it later to target those hosts with "salt-ssh" directly from the Uyuni server.

In short, we would gather, for instance:
- Ansible inventory (hosts)
- Ansible SSH keys referenced in the inventory
- Playbooks under specified "remote playbook path" (to be displayed in the UI - readonly mode - not editable)

This would be stored under `/var/lib/spacewalk/ansible/inventory-label/` path in the Uyuni server. At the time of processing the inventory file by "ansible-gatherer", it needs to be tailored to adapt the path of the SSH keys to the local path in the Uyuni server. As done in script from Ansible Integration PoC [here](https://github.com/meaksh/uyuni-hacks/blob/master/scripts/ansible/import_systems_from_ansible_controller.py).

With this information, Java is able to proceed creating these systems in Uyuni, as "Foreign / ANSIBLE" entitled systems.

- If any of those systems is already existing with "ANSIBLE" entitlement, then nothing to do
- If the system is already registered but not with "ANSIBLE" entitlement, then add "ANSIBLE" entitlement.

Of course, we need some new tables in the database, at least something like:

"suseAnsibleController" (label, type, org_1)
"suseAnsibleControllerConfig" (controller_id, parameter, value)
"suseAnsibleControllerSystem" (system_id, controller_id)
"suseAnsibleControllerPlaybook" (controller_id, local_path, content?)

And also create the new "ANSIBLE" entitlement, which should be an addon-entitlement compatible with Salt, Foreign and maybe also traditional entitlements. Here is the [SQL script](https://github.com/meaksh/uyuni-hacks/blob/master/scripts/ansible/add_ansible_entitleme.sql) used for PoC demo. It's also needed to adapt the rhn databaste functions implemented in the DB.

NOTE: The profile for a system with registered in Uyuni as "Foreign/ANSIBLE" does not look like as the one Salt/Traditional system, since most of the Uyuni features (channels, software profile, etc) are not implemented for neither "Foreign" nor "ANSIBLE" entitlements. In order to get the entire portfolio of Uyuni features for Salt minion, this "Foreign/ANSIBLE" systems would need to be transitioned to "Salt" minion.

Notice also that the Ansible controller is not listed as systems list page, since there is not system entry for it, it would be shown in the respective new UI page for managing Ansible Controller.

#### New UI tabs & pages

* Ansible
* Ansible / Ansible Controllers list
* Ansible / Add new Ansible controller
* Ansible / View Ansible controller information & and visualize playbooks (would also allow triggering playbooks via "salt-ssh" in the controller)

## Operating Ansible

This part describes different expectations/features to implement in order to execute certain operation in your Ansible infrastructure.

#### Run playbooks in an Ansible controller node
Each Ansible controller node contains an Ansible inventory together with all different playbooks and files used together with the playbooks. The targets for the different tasks of a playbook are defined inside the playbook yaml file itself and not externally like Salt does for the states.

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

The execution of a given playbooks is done in the corresponding Ansible controller, which contains the inventory and the hosts definition.

The playbooks available to apply on each Ansible controller, are the ones exposed by "ansible-gatherer" and ultimately, in the future, playbooks created and maintained in Uyuni (via future Ansible playbook catalog) that would be then pushed to the controller node.

At the time of running a playbook from the Ansible controller, Uyuni is able to do it by reaching the controller and operating it using "salt-ssh". There are different approaches here:

Option 1)
- SaltSSH to Ansible controller located in Ansible controller) via Salt state (or execution module):

```yaml
execute_ansible_playbook:
  ansible.playbooks:
    - playbook: /some/path/in/my/ansible/controller/playbook_1.yaml
```

Option 2)
- SaltSSH to Ansible controller to apply Salt state (playbook coming from Uyuni):

```yaml
execute_ansible_playbook:
  ansible.playbooks:
    - playbook: salt://ansible_playbooks/org_1/inventory-label/playbook-1.yaml
```

The option 1 is refers to executing a playbook which is already stored and maintained in the Ansible controller. On the other hand, option 2 would work in an scenario where the maintenance of the Playbooks are done in Uyuni, so we need to make the Ansible controller to get the generated playbook by Uyuni from the Salt file roots.

The SSH credentials to use in both cases to reach the Ansible controller would be the same that "ansible-gatherer" is using.


### Execute Salt commands & states to Ansible systems
The "ansiblegate" module of Salt also allows "salt-ssh" to reuse an Ansible inventory to reach those systems that are being managed by Ansible and execute Salt commands on it.

Example:

```console
# salt-ssh --ssh-option='ProxyCommand="/usr/bin/ssh -i /srv/susemanager/salt/salt_ssh/mgr_ssh_id -o StrictHostKeyChecking=no -o User=root -W %h:%p uyuni-ansible-controller.tf.local"' --roster=ansible --roster-file=/var/cache/ansible/ansible-inventory.yaml -N webserver1 grains.items
```

On this example, we pass `roster=ansible` and then we pass the Ansible inventory as `roster_file`. With `-N` we set the Ansible group to target, in this case `webservers`. We use `ProxyCommand` here because we want the SSH connection jumps via the Ansible controller (in case some firewall). The SSH credentials for the final `webservers` would be taken from the Ansible inventory.

Note that, in terms of performance, targetting Ansible systems using Salt means doing SSH connections via "salt-ssh".


### Transition to a fully-featured minion
Since we're able to reuse the inventory, it's easy to trigger the "bootstrap" (default or SSH) state in an Ansible managed system to easily onboard this system as fully-featured minion. This could be done with a "salt-ssh" call like:

```console
# salt-ssh --ssh-option='ProxyCommand="/usr/bin/ssh -i /srv/susemanager/salt/salt_ssh/mgr_ssh_id -o StrictHostKeyChecking=no -o User=root -W %h:%p uyuni-ansible-controller.tf.local"' --roster=ansible --roster-file=/var/cache/ansible/ansible-inventory.yaml -N webserver1 state.apply certs,bootstrap pillar='{"mgr_server": "uyuni-srv.tf.local", "minion_id": "uyuni-ansible-sles15sp1-2.tf.local"}'
```

In esence, we apply the same states that we do at the time of Boostrapping a new minion via the UI, passing the necessary information as pillar data.

The Java part that reacts to the minion startup event needs to be adjusted to take care of the entitlement migration and proper minion onboarding when the system is "Foreign/ANSIBLE" and needs to transition to "Salt/ANSIBLE".

NOTE: So far, those systems that are registered as "Foreign/ANSIBLE" are not necessary been ever contacted by Uyuni yet, this means we do not have the real `machine-id`, which is not part of the Ansible inventory, and which needed to do a proper matching while onboarding the new minion. This means, before triggering the "Bootstrap" of an Ansible client, the `machine-id` needs to be properly set to the registered system. Easily done by(executing a command on the Ansible system before executing the "boostrap" state.

For those systems that are "Foreign/ANSIBLE" we should enable some "Migration to Minion" tab that allows the user to trigger the bootstrap states via "salt-ssh" to convert this Ansible system into a fully-featured minion.

This is the bulk of the RFC. Explain the design in enough detail for somebody familiar with the product to understand, and for somebody familiar with the internals to implement.

This section should cover architecture aspects and the rationale behind disruptive technical decisions (when applicable), as well as corner-cases and warnings. Whenever the new feature creates new user interactions, this section should include examples of how the feature will be used.


## Maintain your Ansible infrastructure using Uyuni
This section is more like the next level of the Ansible integration in Uyuni. So far, we have been focus on visualize your Ansible infrastrucutre in Uyuni and so some basic operations, like triggering playbooks in the controller or migrate to minion.

This sections exposes lot of different possibilities in case that we really want to make Uyuni an UI for mantaining your playbooks and Ansible infrastructure. Maybe this is not really want we want for Uyuni, since there might be already better tools for this and it's opening a whole new world. In any case, some ideas that might be explored are:

- Maintain your own Ansible Playbooks catalog in the Uyuni server: Playbook catalog (like Configuration State Channels)
  * This would require, of course UI and DB investment. The idea would be to maintain the Ansible catalog inside the Uyuni server and push the playbook directly to the controller or the Ansible systems.
  * Some questions: Which inventory / hosts groups and Ansible controller to use here for running the playbooks? Uyuni server as the Ansible controller?

- Ansible Playbooks with Forms
  * Similarly to what we currently have for Salt with "Formulas with Forms". Prefilled playbooks + some metadata to render the forms to filling the required information. This rendered playbook can be exposed via Salt fileserver as described above so the corresponding controller is able to fetch it.


#### New UI tabs & pages

- TBD


# Drawbacks
[drawbacks]: #drawbacks

Allowing Ansible clients in Uyuni sounds great, but at the same time, we need to think that Uyuni and it's features are really based and tied to Salt. Allowing some basic integration, like collecting your Ansibles managed clients and expose them in Uyuni, operating your Ansible controller and some other things like easily migration to Salt minion are really cool and feasible featus, I think we should really think if we really want to make Uyuni a tool that allows you to build, maintain and operate your Ansible infrastructure from scratch.

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

* Where should we move from here? Full integration of Ansible features? Moving Ansible integration to Spacewalk core? Fully interfacing AWX?
