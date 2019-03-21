- Feature Name: virt_storage_pools
- Start Date: 2018-05-02
- RFC PR:

# Summary
[summary]: #summary

Manage libvirt storage pools in order to define where to place the virtual machines
disk images.

# Motivation
[motivation]: #motivation

When managing virtual machines, users will want to specify where the disk images should
be located. A simple default value will not be enough.

# Detailed design
[design]: #detailed-design

The storage pools management feature will be available in a virtual host *Virtualization*
child tab named *Storage*. It will contain a list of all the storage pools available on
the virtual host. Like the Virtual machines list, this one will be kept up to date using
a combination of libvirt events and virtpoller data.

Each storage pool in the list will show the following data:

- its name
- its state (running / stopped)
- whether it autostarts
- whether it is persistent
- its capacity
- its allocated size
- its available space

Each storage pool will allow the following actions:

- Start
- Stop
- Edit
- Refresh
- Delete

The following bulk actions will be available:

- Start
- Stop
- Refresh
- Delete

A *Create pool* button will open a modal dialog asking for the following properties:

- Name
- Type (among those allowed by libvirt)
- The storage source data depending on the chosen type. See
  [the libvirt storage XML documentation](https://libvirt.org/formatstorage.html#StoragePool) for
  more details on the possible values.
- Whether to create a transient pool (opt-in)
- Whether to autostart the tool (opt-out)

Once the user validates the dialog, the pool is created and started.

When editing a pool, the data that could be changed are the following:

- Name
- Autostart flag

# Drawbacks
[drawbacks]: #drawbacks

None

# Alternatives
[alternatives]: #alternatives

Third party tools like *virsh* or *virt-manager* could be used. However the
user experience of SUSE Manager as a virtualization management solution would
suffer from this lack.

# Unresolved questions
[unresolved]: #unresolved-questions

None
