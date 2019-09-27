- Feature Name: CaaS Platform support
- Start Date: 2019-09-24
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

Initial integration for managing a CaaS Platform cluster from Uyuni/SUSE Manager.

# Motivation
[motivation]: #motivation

Uyuni/SUSE Manager will offer the possibility to manage the nodes that comprise a CaaS Platform cluster.
Uyuni/SUSE Manager will register and show the status of each node of the cluster.

# Detailed design
[design]: #detailed-design

## Node status reporting

All the nodes in the cluster can be registered to Uyuni/SUSE Manager using bootstrapping by the already known methods.
The added benefit will be that the user can see from Uyuni/SUSE Manager if a node has packages updates and patch available, along with all the information that a Salt minion is presenting when registered to Uyuni/SUSE Manager (e.g. CVE auditing).
Another benefit is that the user can associate staged channels to the nodes registered (along with an activation key) to associate channels to the nodes of the cluster.
The agent `skuba-update`, running on each node of the cluster, automatically picks up the packages from the associated channels and proceed to automatically update the nodes.
NOTE: `skuba-update` is **NOT** invoked by Uyuni/SUSE Manager and it is running autonomously on the nodes of the CaaS Platform cluster.

For example: an organization could have a "staging" cluster with a set of staging channels. The operator would cherry-pick Kubernetes updates from the SCC channels into the staging ones and then wait for skuba-update to roll them out into the staging cluster. At a later time, once testing is green inside of the staging cluster, the packages can be promoted to the "production channels" and be rolled out to the production cluster.

If minion blackout is feasible in an easy way, then we can think to introduce it.

It is paramount to state in the documentation that this information is presented in a read-only fashion.
If a user reboots the node, installs a patch or installs a package related to Kubernetes (`kubernetes-kubeadm kubernetes-kubelet kubernetes-client cri-o cni-plugins`) the Kubernetes may break.

## Changes in the Kubernetes integration

Under Virtual Host Manager, there is an already Kubernetes integration that supports CaaS Platform v3.
The current implementation breaks with CaaS Platform v4: the Salt runner needs to take into account that CaaS Platform v4 switched to CRI-O. This needs to be fixed.

Into the Virtual Host Manager, when a Kubernetes cluster is selected, the properties and the names of the nodes are shown, together with CPU Arch, CPU Sockets and RAM of the node.

An addition to the already existing process would be:

- when a user registers a new cluster, we introduce a new workflow to bootstrap (using Systems > Bootstrapping) each node of the cluster
- when every cluster node is registered, a system group with the same name of the cluster is created and all registered systems are moved into this system group
- each node presented the Nodes information is a link to the system overview page of that node

## Documentation

In addition to all the above, we are enriching our documentation on the CaaS Platform deployment. In the following sections, we are going to describe what we should introduce in the documentation.

### AutoYaST Deployment documentation

CaaS Platform provides AutoYaST templates for deploying a standard cluster (in the `SUSE-CaaSP-Management` package) comprising of:

- 2 Load Balancers
- 3 Masters
- 3 Workers

In the Uyuni/SUSE Manager documentation, we need to provide a step-by-step guide on how to customize the AutoYaST template, import it in Uyuni/SUSE Manager and deploy it to bare-metal machines.

### Container registry documentation

As an extra, in the documentation, we can write a guide on how to set up a container registry (using a standard container registry or Portus) and mirror SUSE container registry.

# Drawbacks
[drawbacks]: #drawbacks

If a user does not read the documentation, a Kubernetes cluster can be broken by simply rebooting a node from Uyuni/SUSE Manager.

# Alternatives
[alternatives]: #alternatives

# Unresolved questions
[unresolved]: #unresolved-questions
