- Feature Name: MVP Cluster awareness for Uyuni/SUSE Manager
- Start Date: 2020-02-20
- RFC PR: https://github.com/uyuni-project/uyuni-rfc/pull/36

# Summary
[summary]: #summary

Make Uyuni/SUSE Manager aware and capable of deploying and managing clusters.

# Motivation
[motivation]: #motivation

<!-- - Why are we doing this?
- What use cases does it support?
- What is the expected outcome?

Describe the problem you are trying to solve, and its constraints, without coupling them too closely to the solution you have in mind. If this RFC is not accepted, the motivation can be used to develop alternative solutions. -->

Uyuni/SUSE Manager should be able to interact with other SUSE products:
- SUSE Container as a Service Platform (CaaSP) and Cloud Application Platform (CAP). From now on, we consider CAP as an equivalent of CaaSP for our purposes
- SUSE Enterprise Storage (SES)
- SUSE Linux Enterprise High Availability (SLE-HA) and SUSE Linux Enterprise HA for SAP Products (SHAP)
- Other types of clusters that are not covered in this RFC or that might be released in the future: the generic approach described in this RFC welcomes other types of clusters as long as the required interface is respected

The three SUSE products above constituted our initial study from which we tried to summarize the common actions that a user is interested to issue on a cluster, as much as generically speaking as possible.
This RFC aims to explain how Uyuni/SUSE Manager can __initially__ support the idea of being aware of a cluster and issue a specific set of actions on it. This is the MVP for a cluster: future RFCs will be extending this RFC horizontally (more cluster actions) and vertically (extend an implemented action by adding optional specific actions).

# Detailed design
[design]: #detailed-design

<!-- This is the bulk of the RFC. Explain the design in enough detail for somebody familiar with the product to understand, and for somebody familiar with the internals to implement.

This section should cover architecture aspects and the rationale behind disruptive technical decisions (when applicable), as well as corner-cases and warnings. Whenever the new feature creates new user interactions, this section should include examples of how the feature will be used. -->

## Assumptions

