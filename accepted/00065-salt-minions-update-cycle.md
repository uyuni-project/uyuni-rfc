- Feature Name: Salt Minion Update
- Start Date: 2019-11-26

# Summary
[summary]: #summary

Uyuni-controlled Salt Minion update mechanism on all platforms and architectures.

# Motivation
[motivation]: #motivation

Due to Salt's nature, it comes with the modules that are persistently installed on the Salt Minions. Given Salt Minion outdated due to variety of reasons (e.g. being a part of OS's maintenance schedule), this leads to inconsistent infrastructure, where the same modules might have different capabilitles.

This RFC has the following goals to resolve:

- Ensure Python environment with a specific version on all clients.
- Ensure identical version of Salt Minions with the Salt Master.
- Independence from client OS's maintenance cycle.

# Detailed design
[design]: #detailed-design

## Approach

**Volatile Salt Minion**

SaltSSH as of today is unable to work across different architectures that differs from the one where Salt Master is running. This limitation is due to the binary modules are included into pre-generated `thin.tgz` and they are coming from the hardware architecture on which they are installed at Salt Master side. That said, running SaltSSH from the x86 platform against e.g IBM System/390 or ARM will just fail to load binary included `.so` modules.

However, SaltSSH is treating Salt Minion as volatile entity, and such approach can be successfully reused in a standard deployments, where Salt Minion can be fully installed into a separate optional environment e.g. in `/opt/salt<version>` with its own Python environment and also be directly removed with `rm -rf /opt/salt<version>` without breaking anything on the managed OS. Essentially, this makes Salt Minion state-less and can be removed and reinstalled at any time, regardless what kind of communication channel is used (ZMQ or SSH).

If Salt Minion could be no longer needed to be packaged from the client OS perspective and is deployed from the Salt Master host, then the support routine is also shifting only to a Salt Master host.

**Independent Maintenance Cycle**

In order to efficiently update Salt Minion on any version of operating system, the update cycle of a Salt Minion needs to be independent from the maintenance update of the very operating system itself. This can be achieved by keeping Salt Minion volatile and nearly state-less.

Rationale: Allow components update as soon as it is needed for the software component, without waiting for the general maintenance update.

**Isolation**

Since Salt Minion is a part of configuration management system, it is also a good to have it "static", in terms of zero dependencies from the operating system it currently runs.

Rationale: Allow running latest modern software on much older environments without any impact to the managed operating system.

**In-place Bootstrapping**

Each Salt Minion is not packaged anymore in OS-specific package manager (RPM, Deb etc), but is bootstrapped via standard Python mechanism (Package Installer for Python, PIP).

Rationale: Track all the patches in only one place. As the code is isolated (see above), avoid unnecessary extra-packaging for isolated version of the Salt Minion.

## Deployment Cycle

### Overview

Deployment of the Salt Minion consists of two parts:

1. Setting up statically compiled Python environment. This include 3rd party modules and dependencies, such as MCrypto, SSL etc.
2. Deploy Salt Minion and all its included modules.

