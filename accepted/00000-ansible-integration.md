- Feature Name: Ansible-Gate
- Start Date: 2021-02-01
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

This RFC proposes how to integrate and manage your existing Ansible nodes in Uyuni using the "Ansible-Gate" module of Salt. This means that you are able to import an Ansible inventory and you can apply playbooks to nodes from this inventory using Uyuni.


# Motivation
[motivation]: #motivation

There are two main motivations for this:

1. A user might have some investment Ansible in the past but wants to switch to Uyuni now.
This RFC would offer a transition path for that. The user can import the Ansible systems, start with the already existing playbooks, get familiar with Uyuni and then switch over. It is also be possible to manage clients with Salt and Ansible in parallel.
2. Managing parts of the infrastructure in Ansible.
If it is not possible or not wanted to move everything to Uyuni, it is possible to just keep using Ansible for the few clients that cannot be transitioned.

This RFC is more focus on allowing users to import their existing Ansible environments into Uyuni (allow some basic operations, coexistance of Salt and Ansible managed infrastructure in Uyuni, eventually apply playbooks and also an easy way to transition from Ansible to a full featured Salt minion managed system), rather than making Uyuni a top-featured UI to build your Ansible infrastructure from scratch.

_Describe the problem you are trying to solve, and its constraints, without coupling them too closely to the solution you have in mind. If this RFC is not accepted, the motivation can be used to develop alternative solutions._


# Detailed design
[design]: #detailed-design

There are two main parts/goals here, conceptually:

1) Collect data from an Ansible controller (Inventory / SSH Keys / Playbooks, etc) and import the hosts in the inventory as ANSIBLE systems in Uyuni.
2) Operate Ansible: Apply playbooks via controller node / Apply Salt commands & states directly to Ansible managed systems / Make Ansible system become a fully featured Salt Minion.
3) Maintain Ansible infrastructure: Uyuni Playbook catalog

## Collecting data from Ansible

The premise here is that there is already an existing Ansible infrastructure somewhere and we want to import it into Uyuni. We're primarely focused on building a new Ansible managed infrastructure from scratch using Uyuni.

Therefore, there might be more than one Ansible controller host, or even the Uyuni server could act at some point as an Ansible controller. As sources, and type of sources (i.a. single host, AWX api) might be multiple, this RFC proposes an approach similarly to what Uyuni does for handling "Virtual Host Managers (VHM)". This means, using a Python tool, in this case called something like "ansible-gatherer", which is plugin-based (so easily allow implementing different sources of Ansible inventores). This tool would be called via an Uyuni Java schedule, like the "virtual-host-gatherer", passing the necessary information (parameters, type of host, etc) to reach the Ansible controller and collect the necessary information.

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
- Playbooks under specified "remote playbook path" (to be displayed in the UI - readonly)

This would be stored under ""/var/lib/spacewalk/ansible/inventory-label/" path in the Uyuni server. At the time of processing the inventory file by "ansible-gatherer", it needs to be tailored to adapt the path of the SSH keys to the local path in the Uyuni server. As done in script from Ansible Integration PoC [here](https://github.com/meaksh/uyuni-hacks/blob/master/scripts/ansible/import_systems_from_ansible_controller.py).

With this information, Java is able to proceed creating these systems in Uyuni, as "Foreign / ANSIBLE" entitled systems.

- If any of those systems is already existing with "ANSIBLE" entitlement, then nothing to do
- If the system is already registered but not with "ANSIBLE" entitlement, then add "ANSIBLE" entitlement.

Of course, we need some new tables in the database, something like:

"suseAnsibleController" (label, type, org_1)
"suseAnsibleControllerConfig" (controller_id, parameter, value)
"suseAnsibleControllerSystem" (system_id, controller_id)

Also the new "ANSIBLE" entitlement, which should be an addon-entitlement compatible with Salt, Foreign and maybe also traditional entitlements.


This is the bulk of the RFC. Explain the design in enough detail for somebody familiar with the product to understand, and for somebody familiar with the internals to implement.

This section should cover architecture aspects and the rationale behind disruptive technical decisions (when applicable), as well as corner-cases and warnings. Whenever the new feature creates new user interactions, this section should include examples of how the feature will be used.

# Drawbacks
[drawbacks]: #drawbacks

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
