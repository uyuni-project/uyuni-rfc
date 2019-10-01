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

In this regard, this RFC will cover the following aspects:

- Node status reporting
- Update the current Kubernetes integration of Uyuni/SUSE Manager to work with CaaS Platform version 4 while still supporting CaaS Platform version 3
- Document how to deploy CaaS Platform using AutoYaST

# Detailed design
[design]: #detailed-design

## Node status reporting

All the nodes in the cluster can be registered to Uyuni/SUSE Manager using [bootstrapping methods](https://opensource.suse.com/doc-susemanager/suse-manager/client-configuration/registration-overview.html).
This brings two major benefits:

- The user can see from Uyuni/SUSE Manager if a node has packages updates and patch available, along with all the information that a Salt minion is presenting when registered to Uyuni/SUSE Manager (e.g. CVE auditing)
- Another benefit is that the user can associate staged channels to the nodes registered (along with an activation key) to associate channels to the nodes of the cluster.

The agent `skuba-update`, running on each node of the cluster, automatically picks up the packages from the associated channels and proceed to automatically update the nodes.
NOTE: `skuba-update` is **NOT** invoked by Uyuni/SUSE Manager and it is running autonomously on the nodes of the CaaS Platform cluster.

For example, an organization could have a "staging" cluster with a set of staging channels. The operator would cherry-pick Kubernetes updates from the SCC channels into the staging ones and then wait for skuba-update to roll them out into the staging cluster. At a later time, once testing is green inside of the staging cluster, the packages can be promoted to the "production channels" and be rolled out to the production cluster.

It is paramount to state in the user interface and the documentation that the information presented for the minion is in read-only mode.
If a user reboots the node, installs a patch or installs a package related to Kubernetes (`kubernetes-kubeadm kubernetes-kubelet kubernetes-client cri-o cni-plugins`) the Kubernetes may break.

NOTE: both of the above actions will not cluster-coordinated, so it is entirely possible that a user assigns different channels, install packages or reboots nodes in a subset of nodes belonging to the same cluster.

## Update the current Kubernetes integration

Under Virtual Host Manager, there is an already Kubernetes integration that supports CaaS Platform version 3.
The current implementation breaks with CaaS Platform version 4: the Salt runner needs to take into account that CaaS Platform version 4 switched from Docker to CRI-O.
Uyuni/SUSE Manager must check if the underlying container engine is running Docker (and use the existing Kubernetes integration) or CRI-O (and adapt the current implementation to support CRI-O).
The Kubernetes implementation that this RFC is targeting is the one in CaaS Platform version 4: 1.15.2. Other Kubernetes distributions will not be targeted, at least initially.

Into the Virtual Host Manager, when a Kubernetes cluster is selected, the properties and the names of the nodes are shown, together with CPU Arch, CPU Sockets and RAM of the node.

After the user has imported the `kubeconfig`, obtained from CaaS Platform, the process would be:

- When a user registers a new cluster, we introduce a new workflow to bootstrap (using Systems > Bootstrapping) each node of the cluster
- When every cluster node is registered, a system group with the same name of the cluster is created and all registered systems are moved into this system group
- Each node presented the Nodes information is a link to the system overview page of that node

## Documentation

In addition to all the above, we are enriching our documentation on the CaaS Platform deployment. In the following sections, we are going to describe what we should introduce in the documentation.

### AutoYaST Deployment documentation

CaaS Platform provides AutoYaST templates for deploying a standard cluster (in the `SUSE-CaaSP-Management` package) comprising of:

- 2 Load Balancers
- 3 Masters
- 3 Workers

In the Uyuni/SUSE Manager documentation, we need to provide a step-by-step guide on how to customize the AutoYaST template, import it in Uyuni/SUSE Manager and deploy it to bare-metal machines.

## Next steps

Possible next steps are presented as additional "stretch goals": if time permits, those goals can be achieved in the scope of the initial integration.

### Minion blackout configuration

If the [minion blackout](https://docs.saltstack.com/en/latest/topics/blackout/) is feasible, we can set to blackout every minion registered to Uyuni/SUSE Manager that is part of a Kubernetes or CaaS Platform cluster. Every minion that is in blackout mode will reject all incoming commands.

### Container registry documentation

In the documentation, we can write a guide on how to set up a container registry (using a standard container registry or Portus) and mirror SUSE container registry.

### Management node

As part of the support for the CaaS Platform version 4, SUSE Manager can elect (via the Add-On System Type) a node as "Management Node" for the cluster. This node must run SUSE Linux Enterprise Server and have `skuba` (a tool packaged by CaaS Platform) to deploy and manage the node.
Alternatively, we can choose to run `skuba` on the SUSE Manager server, we should add it to the packaging pattern of SUSE Manager server. The package is Go-vendored, no other dependency is required.

`skuba` is not packaged for OpenSUSE at the time of writing: Uyuni support will be implemented but enabled later, as soon as the package is released for OpenSUSE.

# Drawbacks
[drawbacks]: #drawbacks

If a user does not read the documentation, a Kubernetes cluster can be broken by simply rebooting a node from Uyuni/SUSE Manager.

# Alternatives
[alternatives]: #alternatives

# Unresolved questions
[unresolved]: #unresolved-questions

- CaaS Platform: for Container registry do you suggest a standard container registry or Portus?