The principle is to run own minimal [PyPi](https://pypi.org/project/pypiserver/) local server on Uyuni cluster. In order to install a Salt Minion, a managed system should use PIP againstlocal PyPi server, as shown on Figure 1 below:

![Layout](images/00065-layout.png)

_Figure 1_

Process update or installation flow as follows:
1. One RPM general package of Salt Minion **(1)** is provided for all possible platforms and architectures and is installed on PyPi server. However, Salt Minion is not _installed_ per se in the sense as for end-user, but as a PyPi package into the PyPi repository location. This way patches are still tracked at RPM `.spec` level.
2. General statically compiled Python vanilla environment is provided as an RPM package from Uyuni repository and is allowed to be installed **(2)** on a Managed System, e.g. in `/opt/python3.8` or whatever version is needed. That way it is also allowed to have many Python versions as well as its modifications, if ever needed.
3. Once virtual environment (not shown on the _Figure 1_) is created for the the separate Python interpreter, PIP is bootstrapping the entire Salt Minion against Uyuni-served PyPi server with all the required Salt Minion dependencies.

This should result into running fully featured Salt Minion of latest version in an isolated virtual environment on an OS-isolated Python interpreter, which is aligned with the current Uyuni Server. Once Uyuni Server is updated to another version, so is the PyPi container image is also upgraded. Thus, Uyuni Server should issue mass-upgrade to all Salt Minions that should PIP-upgrade themselves, bumping up to the latest available version.

Consequently, this mechanism will allow to keep always aligned Salt Minions across the entire infrastructure consistent and identical.

## Fail-proof Updates

Having running Salt Minion inside a virtual environment, allows to deliver fail-proof updates. The basic mechanism is to clone Python Virtual Environment from the current active Salt Minion and update the Salt Minion there.

If update is finished successfully, Salt Minion is restarted into a new environment, which is set as default. Previos environment is kept, and is purged over one update cycle (one after current update). This way administrator always has an ability to roll-back to the previous known working version.

If update failed, Salt Minion keeps running without changes, report is created and new Virtual Environment is purged immeditately.

As shown on the _Figure 2_, the difference between RPM-based updates is that the software components are overwritten, instead of installed nearby. Therefore once Salt Minion is broken on upgrade for whatever reasons, it might be no longer possible to revert this with the faulty Salt Minion itself.

![Layout](images/00065-ve.png)

_Figure 2_

According to the _Figure 2_, if updated Salt Minion is successfully updated and is trusted enough, then the statuses of each virtual environment are shifted, and "Previous Salt Minion" is purged.

Naturally, the same way it is possible to update the entire Python version on production and roll-back to the previous Python version, in case things go wrong.

## Installation/Update Process

This RFC is separating Python installation/update process from the Salt Minion installation/update processes, both on all architectures and OS versions. Consequently, mechanisms are different.

### Step 1: Python Interpreter

Python interpreter in "vanilla version" should be packaged as usual in RPM, per OS. However, compiled statically for that specific OS version and architecture. This alone allows update Python interpreter independently from the currently running Salt Minion. The diffrence is that the Python interpreter is installed in an optional namespace, e.g. `/opt/python<VERSION>/bin/python<VERSION>` path. The very RPM package, however, is served by Uyuni Server repository, instead of default channels.

This RPM package remains being vendor supported.

### Step 2: Virtual Environment

Once Python interpreter is delivered and installed on a managed system, Virtual Environment is created. It should contain Package Installer for Python (PIP) and Salt Minion required packages list.

Salt Minion is no longer installed from the RPM package, but bootstrapped by PIP environment. However, the distributed package version that is on the PyPi server remains vendor supported.

> Idea for audit: checksums of all the files in the Virtual Environment can be calculated and stored in the database that might run on PyPi container. This way it is possible to detect if the environment was tampered.

### Step 3: Running Salt Minion

Ready to go Salt Minion on the Virtual Environment is linked for the `systemd` as default and is started.

### Next Steps: Updating Salt Minion

In order to update Salt Minion to the latest Uyuni-supported version, Step 2 is repeated and new Virtual Environment is created nearby current one. Virtual Environment manager component should relink default environments shifting current to "previous" and "new" to "current", and then restart Salt Minion.

### Restoring Failed Minion Update

**Problem**
New Salt Minion is completely broken and doesn't start anymore. This renders managed system no longer be able to be managed via Salt.

**Rationale**
Automatically restore and reconnect previous Salt Minion, once new Salt Minion upgrade went wrong and new Salt Minion is either fails to start at all or fails to communicate/respond or has any other major fatal issues.

**Solution**
One of the ideas is to switch Minions with a simple watchdog function, which has only one purpose: to watch status of some cookie file for a specific amount of time and restore previous minion, in case timeout is over. This function could be a part of the mechanism that takes care of managing Python Virtual Environments.

E.g. if new Salt Minion restarted successfully and reported back, Salt Master can issue another command to "finalise upgrade" and so Salt Minion updates cookie file. In this case watchdog function will get a signal that the previous Virtual Environment restoration is no longer needed. Otherwise, previous Salt Minion is restored back.


# Drawbacks
[drawbacks]: #drawbacks

- 3rd party dependencies should go through the review process, before they appear in the PyPi repository, available for the installation. Possible solution to seamlessly un-RPM them from the packages. Conversion from RPM sources back to the PyPi format?
- Essentially, PyPi server will take a control (and a responsibility) for *all the dependencies* for Salt Minion. It no longer will be valid to rely on  whatever package comes with the current OS. But it is also **a positive side**: it allows to have newest possible library, that is no longer available on the current system in that particular version.

# Unresolved questions
[unresolved]: #unresolved-questions

N/A
