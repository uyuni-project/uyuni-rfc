- Feature Name: SUSE Manager <-> CaaSP integration
- Start Date: 2017-06-20

# Unimplemented note

This RFC was exploratory in nature and has not been implemented yet. It still documents possible options.

# Summary
[summary]: #summary

This RFC describe how to deploy and manage CaaSP with SUSE Manager

# Motivation
[motivation]: #motivation

SUSE Manager is our main systems management tool and should be able to manage
all existing SUSE Products.

With CaaSP we have to solve several special situations:

1. CaaSP is using its own salt-master
2. CaaSP is using MicroOS which provide (only) transactional updates

# Detailed design
[design]: #detailed-design

## Deployment

SUSE Manager provide the capability to deploy using autoyast installation.
CaaSP itself provide a default autoyast template for setting up the worker.
The additional steps required to configure an admin-node are minimal.

SUSE Manager could provide templates for CaaSP deployment.

## Management

To manage MicroOS the system should be registered at SUSE Manager.
This is also needed to get the repositories the local SUSE Manager.

With SUSE Manager repository management the admin has the full power of
cloning channels and provide selected updates to the nodes.

The challenge is, that every CaaSP system already run a salt-minion against
its own master.

There are two options:

### 1. run a second minion which is dedicated for SUSE Manager

By implementing and Instantiated Services (salt-minion@.service) we can
easily run a second minion which is talking to SUSE Manager. We can at least
provide the repositories and from SUSE Manager for the cluster.

Examples
--------

* [Autoyast file for a SUSE CaaSP Admin node](attachments/IntegrateCaaSP/caasp-admin-node.xml)
* [Autoyast file for a SUSE CaaSP Worker Node](attachments/IntegrateCaaSP/caasp-worker-node.xml)
* [Autoinstallation Snippet to setup a second minion on CaaSP](attachments/IntegrateCaaSP/CaaSP-second-minion.snippet)
* [Autoinstallation Snippet to configure the CaaSP admin node](attachments/IntegrateCaaSP/CaaSP-admin-cloud-init.snippet)

For the admin node we can configure cloud-init to perform the initial setup. The example snippet support the following valiables:

```
caasp_rootpw=secret
caasp_timezone=Europe/Berlin
caasp_ntpservers=ntp1.example.com,ntp2.example.com,ntp3.example.com
caasp_fqdn=caasp-admin.example.com
caasp_hostname=caasp-admin
caasp_locale=de_DE.UTF-8
```

ToDo
----

Some of the SUSE Manager states must be adapted to support the different configuration directory
for salt-minion.

Option: use traditional registration or salt-ssh


### 2. use one master for SUSE Manager and CaaSP.

This is more work and needs more time to evaluate.
We need to share the state and pillar data somehow.

This may replace the admin node and velum.
To do this we would need some help from CaaSP developer who has a lot of background info about
what the admin node is doing in the background.

Some findings during the fist evaluation:

* caasp states should not use a top.sls or we need to teach salt to merge them
* orchestration states uses target '*' which in case of SUSE Manager would target all minions registered at SUSE Manager.
* etcd needs to run on one node
* maybe the ca container need to run - but the CA handling is currently under discussion in the CaaSP Team.
* minion config of the CA container is hardcoded to "localhost"


## Transactional Updates and Read Only Filesystem

This means we have a read-only root filesystem. Only some dedicated directories
have write access. Some uses overlay FS to keep changes when booting a different
snapshot.

Updating a read-only FS happens via the tool "transactional-update". It creates
a snapshot, turn it read-write, install the updates in this snapshot, configure
the bootloader to boot this snapshot on the next reboot and turn it read-only again.
To make the changes active, the admin needs to rebot. When this happen is up to the admin.

This limit "management" via SUSE Manager.

* We can provide the repositories.
* We can change salt to call "transactional-update" tool instead of zypper.
* Some configfiles can be managed when they are placed in an area where we can write.



# Drawbacks
[drawbacks]: #drawbacks

CaaSP Management Option 1 is not the best solution. It is only the one which is the easiest
solution to provide SUSE Manager managed repositories to CaaSP.

Better would be Option 2 which more or less replace the Standalone Admin node with
the Standard Datacenter Management Tool.


# Alternatives
[alternatives]: #alternatives

What other designs have been considered? What is the impact of not doing this?

# Unresolved questions
[unresolved]: #unresolved-questions
