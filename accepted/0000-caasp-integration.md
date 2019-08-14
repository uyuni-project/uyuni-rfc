- Feature Name: Container as a Service Platform integration with SUSE Manager
- Start Date: 2019-08-05
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

This RFC describes how SUSE Manager can be leveraged to perform cross-product integration with Container as a Service Platform.

# Motivation
[motivation]: #motivation

<!-- - Why are we doing this?
- What use cases does it support?
- What is the expected outcome?

Describe the problem you are trying to solve, and its constraints, without coupling them too closely to the solution you have in mind. If this RFC is not accepted, the motivation can be used to develop alternative solutions. -->

SUSE Manager is the systems management tool and must offer to the end-user the possibility to deploy and manage other SUSE products like CaaS Platform.

We will be focusing on the following scenarios:

1. Deploy a CaaS Platform cluster using SUSE Manager
2. Manage a CaaS Platform cluster using SUSE Manager


# Detailed design
[design]: #detailed-design

<!-- This is the bulk of the RFC. Explain the design in enough detail for somebody familiar with the product to understand, and for somebody familiar with the internals to implement.

This section should cover architecture aspects and the rationale behind disruptive technical decisions (when applicable), as well as corner-cases and warnings. Whenever the new feature creates new user interactions, this section should include examples of how the feature will be used. -->

