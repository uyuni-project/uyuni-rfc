- Feature Name: Container as a Service Platform integration with Uyuni/SUSE Manager
- Start Date: 2019-08-05
- RFC PR: https://github.com/uyuni-project/uyuni-rfc/pull/10

# Summary
[summary]: #summary

This RFC describes how Uyuni/SUSE Manager can be leveraged to perform cross-product integration with a cluster solution like Container as a Service Platform.

# Motivation
[motivation]: #motivation

<!-- - Why are we doing this?
- What use cases does it support?
- What is the expected outcome?

Describe the problem you are trying to solve, and its constraints, without coupling them too closely to the solution you have in mind. If this RFC is not accepted, the motivation can be used to develop alternative solutions. -->

Uyuni/SUSE Manager is the systems management tool and must offer to the end-user the possibility to deploy and manage other SUSE products like CaaS Platform.

We will be focusing first on the following general scenarios:

1. Deploy a cluster using Uyuni/SUSE Manager
2. Manage a cluster using Uyuni/SUSE Manager

The two subsequent CaaS Platform-specific sections will follow.

# Detailed design
[design]: #detailed-design

<!-- This is the bulk of the RFC. Explain the design in enough detail for somebody familiar with the product to understand, and for somebody familiar with the internals to implement.

This section should cover architecture aspects and the rationale behind disruptive technical decisions (when applicable), as well as corner-cases and warnings. Whenever the new feature creates new user interactions, this section should include examples of how the feature will be used. -->

## Generic design: integrate Uyuni/SUSE Manager with a cluster provider

### Deploy a cluster using Uyuni/SUSE Manager

Under Uyuni/SUSE Manager main menu, a new menu item "Clusters" should be introduced.
All deployable and manageable cluster products (e.g. CaaSP, SOC, SES) will be in the sub-menu.

Under that item, it should be possible to create, edit, and remove a cluster.

To create a cluster, a user has to enter its name.

The general details about the cluster (e.g. name) are saved into corresponding database tables (e.g. `susecluster`).
Every other cluster-specific details (depending on the cluster provider) can be saved in dynamic JSON schemas that can be optionally versioned in a git repository.

API support for all the activities described below should be implemented as well as front-end support.

A new system group will be created for all the nodes that constitute the cluster.
A new role: "Cluster Administrator" will be created. This is the same as the "Image Administrator" Uyuni/SUSE Manager currently has for containers and OS images.
Along with root users of Uyuni/SUSE Manager, Cluster Administrator can create, deploy and manage a cluster.
All the other users without this role cannot see the nodes of the cluster unless they are made System Group Administrators.

#### Cluster requirements

If the cluster required a specific set of nodes optionally with a defined configuration, the cluster provider must offer a way to deploy the whole infrastructure automatically, e.g. using AutoYaST profiles.

Uyuni/SUSE Manager will provision bare-metal machines using the supplied AutoYaST profile to have a complete set of machines ready to be hosting the cluster.

#### The Management Node

The cluster provider must also indicate:

- how and the number of Management Node(s) must be elected among the provisioned machines (e.g. based on hardware requirements)
- how Management Node(s) should be deployed (e.g. additional software to be installed via AutoYaST or Salt states)
- whether Management Node(s) can be managed by Uyuni/SUSE Manager (specifically: can users manage the updates of the Management Node via Uyuni/SUSE Manager?)

#### Cluster bootstrapping

The cluster must be initiated by the Management Node that has all the tools to bootstrap and manage the cluster. Specific instructions on how to bootstrap the cluster must be provided.
Questions that need to be answered by the cluster provider:
- Upon successful bootstrapping, can the worker nodes be managed by Uyuni/SUSE Manager?
- Do the nodes have a specific agent running on them and/or can we install a `salt-minion` or use `salt-ssh` on those nodes?
- Can the nodes be managed by Uyuni/SUSE Manager? Can the packages be updated or do they require specific handling by the Management Node?

### Manage a cluster using Uyuni/SUSE Manager

