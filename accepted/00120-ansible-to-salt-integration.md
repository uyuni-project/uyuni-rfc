- Feature Name: Ansible to Salt integration improvements
- Start Date: 2026-06-26

# Summary
[summary]: #summary

This RFC represents another point of view on Ansible to Salt integration with Uyuni.
The key point is to let the users to use systems registered to Uyuni as Ansible Inventory
and use Salt ZeroMQ transport for targetting these systems with Ansible instead of SSH.
Additionally it should allow to use Python from Salt Bundle as Ansible Python Interpreter.

# Motivation
[motivation]: #motivation

With the current implementation the only possible way to run Ansible Playbook with Uyuni deployment
is to have Ansible Control Node deployed in the environment and maintain the inventory on this host.
In case if the Ansible Playbooks are intended to be used with the same hosts as registered with Uyuni,
it requires to configure SSH connections for these hosts on the Ansible Control Node.

The suggested change is intended to let the users to run Ansible Playbooks with targetting the clients
registered in Uyuni using existing Salt ZeroMQ transport instead of SSH or even Salt-SSH roster data for
Salt-SSH clients with or without tunnel.

With this approach we also don't need dedicated Ansible Control Node, but use separate container on the Uyuni Server instead.

Additionally the Python from Salt Bundle (`venv-salt-minion` package) could be used as Ansible Interpreter.

With such approach we can offer smooth transition to Uyuni with Salt for the users with Ansible experience.
The Uyuni deployment could provide transparent co-existing Salt and Ansible environments providing the benefits of both.

# Detailed design
[design]: #detailed-design

This RFC is a follow up of [Ansible to Salt integration Hack Week 25 project](https://hackweek.opensuse.org/projects/ansible-to-salt-integration).
The original project covers only Ansible and Salt, it was not focused on Uyuni and it is not using Uyuni
as a source of system profiles data. The other limitation of the original project was mising Salt-SSH implementation,
which was out of scope of the project, but it could be implemented in the context of Uyuni.

As the starting point the same inventory and connection plugins (from the hackweek project) could be used.
Inventory plugin requires adding Uyuni as a source of inventory data. The open question with the inventory
is the way of presenting the group assignments. The naming of the groups is way more limited in Ansible,
so we can't just use the System Group names from Uyuni as they could contain not allowed symbols
and could intersect with the names across different organizations defined in Uyuni.

The problem of Ansible group naming could be solved with one of the following ways:
* automatically replace not-allowed characters with the allowed one (for example `_`)
  and adding `org_id` as a prefix or suffix
* create a separate mapping list to specify which Uyuni System Group should be mapped
  to the specific Ansible group
* extend Uyuni System Group Properties to let the users to point Ansible group directly
  in the System Group profile
* assign Ansible Group to the Uyuni System profile with the Custom Info,
  it could provide some extra flexibility, but could be confusing for the users

The inventory and connection plugins could be delivered with Salt and Ansible in the separate container image
for Uyuni Server. Ansible CLI tools like `ansible-inventory`, `ansible`, `ansible-playbook` could be called
inside the shell of this container. The container should have the volume attached with salt unix sockets
serverd by `salt-master` running inside `uyuni-server` container to let ansible plugins to communicate with Salt.

This solution allows to call ansible modules on Salt Minions or Salt-SSH clients without
additional SSH connection with reusing either existing Salt ZeroMQ connection established from
Salt Minion (the minion service from the Salt Bundle is preferred here as it has bundled Python,
which can be used as an Ansible Interpreter) or Salt-SSH roster data provided by Uyuni to establish
SSH connection as usual with Ansible, but with no need to keep separate credentials.
Salt Bundle could be also used for Salt-SSH clients to provide Python as an Ansible Interpreter.

In case of delivering such solution with the container image, the users don't need to have separate
Ansible Control Nodes anymore. It is also possible to mix both solution with existing Ansible Control Nodes
to manage existing Ansible environments and to manage the systems registered to Uyuni directly
using this integration.

# Drawbacks
[drawbacks]: #drawbacks

- Increases the complexity of the project and deployment
- Affects performance of Salt as Ansible is composing scripts to be transferred to the clients,
  in case of transferring the scripts with Salt ZeroMQ transport the data is converted to base64,
  what extends the size of the data, so the calls to Ansible through Salt ZeroMQ transport
  are bit havier than the calls to similar modules of Salt
- Requires changes on Java side and the changes on the web UI to provide an access
  to this integration with web UI
- Increases the workload on release engineers and QA

# Alternatives
[alternatives]: #alternatives

- Ansible could be included to `uyuni-server` container instead of detaching it to the separate one.
  Such approach could reduce the workload on release engineers and prevent increasing the number
  of separate parts of the product, but the `uyuni-server` container will grow and this feature
  couldn't be detached easily to reduce the server workload.
- As an alternative we can continue with Ansible Control Nodes approach and not to deliver this feature.
  But some of the customers could be interested in getting this feature.

# Unresolved questions
[unresolved]: #unresolved-questions

The open question here is how to provide the access for the user to Ansible CLI commands?
It could be done by switching to the shell inside the ansible container on Uyuni Server,
but in this case the session could be lost in case of dropping the connection to the shell
of Uyuni Server. It is also not very clear yet how the access to this functionality could be
provided from the web UI of the product.

The way of providing the access to the certain playbooks is also open. The easiest way for us
is to access the playbooks with shared volume from the container and let users to sync the content
there with any way they like, for example with `git`.

There is no way to limit the access with Ansible to the clients assigned to certain
organization defined in Uyuni. All will be visible for the user.
