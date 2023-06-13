- Feature Name: virtual networks management
- Start Date: 2018-05-02
- RFC PR:

# Summary
[summary]: #summary

When using SUSE Manager to handle virtual machines, the user will need to
also manage virtual networks on his virtual hosts. This RFC documents what
would be needed to handle them.

# Motivation
[motivation]: #motivation

Most virtual machines use one or more virtual networks defined on the virtual
host. These are chosen when creating or editing the virtual machine. Before
being able to choose among networks, the user needs to be able to create, list,
delete or edit them.

# Detailed design
[design]: #detailed-design

The virtual networks will be listed in a *Networks* child tab of the *Virtualization*
one. Similarly to what is done for Virtual Machines, this tab will list all the virtual
networks defined on the host.

Each network will display:

- its name
- its state (running / stopped)
- whether it autostarts
- whether it is persistent
- the name of the bridge it uses

The following actions will be available for each network:

- Start or stop, depending on the network state
- Edit
- Delete

The following bulk actions will be available:

- Start
- Stop
- Delete

Editing a network will allow changing the following:

- The name of the bridge to be used
- The forward type among the ones handled by libvirt
- The NAT address and port ranges if the forward mode it `nat`
- The interfaces to use in `passthrough`, `vepa`, `bridge` or `private` forward mode
- Static routes to add to the network
- The network IP setup (both IPv4 and IPv6), with its address, prefix and DHCP range

More advanced options could be added later like vlan tags, virtual port or DHCP
advanced settings. As these are advanced features, the expert users could still change
them with the appropriate `virsh net-edit` command.

A *Create Network* button will show a modal dialog like the editing one. Once the user
finishes the dialog, the network will be created and added to the list.

The network list will be refreshed often and will show network changes using libvirt
events for quick reaction. The virt poller should be extended to also provide a full
network status at less frequent intervals.

# Drawbacks
[drawbacks]: #drawbacks

None

# Alternatives
[alternatives]: #alternatives

Third-party tools like *virsh* or *virt-manager*.

# Unresolved questions
[unresolved]: #unresolved-questions

A clean and organized UI design for the edit page would be awesome.
