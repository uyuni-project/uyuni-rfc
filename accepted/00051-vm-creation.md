- Feature Name: vm_creation
- Start Date: 2018-05-02
- RFC PR:

# Summary
[summary]: #summary

Currently the Virtualization tab of virtual hosts lists all the defined virtual machines.
As a step forward, this feature would allow creating a new Virtual Machine out of a pre-built
image or a kiwi-built one.

# Motivation
[motivation]: #motivation

For SUSE Manager to be able to have a better support of virtual machines, we want to
be able to create new ones directly from it, not rely on an external tool like `virsh`
or `virt-manager`.

The typical use case is: I need to create a new VM `XXX` on host `YYY`. Obviously, the
user could want more or less control on the type of VM created, like what devices to add,
the size and type of disk, using backing chain, the network to use, etc.

# Detailed design
[design]: #detailed-design

To add a new VM, the user goes to the Virtualization tab of the host and clicks on a *Add VM*
button. This pops up a new modal dialog asking for the needed data. These data could be split
into several groups depending on their importance.

*Mandatory*:

- VM name
- Memory size
- vCPU amount
- disk size
- disk image to use as base or ISO to attach for the first run
- whether to create a transient VM (opt-in)
- whether to automatically register the VM (opt-out)

*Optional*:

- Network selection (could use a default one)
- Storage pool selection (could use a default one)
- Graphics (None, Spice or VNC), a default value could be used

An advanced setup could allow adding new devices.

Once the user validates the dialog, the VM will be defined and started. If it has a graphics
display (and the console feature is implemented in SUMA), display the VM console.

Some features could be left out for a first increment as they would depend on other
features:

- Creating a VM from an ISO image, would require SUSE Manager to be able to show a console
  for the VM since the user needs to interact with that VM to continue the installation
- Adding new device would surely be a too advanced feature for a first increment.

If possible the newly created virtual machine should be automatically registered with
SUSE Manager.

# Drawbacks
[drawbacks]: #drawbacks

Do we want to implement this for traditionnaly registered virtual hosts? Since this is
a new feature, it could be a Salt-only one.

# Alternatives
[alternatives]: #alternatives

Using third-party tools would be a serious usability problem when using SUSE Manager
as a virtualization management solution.

# Unresolved questions
[unresolved]: #unresolved-questions

The exact look of the creation dialog would surely need some more thinking to come
up with somethink nice.