- During the writing of this RFC, we considered the documentation available of the latest version of the following products: CaaSP 4.1, SES 6, SLE-HA 15 SP1
- All products that want to integrate with Uyuni/SUSE Manager must provide a cluster provider manager in the form of a Salt module that implements the actions described below: add a node, remove a node, upgrade the cluster.
- Managing an existing cluster has priority over deploying a new cluster from the Uyuni/SUSE Manager perspective
- Deploying and provisioning the underlying infrastructure to host the cluster product is not covered in this RFC: for this purpose, consult [SUMA as a Virtualization Solution with Multi-Tenancy](https://confluence.suse.com/pages/viewpage.action?pageId=431620395)
- We decided not to install the software management stack on the Uyuni/SUSE Manager itself but rather to have a dedicated management node for each cluster to avoid any kind of conflicts. This requirement may be relaxed in the future and Uyuni/SUSE Manager may be the management node of any cluster.
- SES 6 requires to have a salt-master as part of the cluster - this will clash with the idea above of Uyuni/SUSE Manager being the salt-master of the minion. SES 7 is still under development but expected to be released in late 2020 and will probably relax this requirement. Uyuni/SUSE Manager will target SES 7: we consulted the available documentation for SES 7 (see References) and for everything that was not clear at the time of writing we looked at the documentation for SES 6.
- This is an MVP: only basic functionality for a cluster will be covered in this first iteration
- The functionality is built in a pluggable way to be easily extendable

## A new Cluster object

A new “Clusters” item in the main menu will be added.
The "Clusters" section will be available to the Administrative Roles and the new "Cluster Administrator" role.

Under Clusters, there will be:

- An “Import existing cluster” item that allows importing an existing cluster definition
- A “Create new cluster” item that allows to deploy and define a new cluster in Uyuni/SUSE Manager
- An “Overview” item that lists all the clusters currently known to Uyuni/SUSE Manager

A cluster is identified in Uyuni/SUSE Manager by:
- the cluster name
- the cluster type
- the management node (hostname) - for clusters that do not requires a management node (e.g. SHAP) one node of the cluster will be used by Uyuni/SUSE Manager as the management node.

After importing or creating a new cluster these pieces of information will be stored in the Uyuni/SUSE Manager database.
All the described operations will be also exposed in an XMLRPC API.

### Import an existing cluster

The requirement is to have an already provisioned management node for the cluster that the user wants to manage with Uyuni/SUSE Manager.
It is implied that the management node is already capable of reaching the nodes of the cluster (via passwordless SSH or any other mean requested by the cluster provider manager) and all clustering management stack is already installed in the management node.

When the import action is selected, Uyuni/SUSE Manager will register the management node to Uyuni/SUSE Manager (by replicating what is done under Systems > Bootstrapping).
Additionally, Uyuni/SUSE Manager asks for the name and the type of cluster that the user wants to register.

Uyuni/SUSE Manager will store all entered cluster details data into the database.

After successful registration, the cluster overview will be shown.

### Creating a new cluster

When creating a new cluster, Uyuni/SUSE Manager will ask:

1. Cluster name and cluster type
2. A minion to provision as the management node using a System Add-On or a Salt Formula that will install the clustering management stack on the minion. A list of available minions will be presented.
3. Uyuni/SUSE Manager will apply the Salt highstate (or the Salt formula) to provision the system as the clustering management stack.

Only the clustering management stack is provisioned on the management node at this time.

All other optional actions:
- provisioning a load balancer
- copying SSH keys from the management node to aspirant nodes of the cluster

will __not__ be managed by Uyuni/SUSE Manager and must be provisioned manually. In a future follow-up, Uyuni/SUSE Manager can make use of [Salt orchestrate runner](https://docs.saltstack.com/en/latest/topics/orchestrate/orchestrate_runner.html#orchestrate-runner) to provision these complex setups before provisioning the management node.

Uyuni/SUSE Manager will store all entered cluster details data into the database and after successful provisioning of the management node, the cluster overview will be shown.


### Cluster overview

Under “Cluster overview”, all clusters known to Uyuni/SUSE Manager will be displayed. When a cluster is selected, a new page listing all the details of the cluster will be shown, containing:

- List of all nodes of the cluster - by invoking the cluster provider manager (via Salt) on the Management Node:

  ```
  # salt <mgmt node> <cluster provider mgr>.list_nodes <cluster name>
  ```
    - For CaaSP: `salt <mgmt node> skuba.list_nodes <cluster name>`
    - For SES: `salt <mgmt node> ceph.list_nodes <cluster name>`
    - For SLE-HA/SHAP: `salt <mgmt node> crm.list_nodes <cluster name>`

- Optional information retrieved via Salt grains (populated by the product):
    - Link to the product dashboard (e.g. SES)
    - Credentials download (e.g. download `kubeconfig` from CaaSP)
- Optional information regarding the health of each node of the cluster (if supported by the cluster).

By enumerating all the functions of the Salt module corresponding to the cluster provider manager, Uyuni/SUSE Manager will offer to run all the actions that the cluster provider manager exposes.
A minimum list of actions that must be exposed by the cluster provider manager is:

* Adding a node: Uyuni/SUSE Manager will invoke the cluster provider manager on the management node of the cluster and will pass any optional parameter (requested to the user) (e.g. username, IP of the system, type of the node).

  ```
  # salt <mgmt node> <cluster provider mgr>.add_node <cluster name> <optional params>
  ```

  All the parameters of the formula have to be specified by the cluster provider manager's types.

  In a future version, Uyuni/SUSE Manager may offer the possibility to present to the user a drop-down selection of systems registered to Uyuni/SUSE Manager and not part of any cluster.

* Removing a node: Uyuni/SUSE Manager will invoke the cluster provider manager on the management node of the cluster and will pass any optional parameter (requested to the user) to the call using Salt pillar.

  ```
  # salt <mgmt node> <cluster provider mgr>.remove_node <cluster name> <optional params>
  ```

* Node reboot: Uyuni/SUSE Manager will invoke the cluster provider manager on the management node of the cluster and will pass any optional parameter (requested to the user) to the call using Salt pillar.

  ```
  # salt <mgmt node> <cluster provider mgr>.reboot_node <cluster name> <optional params>
  ```

  The implementation of how a node is rebooted is left to the specific cluster provider manager.

* Cluster upgrade: As every cluster has its peculiarities when upgrading the cluster nodes and Uyuni/SUSE Manager should be agnostic about the implementation strategy, Uyuni/SUSE Manager will invoke the cluster provider manager on the management node of the cluster and will pass any optional parameter (requested to the user) to the call using Salt pillar.

  ```
  # salt <mgmt node> <cluster provider mgr>.upgrade_cluster <cluster name> <optional params>
  ```

### Single cluster node management with Uyuni/SUSE Manager

The following actions refer to the individual cluster node registered to Uyuni/SUSE Manager. The following actions must be implemented after the cluster overview and its corresponding actions are implemented.
NOTE: registering an SES 6 node to Uyuni/SUSE Manager is not be possible as SES 6 management node is a Salt master. SES 7 will relax this requirement, as Salt will be used for node deployment only.

#### Relaxing system lock

In the cluster overview, when listing individual nodes of the cluster, Uyuni/SUSE Manager will also offer the possibility of registering an individual node to Uyuni/SUSE Manager (with System > Bootstrapping).

It is common between all analyzed cluster products that rebooting and package modification/removal are two forbidden actions on all nodes of the cluster.

By default, Uyuni/SUSE Manager will put the minion in system lock when one of the following product is detected upon registration:

* CaaSP: /etc/products.d/caasp.prod + pattern `pattern-caasp-Node`
* SES: /etc/products.d/ses.prod
* SLE-HA/SHAP: /etc/products.d/SLES_SAP.prod, /etc/products.d/sle-ha.prod

When a system is locked, no action will be executed. System lock may be disabled by the user by disabling the corresponding Salt Formula.

It will be possible to define an allowed list of actions that Uyuni/SUSE Manager can issue on a specific node by implementing a combination of selective blackout (https://github.com/uyuni-project/uyuni-rfc/pull/31/) and package locking.

A product can define a list of:
- an allowed list of actions in Uyuni/SUSE Manager action terms
- packages or patterns to lock at the minion level

This information must be provided by the product and must be inserted into Uyuni/SUSE Manager database.
Upon bootstrapping, Uyuni/SUSE Manager will issue the required package locks and the allowed list of actions will be not part of the blackout.
Example:
- CaaSP define the `zypper lock` the `patterns-caasp*` pattern
- Uyuni/SUSE Manager allows package install, modify, removal actions

#### Cluster node as special citizens in the minion domain

All systems add-on types will be disabled for installation, except for the Monitoring add-on.
When deleting a system, a cleanup of salt-minion must not be done (requested by SES).

All other actions will be inhibited by the system lock and will require special handling by being implemented in the cluster provider manager level.

#### System groups

When defining a new cluster, Uyuni/SUSE Manager also creates a system group named `<type><name>` in which all nodes of the cluster will be inserted.

## Integration requirements from an external product perspective

From the plugin perspective, a product needs to define:
- a new cluster type in Uyuni/SUSE Manager with a specific configuration (cluster type <-> cluster provider manager)
- provide a system add-on type (or a Salt Formula) that provisions the management node with cluster management software

When a new cluster product type is available in Uyuni/SUSE Manager, the association between the cluster type and its cluster provider manager is stored in the database.

Summary of what a product must provide to Uyuni/SUSE Manager:

* CaaSP:
  - Salt Formula to install CaaSP software on the management node
  - Salt Formula to install CaaSP software for control-plane/workers
  - Cluster provider manager in a Salt module: skuba
  - (Optional) Salt Formula to provision a load balancer
* SES:
  - Salt Formula to provision an SES minion
  - Salt Formula to provision the management node
  - Cluster provider manager in a Salt module: cephadm
* SLE-HA/SHAP:
  - Salt Formula to provision the management node
  - Salt Formula to provision a SLE-HA/SHAP node
  - Cluster provider manager in a Salt module: crm

## Opening Uyuni/SUSE Manager features to cluster objects

Future developments can enrich the implementations described in the RFC by converting the cluster management node into a [Salt proxy minion](https://docs.saltstack.com/en/latest/topics/proxyminion/index.html) using the SSH backend to access all cluster nodes.
In this way, the cluster object can be represented by a special minion registered to Uyuni/SUSE Manager and the user can issue some operations on the cluster object that will translate the action to all cluster nodes and collect the results. Some examples:

* Assign Salt states
* Execute Salt execution modules
* Assign software channels and manage Channel Lifecycle Management

We listed this feature as a future development because:
* The MVP actions we outlined above have higher priority
* During our experiments we encountered [this bug](https://github.com/saltstack/salt/issues/53341) with `salt-proxy`, we correctly got past it but we were still unable to register a proxied system to the `salt-master`
* Some of the features can be already implemented by scripting and using Salt on the cluster.

## SSH keys management

Any SSH key pair required for accessing the cluster nodes will be stored on the server.

The keys will be made available to the provisioning node by:
1. loading them into the `ssh-agent` on the server
2. opening a connection to the provisioning node using agent forwarding (`ssh -A`)

The connection must be opened before executing any action that might require connecting to the cluster nodes. E.g. joining a node, getting the cluster status, etc.
The server must retrieve the value of the `SSH_AUTH_SOCK` environment variable and inject into subsequent `state.apply`s as a pillar.

The salt state corresponding to the action must ensure the `SSH_AUTH_SOCK` environment variable is set correctly to allow access to the forwarded agent. 

Once the action is completed the SSH connection can be terminated.

E.g. a state that calls `skuba` to get the status of a CaaSP cluster:

```yaml
ssh_agent_socket:
    environ.setenv:
        - name: SSH_AUTH_SOCK
        - value: {{ pillar['ssh_auth_sock'] }}

cluster_status:
     cmd.run:
         - name: skuba cluster status
         - cwd: {{ pillar['cluster_dir'] }}
         - require:
           - environ: ssh_agent_socket
...
```

```
salt <provisioning.node> state.apply caasp.join pillar='{"ssh_auth_sock": "/tmp/....", ...}'
```


# Drawbacks
[drawbacks]: #drawbacks

<!-- Why should we **not** do this?

  * obscure corner cases
  * will it impact performance?
  * what other parts of the product will be affected?
  * will the solution be hard to maintain in the future? -->

# Alternatives
[alternatives]: #alternatives

<!-- - What other designs/options have been considered?
- What is the impact of not doing this? -->

# Unresolved questions
[unresolved]: #unresolved-questions

<!-- - What are the unknowns?
- What can happen if Murphy's law holds true? -->

# References

Documentation used to write this RFC:

* https://documentation.suse.com/suse-caasp/4.1/single-html/caasp-admin
* https://documentation.suse.com/suse-caasp/4.1/single-html/caasp-deployment/
* https://documentation.suse.com/suse-caasp/4.1/single-html/caasp-quickstart/
* https://documentation.suse.com/ses/6/single-html/ses-admin/
* https://documentation.suse.com/ses/6/single-html/ses-deployment/
* https://confluence.suse.com/display/SUSEEnterpriseStorage/ceph-salt%3A+How+to+use#ceph-salt
* https://documentation.suse.com/sle-ha/15-SP1/single-html/SLE-HA-guide/
* https://documentation.suse.com/sle-ha/15-SP1/single-html/
* https://documentation.suse.com/sle-ha/15-SP1/single-html/SLE-HA-install-quick/
* https://documentation.suse.com/sle-ha/15-SP1/single-html/SLE-HA-pmremote-quick

## Formulas already available

- SES:
  - ceph-salt-formula [https://github.com/ceph/ceph-salt/tree/master/ceph-salt-formula]
- SHAP:
  - https://github.com/SUSE/habootstrap-formula​
  - https://github.com/SUSE/saphanabootstrap-formula​
  - https://github.com/SUSE/sapnwbootstrap-formula
  - https://github.com/SUSE/habootstrap-formula