Uyuni/SUSE Manager offers to show the status of the running cluster by either accessing the cluster directly or via the Management Node.
In this regard, the cluster provider should provide a way to expose the cluster status (e.g. running nodes, the health of each node, monitoring metrics...) to Uyuni/SUSE Manager.

#### Add and removal of nodes to the cluster

Uyuni/SUSE Manager also offers the possibility of adding and removing nodes to the cluster:

- To add a node from scratch, an AutoYaST profile can be reused
- To remove a node, Uyuni/SUSE Manager must remove the node from the cluster using the Management Node and issuing the proper procedure

Uyuni/SUSE Manager should be instructed to perform additional actions depending on the role of added/removed node (e.g. control plane, worker, load balancer, ...).

#### Cluster upgrade

If every node of the cluster is not directly registered to Uyuni/SUSE Manager, Uyuni/SUSE Manager should offer the possibility to use the Management Node to trigger an update of every node in the cluster, following the standard procedure of upgrading predisposed by the cluster provider.

Also, Uyuni/SUSE Manager must coordinate the Management Node to issue a correct upgrade procedure of the product (e.g. from CaaS Platform version 3 to 4): this process is initiated by Uyuni/SUSE Manager by using the cluster provider framework implementation (e.g. `skuba`) to handle the upgrade operation.

#### Application deployment

Uyuni/SUSE Manager can also offer the possibility of deploying an application on top of the cluster deployed (e.g. Kubernetes deployment descriptor to deploy a Kubernetes operator). In this case, the cluster provider must provide the Management Node of the necessary tooling to deploy an application using an API. Uyuni/SUSE Manager makes use of the Management Node to deploy a provided application.

#### Specific usage of Uyuni/SUSE Manager features

One cluster deployment can also leverage Uyuni/SUSE Manager features via API.
For example, a cluster deployment may invoke `CVEAuditHandler` and test if a container image built by SUSE Manager is vulnerable against a particular CVE and decide whether to allow the deployment of the image or not.

## CaaS Platform-specific design

It is intended that Uyuni/SUSE Manager will not deal and will not know with the application deployed on top of CaaS Platform.

