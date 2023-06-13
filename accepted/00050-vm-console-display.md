- Feature Name: vm-console-display
- Start Date: 2018-05-02
- RFC PR:

# Summary
[summary]: #summary

Display a Spice or VNC web console for Virtual Machines running on virtual hosts
registered with SUSE Manager.

# Motivation
[motivation]: #motivation

To manage virtual machines from SUSE Manager, the user needs at some point in time
to interact with the VM display.

# Detailed design
[design]: #detailed-design

Among the possible actions for a virtual machine in the `Virtualization` tab of a virtual
host system would be a *Show Console* action. This action would open a new page embedding
either a `spice-html5` or `noVNC` console depending on the virtual machine graphics setup.

Both `spice-html5` and `noVNC` require a [websockify](https://github.com/novnc/websockify/)
daemon running on the virtual host to work.

An improperly configured Websockify could be a security hole. It should at least be
setup with a [token file](https://github.com/novnc/websockify/wiki/Token-based-target-selection)
and HTTPS. Websockify also has a pluggable authentication mechanism that could be used
to authenticate against a SUSE Manager user.

Once this feature implemented, the virtual machine creation dialog will open the VM console
once created, for the user to continue the setup.

# Drawbacks
[drawbacks]: #drawbacks

None

# Alternatives
[alternatives]: #alternatives

Using a third-party tool like *virt-viewer* or *virt-manager*, but that defeats the idea
of SUSE Manager used to manager Virtual Machines.

# Unresolved questions
[unresolved]: #unresolved-questions

The security of websockify would surely require some more attention at implementation time.