## Deploy a CaaS platform cluster using SUSE Manager

  ### Cluster Deployment

  Under SUSE Manager main menu, a new menu item "CaaS Platform" should be introduced.

  Under that item, it should be possible to create, edit, and remove a cluster.

  To create a cluster, a user has to enter its name.

  Then, the user will be requested to associate a load balancer and a management node to the cluster.

  The cluster is then identified by:
  - a unique name
  - the hostnames of the load balancers
  - the hostname of its management node

  (more on the load balancer and the management node below).

  Every detail about the cluster is saved into corresponding database tables (e.g. `susecaaspcluster`).

  NOTE: the load balancer is unique for the cluster and it is a level 4 load balancer (no TLS termination). The management node can manage different clusters at the same time.

  #### Cluster node requirements

  Every machine that needs to be part of cluster (either a control plane or a worker) has strictly hardware and software requirements (e.g.: every machine has to run SUSE Linux Enterprise 15, has a fixed IP that can be resolved, [a precise partition layout with no swap](https://susedoc.github.io/doc-caasp/beta/caasp-deployment/single-html/#_suse_linux_enterprise_server_installation), at least 2 CPUs, etc.). From now on, these requirements will be called "CaaS Platform node requirements".

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

  ##### Templating selection
  
  SUSE Manager has an existing integration with VMWare (Virtual Host Manager). This integration is read-only, as SUSE Manager can show the guests running in the VMWare host and display information about the guests.
  Currently, there is no any integration with SUSE OpenStack Cloud 8.
  Additionally, SUSE Manager has not currently any integration with `terraform`.

  SUSE Manager supports autoinstallation via AutoYaST.

  For the reasons above, it looks promising to invest in two directions for fulfilling the integration in the deployment phase:
  1. Existing node: SUSE Manager must filter the eligible nodes that satisfy all CaaS Platform node requirements among the already registered Salt minions already available
  2. AutoYaST deployment: in case the user wants to deploy additional autoinstalled node, SUSE Manager should guide the user into setting up as many nodes of the cluster by autoinstalling them using the AutoYaST profile provided by `skuba`.

  **NOTE**: skuba also provides templates for AWS and libvirt, but those are not supported at the moment of writing.

  ##### The Management Node

  CaaS Platform requires a "Management Node" to deploy itself. The Management node must run SUSE Linux Enterprise 15 SP1.
  The Management Node will be used for deployment of the CaaS Platform cluster, and cannot be re-used to be part of the cluster.

  Provided that the machine is a minion (Salt-only feature) and is running the correct OS (checked via grains), we can introduce a new entitlement ("Add-On System type") to entitle the machine as a Management Node.

  As it already happens with Container Build Host and OS Image Build Host, the user has also to assign the following channels to the Management Node:

  - SUSE CaaS Platform Extension to SUSE Linux Enterprise 15
  - SUSE Containers Module 15 SP1 x86_64 

  These channels must be already synced by SUSE Manager.

  In the corresponding Salt state, that must be applied via the usual highstate, the state must:

  - Generate an SSH keypair for accessing the cluster nodes. It is also possible to generate the keys locally to the SUSE Manager server and make use of SSH's forwarding agent mechanism.
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

  Finally, SUSE Manager copies the templates for deployment files provided by `skuba` (in `/usr/share/caasp/AutoYaST/bare-metal/AutoYaST.xml`) from the Management Node to the SUSE Manager itself.

  Given that the Management Node is a Salt minion managed by SUSE Manager, every update for `SUSE-CaaSP-Management` can be installed directly from SUSE Manager. Extra care should be put into protecting the cluster configuration file generated by `skuba` during cluster bootstrapping (rsync into SUSE Manager nightly?).

  ##### Load balancer

  Every CaaS Platform production cluster must have at least one load balancer associated. There is not a standardized way to deploy a load balancer. One example that the CaaS Platform suggests using is the [`nginx` TCP Load Balancer with passive health checks](https://susedoc.github.io/doc-caasp/beta/caasp-deployment/single-html/#_configuring_the_load_balancer).

  In this case, every Salt minion registered with SUSE Manager that runs SUSE Linux Enterprise 15 can be used to be a load balancer. The configuration of the load balancer can be offered via a new "CaaS Platform" entitlement that modifies the highstate of the minion by configuring `nginx` as the load balancer.

  Every update to the load balancer `nginx` will be handled via SUSE Manager.

  ##### Bootstrapping an empty cluster

  Salt will invoke `skuba` (using `cmd.run`) in the Management Node. Unfortunately, `skuba` does not offer an API yet (is in the progress).

  NOTE: every `skuba` command will make us of the `SSH_AUTH_SOCK` variable. The `Management Node` must run and import the SSH key deployed during provisioning into the `ssh-agent`.
  Example:

  ```
  bootstrap_control_plane:
    cmd.run:
      - name: skuba cluster init --control-plane <load balancer IP> <cluster name>
  ```

  The parameters above are already known to SUSE Manager.

  It is probably not in the scope of this RFC to offer to the user the ability to customize the configuration directly from SUSE Manager, but it will be in the future. At this point, the configuration of the cluster is in the Management Node and can be customized by the user (e.g. [integrating an external LDAP](https://susedoc.github.io/doc-caasp/beta/caasp-deployment/single-html/#_integrate_external_ldap) or [configure `kured`](https://susedoc.github.io/doc-caasp/beta/caasp-deployment/single-html/#_prevent_nodes_running_special_workloads_from_being_rebooted)). 
  
  Single Sign-On is out of scope until further developments from the Product Management.
  
  ##### Control plane and worker nodes

  ###### Registering control plane and worker to SUSE Manager

  The core of the CaaS Platform is control plane and worker nodes. The Management Node, instructed by SUSE Manager, will take care of bootstrapping control plane and worker nodes.

  The critical part of every control plane and worker node is handling updates of the underlying Kubernetes-related packages (`kubernetes-kubeadm kubernetes-kubelet kubernetes-client cri-o cni-plugins`): these updates must be handled with `skuba` from the Management Node.

  [`skuba-update` will take care of updating the Base Operating System](https://susedoc.github.io/doc-caasp/beta/caasp-admin/single-html/#_base_os): this means we cannot register any control plane or worker node with SUSE Manager (otherwise an end-user could apply updates to the machine).
  In case the machines are registered to SUSE Manager, the machines will be de-registered during the bootstrapping.
  
  ###### Bootstrapping control plane and worker nodes

  In SUSE Manager under "CaaS Platform > Deployment > cluster name" there will be a list of machines that:
  - are not part of any other CaaS Platform cluster
  - are not already bootstrapped into the current cluster
  - satisfy the CaaS Platform node requirements: those machines are either bootstrapped via the AutoYaST profile or are already registered with SUSE Manager and satisfy the node requirements (checked via grains).

  The user will then have the option to bootstrap the selected machine as the first control plane (or subsequently, as an additional control plane or worker). Upon triggering of this event, the SUSE Manager will:

  - operate on the to-be control plane or worker node:
    - Copy the SSH key of the Management Node for passwordless login in the node. In case of existing machines, the SSH file must be copied (e.g. via Salt), whereas the AutoYaST case will be already covered during provisioning.
    - Assign the CaaS Platform channels assigned via Salt (SUSE CaaS Platform Extension to SUSE Linux Enterprise 15 and SUSE Containers Module 15 SP1 x86_64), whereas the AutoYaST case will be already covered during provisioning.
    - De-register the machine from SUSE Manager (if it is registered)

  - operate on the Management Node:
    - Salt will invoke `skuba` (using `cmd.run`) to bootstrap the first control plane or make the selected node join the cluster. The user must specify which user to use for passwordless login (in this case `sles`) and whether to use `sudo` or not.

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

    SUSE Manager will check the return code of the `skuba` command and, in case of errors, show the raw output.

## Manage a CaaS Platform cluster using SUSE Manager

### Show cluster status

SUSE Manager shows the status of the cluster by invoking `skuba cluster status` on the Management Node (via Salt).

E.g. of the output:

```
NAME         OS-IMAGE                              KERNEL-VERSION        CONTAINER-RUNTIME   HAS-UPDATES   HAS-DISRUPTIVE-UPDATES
cp0       SUSE Linux Enterprise Server 15 SP1   4.12.14-110-default   cri-o://1.13.3      <none> <none>
worker0   SUSE Linux Enterprise Server 15 SP1   4.12.14-110-default   cri-o://1.13.3      <none> <none>
```

The output is presented in the "CaaS Platform > cluster name" section.

### Removing nodes from the cluster

A node can also be removed from the cluster:

- temporarily (drained and cordoned off): [using `kubectl`](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/#use-kubectl-drain-to-remove-a-node-from-service) from the Management Node via Salt.
- permanently: by invoking `skuba node remove <nodename>` via Salt. NOTE: this removal is permanent and the cluster cannot join any cluster in the future (a complete reinstallation is required to so).

Example state:

```
remove_node:
      cmd.run:
        - name: skuba node remove <nodename>
```

NOTE: Other `skuba` options can be implemented in the future (e.g. resetting and reconfiguring a node).

### Cluster upgrade

All the cluster updates must be handled by `skuba`.

SUSE Manager can check and notify the user if an update for the cluster is present by triggering `skuba cluster upgrade plan` on the Management Node (using Salt) and check if a new output is available in a cron fashion (e.g. Taskomatic job).

SUSE Manager will then interface with the Management node and upgrade every control plane in the cluster first:

`skuba node upgrade apply --target <control-plane-node-ip> --user <user> --sudo`

and then every worker:

`skuba node upgrade apply --target <worker-node-ip> --user <user> --sudo`

This can be done by supplying the command to the Management Node via Salt.

### CVE Auditing

By leveraging the existing feature of CVE Auditing, SUSE Manager can detect and notify the user whether the cluster is running a vulnerable image. When SUSE Manager rebuilds the image and patches it, SUSE Manager can also guide the user in modifying the Kubernetes deployment to pull the updated image (in case `imagePullPolicy:` is not `Always`) or do a `kubectl rolling-update`.

## Future work

### CVE Auditing

An useful addition would be to have SUSE Manager as an admission controller for rejecting pod creation whenever an image used is vulnerable.

### Deploy OpenStack Cloud

If OpenStack Cloud will be deployed using AirShip (still under discussion), the approach described in this RFC can be further reused for deploying and managing an OpenStack Cloud, given that `skuba` is similar to `airshipctl`:

- provision nodes to be part of the cloud
- tag nodes and bootstrap them to be part of the cloud
- manage the lifecycle of the cloud

### Run other products in the cluster

It would also be possible, after that the cluster has been deployed, to deploy other SUSE products on top of the cluster (e.g. SUSE OpenStack Cloud, SUSE Enterprise storage): 

- CaaS Platform deploys a SUSE Application Lifecycle operator on top of the cluster with a set of custom resources (CRDs)
- SUSE Manager can then deploy SOC, SES or any other combination of products on top of the cluster and manage the lifecycle of the deployed products

In this case, SUSE Manager would be the central point of deployment for other products based on CaaS Platform and show the health of every cluster installed, while offering the possibility of managing and upgrading the cluster.

### Kubernetes dashboard

In the future developments, SUSE Manager can also embed the Kubernetes dashboard to help the user in deploy applications on top of CaaS Platform.
The alternative of offering to configure application deployments from SUSE Manager would be seen as a second-choice solution compared to Kubernetes dashboard.

### Re-use of deployment structure

A small part of the deployment of the CaaS Platform can be reused for other Kubernetes distributions (e.g. OpenShift); deploying on bare metal requires machines configured with very specific requirements and that can be solved with AutoYaST (or Kickstart in the Red Hat case).

Every distribution uses then its deployment helper (OpenShift uses `openshift-install`) to bootstrap the cluster. In this regard, `skuba` is only targeting SUSE CaaS Platform and cannot be reused for bootstrapping and managing a cluster that is not CaaS Platform based.

# Drawbacks
[drawbacks]: #drawbacks

What if the customer wants to deploy another Kubernetes distribution?
If we are using `skuba`, we only target CaaS Platform deployments.

# Alternatives
[alternatives]: #alternatives

- Managing the cluster with `kubectl` and importing its `kubeconfig` without using `skuba`: limited functionality, every Kubernetes distribution must be treated according to its specification, lots of duplicate work.

# Unresolved questions
[unresolved]: #unresolved-questions

Ctrl-F: TODO