### Deploy a CaaS platform cluster using Uyuni/SUSE Manager

  #### Cluster Deployment

  Under Uyuni/SUSE Manager main menu, a new sub-menu item "CaaS Platform" should be introduced under "Clusters".

  Under that item, it should be possible to create, edit, and remove a cluster.

  To create a cluster, a user has to enter its name.

  Then, the user will be requested to associate a load balancer and a Management Node to the cluster.

  The cluster is then identified by:
  - a unique name
  - the FQDN of the load balancer
  - the hostname of its Management Node

  (more on the load balancer and the Management Node below).

  Every detail about the cluster is saved into corresponding database tables (e.g. `susecaaspcluster`).

  NOTE: the load balancer is unique for the cluster and it is a level 4 load balancer (no TLS termination). The Management Node can manage different clusters at the same time.

  #### Cluster node requirements

  Every machine that needs to be part of cluster (either a control plane or a worker) has strictly hardware and software requirements (e.g.: every machine has to run SUSE Linux Enterprise 15, has a fixed IP that can be resolved, [a precise partition layout with no swap](https://susedoc.github.io/doc-caasp/beta/caasp-deployment/single-html/#_suse_linux_enterprise_server_installation), at least 2 CPUs, etc.). From now on, these requirements will be called "CaaS Platform node requirements".

  NOTE: In the future, there might be a CaaSP Community that will work on openSUSE. The stack would then be:
  - CaaSP 4.0 + SUSE Manager 4.0
  - CaaSP Community 4.0 + Uyuni Server 4.0

  For this reason, the CaaS Platform [supports deployment on](https://susedoc.github.io/doc-caasp/beta/caasp-deployment/single-html/#_platform):

  - VMware ESXi
  - SUSE OpenStack Cloud 8
  - [Bare-metal deployment](https://susedoc.github.io/doc-caasp/beta/caasp-deployment/single-html/#_deployment_on_bare_metal)

  CaaS Platform also provides templates for the above providers that can be found in the `skuba` package (in `/usr/share/caasp/{AutoYaST, terraform}`). For VMware and SUSE OpenStack Cloud, the template is provided via Terraform. The up-to-date version of these templates can be found at:
  - for VMware: https://github.com/SUSE/skuba/tree/master/ci/infra/vmware
  - for SUSE OpenStack Cloud 8: https://github.com/SUSE/skuba/tree/master/ci/infra/openstack
  - for AutoYaST: https://github.com/SUSE/skuba/blob/master/ci/infra/bare-metal/AutoYaST.xml

  One additional scenario would be to use [an existing node running SUSE Linux Enterprise 15](https://susedoc.github.io/doc-caasp/beta/caasp-deployment/single-html/#_deployment_on_existing_sles_installation). In this particular case, we should check that the CaaS Platform requirements are satisfied before offering this node to be part of the cluster.
  These checks can be done using Salt grains.

  #### Templating selection

  Uyuni/SUSE Manager has an existing integration with VMWare (Virtual Host Manager). This integration is read-only, as Uyuni/SUSE Manager can show the guests running in the VMWare host and display information about the guests.
  Currently, there is no integration with SUSE OpenStack Cloud 8.
  Additionally, Uyuni/SUSE Manager has not currently any integration with `terraform`.

  Uyuni/SUSE Manager supports autoinstallation via AutoYaST.

  For the reasons above, it looks promising to invest in two directions for fulfilling the integration in the deployment phase:
  1. Existing node: Uyuni/SUSE Manager must filter the eligible nodes that satisfy all CaaS Platform node requirements among the already registered Salt minions already available
  2. AutoYaST deployment: in case the user wants to deploy additional auto-installed nodes, Uyuni/SUSE Manager should guide the user into setting up as many nodes of the cluster by auto-installing them using the AutoYaST profile provided by `skuba`. For example, Uyuni/SUSE Manager can offer the possibility to register empty system profiles and display those nodes as available when selecting the AutoYaST deployment target.

  **NOTE**: `skuba` also provides templates for AWS and libvirt, but those are not supported at the moment of writing.

  #### The Management Node

  CaaS Platform requires a "Management Node" to deploy itself. Uyuni/SUSE Manager will offer to elect as Management Node:

  - The Uyuni/SUSE Manager itself. In this case, SUSE Manager does not need to manage itself by installing `salt-minion` and will just apply the Management Node state. It doesn't require an extra management node for CaaSP (save resources and time) and `skuba` can be installed inside on top of a regular SLE15 SP1 (it is not going to cause any interference with the stack used by SUSE Manager).

  - A node deployed for this particular purpose (must run SUSE Linux Enterprise 15 SP1). Provided that the machine is a minion (Salt-only feature) and is running the correct OS (checked via grains), we can introduce a new entitlement ("Add-On System type") to entitle an existing machine as a Management Node.
  - An ephemeral container

  In case we do not select the container way, the user has also to assign the following channels to the Management Node (channels must be already synced by Uyuni/SUSE Manager):

  - SUSE CaaS Platform Extension to SUSE Linux Enterprise 15
  - SUSE Containers Module 15 SP1 x86_64

  In the corresponding Salt state, that must be applied via the usual highstate, the state must:

  - Generate an SSH keypair for accessing the cluster nodes. It is also possible to generate the keys locally to the Uyuni/SUSE Manager server and make use of SSH's forwarding agent mechanism.
  - Import the SSH key into the `ssh-agent` and `export` the `SSH_AUTH_SOCK` environment variable
  - Install the pattern `SUSE-CaaSP-Management` (depends on `terraform` and `skuba` packages)

  e.g.

  ```
  mgr_install_caasp_tools:
  pkg.installed:
    - pkgs:
      - SUSE-CaaSP-Management

  mgr_sshd_installed:
    pkg.installed:
      - name: openssh

  generate_ssh_key_management:
    cmd.run:
      - name: ssh-keygen -q -N '' -f /var/lib/caasp-management/.ssh/id_rsa
      - unless: test -f /var/lib/caasp-management/.ssh/id_rsa
    require:
      - pkg: mgr_sshd_installed
  ```

  Finally, Uyuni/SUSE Manager copies the templates for deployment files provided by `skuba` (in `/usr/share/caasp/AutoYaST/bare-metal/AutoYaST.xml`) from the Management Node to the Uyuni/SUSE Manager itself.

  Given that the Management Node is a Salt minion managed by Uyuni/SUSE Manager, every update for `SUSE-CaaSP-Management` can be installed directly from Uyuni/SUSE Manager. Extra care should be put into protecting the cluster configuration file generated by `skuba` during cluster bootstrapping (`rsync` into Uyuni/SUSE Manager nightly and version it into a `git` repository).

  Summarizing: the Management Node, either in a native or containerized way must have:
  - the SSH keys to access the CaaS Platform nodes
  - the cluster definition (generated after cluster bootstrapping)
  - access to the management packages (`SUSE-CaaSP-Management` pattern)

  #### Load balancer

  Every CaaS Platform production cluster must have at least one load balancer associated. There is not a standardized way to deploy a load balancer. In this regard, the user has to configure the load balancer in his/her fashion, but Uyuni/SUSE Manager can provide hints to deploy HAProxy with SUSE Linux Enterprise Server with HA Extension.

  #### Bootstrapping an empty cluster

  Salt will invoke `skuba` (using `cmd.run`) in the Management Node. `skuba` does not offer an API yet (is in the progress).

  NOTE: every `skuba` command will make us of the `SSH_AUTH_SOCK` variable. The `Management Node` must run and import the SSH key deployed during provisioning into the `ssh-agent`.
  Example:

  ```
  bootstrap_control_plane:
    cmd.run:
      - name: skuba cluster init --control-plane <load balancer IP> <cluster name>
  ```

  The parameters above are already known to Uyuni/SUSE Manager.

  #### Control plane and worker nodes

  #### Registering control plane and worker to Uyuni/SUSE Manager

  The core of the CaaS Platform is control plane and worker nodes. The Management Node, instructed by Uyuni/SUSE Manager, will take care of bootstrapping control plane and worker nodes.

  The critical part of every control plane and worker node is handling updates of the underlying Kubernetes-related packages (`kubernetes-kubeadm kubernetes-kubelet kubernetes-client cri-o cni-plugins`): these updates must be handled with `skuba` from the Management Node.

  [`skuba-update` will take care of updating the Base Operating System automatically](https://susedoc.github.io/doc-caasp/beta/caasp-admin/single-html/#_base_os). `skuba-update` will honor the repository configuration:

  - SCC
  - registry.suse.com
  - Uyuni/SUSE Manager with Content Lifecycle Management filters

  NOTE: `skuba-update` will not update the Management Node - this upgrade must be initiated by SUSE Manager if the Management Node is not the SUSE Manager node itself.

  #### Bootstrapping control plane and worker nodes

  In Uyuni/SUSE Manager under "CaaS Platform > Deployment > cluster name" there will be a list of machines that:
  - Are not part of any other CaaS Platform cluster
  - Are not already bootstrapped into the current cluster
  - Satisfy the CaaS Platform node requirements: those machines are either bootstrapped via the AutoYaST profile or are already registered with Uyuni/SUSE Manager and satisfy the node requirements (checked via grains).

  The user will then have the option to bootstrap the selected machine as the first control plane (or subsequently, as an additional control plane or worker). Upon triggering of this event, the Uyuni/SUSE Manager will:

  - operate on the to-be control plane or worker node:
    - Copy the SSH key of the Management Node for passwordless login in the node. In case of existing machines, the SSH file must be copied (e.g. via Salt), whereas the AutoYaST case will be already covered during provisioning
    - Assign the CaaS Platform channels assigned via Salt (SUSE CaaS Platform Extension to SUSE Linux Enterprise 15 and SUSE Containers Module 15 SP1 x86_64)
    - Register the machine from Uyuni/SUSE Manager (if it is not registered). In this case, the node gains all the advantages of being managed by Uyuni/SUSE Manager (e.g. access to mirrored channels specified above)

    NOTE - Channel syncing: Uyuni/SUSE Manager must sync __all__ the packages that constitute the `patterns-caasp-Node` pattern even in the case of package pinning or other user's customizations. Being in a situation where `skuba` is updated while `patterns-caasp-Node` can lead to problems.

    NOTE - Minion registration: Uyuni/SUSE Manager will implement countermeasures to restrict the user to issue a list of actions (that must be identified and consolidated in a list) on the cluster nodes, either via user interface or API. Some examples of restricted actions:
    - Remote commands
    - Package upgrade
    - System reboot
    Issuing those actions might result in the malfunction of the cluster. The restriction can be implemented using [Minion Blackout Configuration](https://docs.saltstack.com/en/latest/topics/blackout/) or the [`zypper` package locking](https://docs.saltstack.com/en/latest/ref/modules/all/salt.modules.zypperpkg.html#salt.modules.zypperpkg.add_lock).

  - operate on the Management Node:
    - Salt will invoke `skuba` (using `cmd.run`) to bootstrap the first control plane or make the selected node join the cluster. The user must specify via the web interface or API call parameters which user to use for passwordless login (in this case `sles`) and whether to use `sudo` or not.

    Example:

    ```
    bootstrap_first_control_plane:
      cmd.run:
        - name: skuba node bootstrap --user sles --sudo --target <node IP> <node name>

    bootstrap_additional_control_plane:
      cmd.run:
        - name: skuba node join --role master --user sles --sudo --target <node IP> <node name>

    bootstrap_worker:
      cmd.run:
        - name: skuba node join --role worker --user sles --sudo --target <node IP> <node name>
    ```

    Uyuni/SUSE Manager will check the return code of the `skuba` command and, in case of errors, show the raw output.

### Manage a CaaS Platform cluster using Uyuni/SUSE Manager

#### Show node status

Individual nodes that constitute the cluster can be accessed and managed as already happen with Uyuni/SUSE Manager, with the restrictions described above.
Hardware details of the node will be shown.

From a Uyuni/SUSE Manager point of view, it would make sense to create a system group to identify the nodes part of the cluster.

#### Show cluster status

Uyuni/SUSE Manager shows the status of the cluster by invoking `skuba cluster status` on the Management Node (via Salt).

E.g. The output is presented in the "CaaS Platform > cluster name" section:

```
NAME         OS-IMAGE                              KERNEL-VERSION        CONTAINER-RUNTIME   HAS-UPDATES   HAS-DISRUPTIVE-UPDATES
cp0       SUSE Linux Enterprise Server 15 SP1   4.12.14-110-default   cri-o://1.13.3      <none> <none>
worker0   SUSE Linux Enterprise Server 15 SP1   4.12.14-110-default   cri-o://1.13.3      <none> <none>
```

#### Removing nodes from the cluster

A node can also be removed from the cluster:

- temporarily (drained and cordoned off): [using `kubectl`](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/#use-kubectl-drain-to-remove-a-node-from-service) from the Management Node via Salt.
- permanently: by invoking `skuba node remove <nodename>` via Salt. NOTE: this removal is permanent and the cluster cannot join any cluster in the future. A complete reinstallation is required and Uyuni/SUSE Manager must offer the user to re-provision the node from scratch, e.g. via AutoYaST.

Example state:

```
remove_node:
      cmd.run:
        - name: skuba node remove <nodename>
```

NOTE: Other `skuba` options can be implemented in the future (e.g. resetting and reconfiguring a node).

#### Cluster upgrade

All the cluster updates must be handled by `skuba`. NOTE: it is recommended to upgrade the whole cluster machine by machine, all of them at the same time.

Uyuni/SUSE Manager can check and notify the user if an update for the cluster is present by triggering `skuba cluster upgrade plan` on the Management Node (using Salt) and check if a new output is available in a cron fashion (e.g. Taskomatic job).

Uyuni/SUSE Manager will then interface with the Management node and upgrade every control plane in the cluster first:

`skuba node upgrade apply --target <control-plane-node-ip> --user <user> --sudo`

and then every worker:

`skuba node upgrade apply --target <worker-node-ip> --user <user> --sudo`

This can be done by supplying the command to the Management Node via Salt.

NOTE: CaaS Platform stack is also deployed via containers. We will need to update this section when the CaaS Platform team concludes the "add-ons update story".

#### CVE Auditing

By leveraging the existing feature of CVE Auditing, Uyuni/SUSE Manager can detect and notify the user whether the cluster is running a vulnerable image. When Uyuni/SUSE Manager rebuilds the image and patches it, Uyuni/SUSE Manager can also guide the user in modifying the Kubernetes deployment to pull the updated image (in case of `imagePullPolicy:` is not `Always`) or do a `kubectl rolling-update`.
In this example, Uyuni/SUSE Manager can offer two strategies:
- just warn that the image is vulnerable (conservative)
- refuse to start the vulnerable cluster (disruptive)

The final choice about the strategy is up to the user.

##  Future work

### Cluster configuration customization

The configuration of the cluster is in the Management Node and can optionally be customized by the user directly from Uyuni/SUSE Manager (e.g. Uyuni/SUSE Manager offering a text editor to configure [integrating an external LDAP](https://susedoc.github.io/doc-caasp/beta/caasp-deployment/single-html/#_integrate_external_ldap) or [configure `kured`](https://susedoc.github.io/doc-caasp/beta/caasp-deployment/single-html/#_prevent_nodes_running_special_workloads_from_being_rebooted)).

Single Sign-On is out of scope until further developments from the Product Management.

### CVE Auditing

A useful addition would be to have Uyuni/SUSE Manager as an admission controller for rejecting pod creation whenever an image used is vulnerable.

### Deploy OpenStack Cloud

If OpenStack Cloud will be deployed using AirShip (still under discussion), the approach described in this RFC can be further reused for deploying and managing an OpenStack Cloud, given that `skuba` is similar to `airshipctl`:

- provision nodes to be part of the cloud
- tag nodes and bootstrap them to be part of the cloud
- manage the lifecycle of the cloud

NOTE: Uyuni/SUSE Manager has just the knowledge of deploying and managing clusters and does not know what is running on top.

### Run other products in the cluster

It would also be possible, after that the cluster has been deployed, to deploy other SUSE products on top of the cluster (e.g. SUSE OpenStack Cloud, SUSE Enterprise storage):

- CaaS Platform deploys a SUSE Application Lifecycle operator on top of the cluster with a set of custom resources (CRDs)
- Uyuni/SUSE Manager can then deploy SOC, SES or any other combination of products on top of the cluster and manage the lifecycle of the deployed products by simply having access to the `kubectl` configuration file

In this case, Uyuni/SUSE Manager would be the central point of deployment for other products based on CaaS Platform and show the health of every cluster installed, while offering the possibility of managing and upgrading the cluster.

### Kubernetes dashboard

In the future developments, Uyuni/SUSE Manager can also embed the Kubernetes dashboard to help the user in deploy applications on top of CaaS Platform.
The alternative of offering to configure application deployments from Uyuni/SUSE Manager would be seen as a second-choice solution compared to Kubernetes dashboard.

### Re-use of deployment structure

A small part of the deployment of the CaaS Platform can be reused for other Kubernetes distributions (e.g. OpenShift); deploying on bare metal requires machines configured with very specific requirements and that can be solved with AutoYaST (or Kickstart in the Red Hat case).

Every distribution uses then its deployment helper (OpenShift uses `openshift-install`) to bootstrap the cluster. In this regard, `skuba` is only targeting SUSE CaaS Platform and cannot be reused for bootstrapping and managing a cluster that is not CaaS Platform based.

# Drawbacks
[drawbacks]: #drawbacks

What if the customer wants to deploy another Kubernetes distribution? If we are using `skuba`, we only target CaaS Platform deployments.
When targeting a different Kubernetes distribution a set of integration points with `kubectl` must be defined as per the generic design described in this RFC.

# Alternatives
[alternatives]: #alternatives

- Managing the cluster with `kubectl` and importing its `kubeconfig` without using `skuba`: limited functionality, every Kubernetes distribution must be treated according to its specification and provide an actuator for the `cluster-api` (that is targeting Container as a Service Platform 5), lots of duplicate work.

# Unresolved questions
[unresolved]: #unresolved-questions
