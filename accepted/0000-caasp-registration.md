- Feature Name: automatic registration of Kubernetes nodes
- Start Date: 2019-11-20
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

Automatically register to Uyuni/SUSE Manager nodes all the nodes reachable via a `kubeconfig` import.

# Motivation
[motivation]: #motivation

<!-- - Why are we doing this?
- What use cases does it support?
- What is the expected outcome?

Describe the problem you are trying to solve, and its constraints, without coupling them too closely to the solution you have in mind. If this RFC is not accepted, the motivation can be used to develop alternative solutions. -->

When dealing with a Kubernetes or a CaaS Platform cluster, the user is required to manually register all cluster nodes to Uyuni/SUSE Manager.
In this RFC we will use the term "cluster node" to refer to a generic Kubernetes cluster node.

We are going to describe a way to automatically register all the cluster nodes upon `kubeconfig` import.

# Detailed design
[design]: #detailed-design

Under "Virtual Host Managers > Kubernetes" cluster, there is already the possibility of importing a `kubeconfig` file (obtained from a Kubernetes cluster).
After the import, the hostname of each node of the cluster is displayed, along with basic information: operating systems, CPU(s) information, architecture, and memory.

The idea is to introduce a new checkbox on this page called "Register the cluster nodes to Uyuni/SUSE Manager".
If the user does not click on the checkbox, the workflow is unchanged.
We are going to describe it in the next chapter what happens when the user clicks on the checkbox.

## The new workflow

When the checkbox is selected, a new UI form will appear containing asking for the following information:

- SSH port
- SSH username with `sudo` rights
- SSH password
- Activation Key
- Proxy

Most experienced readers will recognize that these details are the same asked in the "Boostrap minions" page except for the host (the hosts will be gathered from the `kubeconfig` import call).

**Assumptions**: it is assumed that all the details provided by the user are valid for all nodes of the cluster, which means that all the cluster nodes have the same:

- SSH port
- `root` SSH access or a user with `sudo` rights
- password for the user above

After the form has been filled out and the `kubeconfig` import has begun, the usual workflow is followed.
The additional result for the final user would be that each system listed reached after the `kubeconfig` has been imported will be bootstrapped to Uyuni/SUSE Manager.

## How each cluster node is registered

The SSH details supplied by the user in the workflow will be used to bootstrap each reachable node of the cluster. We want to reuse as much code as possible: a call to `XmlRpcSystemHelper#bootstrap` will be issued for each node of the cluster. For the sake of simplicity and feature-wise, each node will be registered as a Salt minion and not as a salt-ssh minion.
Scalability-wise:

* From the field, it has been reported that a Kubernetes cluster should not be comprised of more than 100 nodes: managing 100 registrations at the same time should not constitute a performance problem for a healthy Uyuni/SUSE Manager.
* Theoretically, a cluster [must not have more than 5000 nodes](https://cloud.google.com/solutions/scope-and-size-kubernetes-engine-clusters): the same considerations apply as per the above.

# Drawbacks
[drawbacks]: #drawbacks

<!-- Why should we **not** do this?

  * obscure corner cases
  * will it impact performance?
  * what other parts of the product will be affected?
  * will the solution be hard to maintain in the future? -->

Some users already have their automation stack (e.g. puppet or cloud-init) to automatically use the Uyuni/SUSE Manager bootstrap script upon cluster node provisioning.
In that case, the feature introduced with this RFC is not appealing to this segment of users.

# Alternatives
[alternatives]: #alternatives

<!-- - What other designs/options have been considered?
- What is the impact of not doing this? -->

## Bootstrapping by pasting private SSH key

This is an alternative to using SSH username and passwords to automatic register the cluster nodes.

**Assumptions**: it is assumed that all the cluster nodes have the same:

- `root` SSH access or a user with `sudo` rights
- An SSH key already deployed for the user above in the `authorized_keys` file
- SSH logins via SSH keys enabled

The form for `kubeconfig` import will be changed to two inputs:

- User
- Private SSH key for that user<sup>1</sup>

The private key will be used to register the nodes to Uyuni/SUSE Manager. At the time of writing, Uyuni/SUSE Manager does not have a way to bootstrap a system using SSH keys and this feature must be implemented if we choose this alternative.

For this reason, re-using the code for minion bootstrapping using username and password has been preferred, although this alternative might be future work.

## Bootstrapping using Uyuni/SUSE Manager SSH key

This is an alternative to using SSH username and passwords to automatic register the cluster nodes.

Uyuni/SUSE Manager already generates an SSH key for dealing with SSH minions. The public and private key are located in `/srv/susemanager/salt/salt_ssh/mgr_ssh_id{.pub}`.
To have access to the cluster nodes, the user has to manually deploy the public key fingerprint into each node under `~[home of the root or user with sudo rights]/.ssh/authorized_keys`.
Uyuni/SUSE Manager must show the public key fingerprint and display information on how to the user must deploy this key into cluster nodes before continuing with importing the `kubeconfig`:

1. Copy the Uyuni/SUSE Manager key to a local machine
2. `ssh-copy-id` the key to all nodes of the cluster
3. The user must input the username (unique for all the cluster nodes) that has the key deployed
4. The user enables SSH logins via SSH keys (if not already enabled)

**Assumptions**: it is assumed that all the details provided by the user are valid for all nodes of the cluster, which means that all the cluster nodes have the same:

- `root` SSH access or a user with `sudo` rights

The private key will be used to register the nodes to Uyuni/SUSE Manager. At the time of writing, Uyuni/SUSE Manager does not have a way to bootstrap a system using SSH keys and this feature must be implemented if we choose this alternative.

For this reason, re-using the code for minion bootstrapping using username and password has been preferred, although this alternative might be future work.

# Unresolved questions
[unresolved]: #unresolved-questions

<!-- - What are the unknowns?
- What can happen if Murphy's law holds true? -->

<hr />

<sup>1</sup> Uyuni/SUSE Manager will use the SSH key just for registering the nodes and after this action, the key will be forgotten.
