- Feature Name: CaaS Platform support
- Start Date: 2019-09-24
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

Initial integration for managing a CaaS Platform cluster from Uyuni/SUSE Manager.

# Motivation
[motivation]: #motivation

Uyuni/SUSE Manager is the systems management tool and must offer to the end-user the possibility to manage other SUSE products like CaaS Platform.
Uyuni/SUSE Manager already supports Kubernetes cluster integration. It works with CaaS Platform version 3 (container engine: Docker).

In this regard, this RFC will cover the update of the current Kubernetes integration of Uyuni/SUSE Manager to work with CaaS Platform version 4 while still supporting CaaS Platform version 3

# Detailed design
[design]: #detailed-design

## Update the current Kubernetes integration

Under Virtual Host Manager, there is an already Kubernetes integration that supports CaaS Platform version 3.
When Uyuni/SUSE Manager interfaces with the Kubernetes engine, [a Salt runner queries the running containers on the cluster](https://bugzilla.suse.com/show_bug.cgi?id=1149741#c0).
The current implementation breaks with CaaS Platform version 4 and must be fixed to work seamlessly with CaaS Platform version 3 and 4.
The Kubernetes implementation that this RFC is targeting is the one in CaaS Platform version 4: 1.16. Other Kubernetes distributions will not be targeted, at least initially.

The current implementation shows, when a Kubernetes cluster is selected into the Virtual Host Manager, the properties and the names of the nodes together with CPU Arch, CPU Sockets and RAM of each node. No changes will be introduced in the information shown.

# Drawbacks
[drawbacks]: #drawbacks

# Alternatives
[alternatives]: #alternatives

# Unresolved questions
[unresolved]: #unresolved-questions
