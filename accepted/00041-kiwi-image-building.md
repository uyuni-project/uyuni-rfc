- Feature Name: OS image building with Kiwi
- Start Date: 2018-04-03
- RFC PR: https://github.com/SUSE/susemanager-rfc/pull/68

# Summary
[summary]: #summary

SUSE Manager lacks the support for building OS images.
This RFC proposes a way to integrate OS images built with Kiwi into SUSE Manager.

# Motivation
[motivation]: #motivation

[*Kiwi*](https://suse.github.io/kiwi/) is a tool to create disk images, virtual machines, and appliances: from a directory containing a description of the ingredients of the image the user can create to the final product that can be either an image for QEMU, Xen, VMware, Docker or even physical machines.

At the current state of writing, end users running SUSE Manager have to manually:

* provision a build host by installing Kiwi
* trigger Kiwi from the command line to build an OS image

Given the recent [removal of SUSE Studio for image deployment](https://github.com/SUSE/spacewalk/pull/3901), we are also in the need of providing an alternative: we want to offer an easy way for the end user to build and manage OS images with Kiwi that use SUSE Manager channels directly from SUSE Manager.

# Detailed design
[design]: #detailed-design

All the following design will be part of the first iteration.

x86_64 will be the only architecture supported.
All the following design is referred to Kiwi version 7 (see "Future developments" for the newer versions of Kiwi).

Kiwi can also build container images. Given that:

* we already offer the possibility to build container images
* end users are more comfortable with Dockerfiles rather than Kiwi configuration file (`config.xml`) to build container images

We should educate end users to use Kiwi to build OS images only, but not restrict us from providing a design that would later allow Kiwi based container building.

All the database tables related to image building are generic, including the action type tables, and thus can be re-used for OS images as well (possibly with minor additions).
The only exception is `suseDockerfileProfile`, which stores container-specific additional data for image profiles.
This table must be copied for OS images (e.g. `suseKiwiProfile`).

We are going to illustrate every feature that must be implemented in SUSE Manager:

* provision Kiwi build host
* define OS image profile
* build OS images
* store OS images in a Kiwi store
* list OS images in Kiwi store
* audit OS images against a specified CVE audit

## Provision Kiwi build host

Kiwi is a standalone application that must be installed on the build host. Other packages that should be installed are listed in the [`kiwi-image-server`](https://gitlab.suse.de/SLEPOS/SUMA_Retail/blob/eb80f512963fe28c0eb979c6d04769ef61d05eb2/image-server-sls/image-server/kiwi-image-server.sls) Salt file.

Relevant part:
```
mgr_install_kiwi:
pkg.installed:
  - pkgs:
    - kiwi
{%- if pillar.get('use_build') %}
    - build
{%- endif %}
[...]

mgr_kiwi_build_tools:
pkg.installed:
  - pkgs:
    - kiwi-desc-saltboot
    - image-server-tools
[...]
```

Let's now make an example. Let's consider SUSE Linux Enterprise SP3:
  * `kiwi` package is in `SLE-12-SP3-x86_64-Update` channel
  * `kiwi-desc-saltboot` is in `SUSE-Manager-Head-x86_64-Pool` channel. SMR team will adjust package definitions to deliver this package in `SLE-Manager-Tools12-x86_64-Update`.
  * `image-server-tools` is in `SUSE-Manager-Head-x86_64-Pool` channel. SMR team will adjust package definitions to deliver this package in `SLE-Manager-Tools12-x86_64-Update`
  * (not required in the first iteration): `build` package is in `SLE-SDK`. `build` (OBS build script) is a build tool used in OBS Express to prepare and handle kiwi in a way compatible with OBS. At the time of writing, `build` suffers from the following bugs that prevent its use:
    * [Fix sysdeps parsing in case of kiwi image](https://github.com/openSUSE/obs-build/pull/421)
    * `build` in chroot does not install `zypper` in chroot (no package dependency resolution)
    * `build` in chroot does not provide network access (the repositories must be copied on the build host).
  NOTE: we need a written statement (email) stating that `build` is fully supported and maintained, including L3 support.

In the `System > Details > Properties`, under `Add-On System Types:`, there will be an additional checkbox labeled "Kiwi Build Host".
When the user marks a system as a Kiwi build host, the states that come from the Salt file described above are appended to the system's highstate.
As already happens with container image building, a notification for the end user will be shown:

```
Kiwi Build Host type has been applied.
Note: This action will not result in state application. To apply the state, either use the states page or run `state.highstate` from the command line.
```

The user has then to manually apply the highstate to install the required packages on the system.

[`kiwi-image-server.sls`](https://gitlab.suse.de/SLEPOS/SUMA_Retail/blob/eb80f512963fe28c0eb979c6d04769ef61d05eb2/image-server-sls/image-server/kiwi-image-server.sls) is provided by SMR team and will be included in the `image-server-sls` package. This file will be installed in `/usr/share/susemanager/salt/services` on the SUSE Manager server.

## Define OS image profile

Under `Images > Profiles > Create`, the end user will have to fill out the following details:

  * **Label**: name of this profile, mnemonic name for the user. Not used in Kiwi build phase
  * **Image Type**: in addition to Dockerfile, we should add "OS image"
  * **Target Image Store**: non-editable but pre-filled out with "File store on SUSE Manager". It can also show the directory of the Kiwi store and the URI to reach it.
  * **URI**: the URI of the repository that contains Kiwi configuration file(s). NOTE: [Existing fields for container build are in the progress of being renamed to `URI` (update: user interface, database, manuals)](https://github.com/SUSE/spacewalk/issues/3828). We can also link an example Git repository that contains a base Kiwi configuration file in order to help users.
  * **Activation Key**: _must_ be specified: All packages installed during building will be fetched from the repositories associated with the specified Activation Key.
  * **Custom info values**: not used for Kiwi.
    NOTE: This feature is implemented exclusively inside SUSE Manager. It is not related at all to containers either. Basically, custom data values are a way to tag images arbitrarily inside SUSE Manager requested by customers. Furthermore, this feature should work with Kiwi as well out-of-the-box.

The details specified will be saved in the database.

Under `Images > Profiles` we will show all profiles currently available, consisting of:

* **Label**: as filled out by the end user in the previous step
* **Build type**: "OS image" for Kiwi build profiles, "Dockerfile" as already happens for containers

## Build OS image

Under `Images > Build`, the end user will have to fill out:

* **Version**: Disabled, as Kiwi build will append the version of the build to the generated data after inspection.
* **Image profile**: select any of the Image profiles defined
* **Build host**: based on the previous selection, we allow to select (via database query) all Kiwi enabled build host if an OS image profile is selected
* **Earliest**: SUSE Manager internal, selected by the user
* **Add to**: SUSE Manager internal, selected by the user

When the end user selects the Build action, two Salt executions must be triggered

### Image building

A Salt call is executed to apply the state named [`images/kiwi-image-build`](https://gitlab.suse.de/SLEPOS/SUMA_Retail/blob/eb80f512963fe28c0eb979c6d04769ef61d05eb2/image-server-sls/image-server/kiwi-image-build.sls) state that builds the image:

```
salt buildhost state.apply images/kiwi-image-build <pillar>
```

Using a pillar we supply the following parameters:

* `source`: the path to Kiwi configuration file(s) contained in a repository accessible by the Kiwi build host. Configuration files can also contain script files (e.g. `config.sh`) and, optionally, multiple other files which are copied to the root of the generated image.

  NOTE: SMR team will modify `images/kiwi-image-build` to:
    * accept `source` as:
      * Git repository pointing to the repository containing the Kiwi configuration file
      * HTTP/HTTPS URL pointing to the Kiwi configuration files compressed in a tarball file
    * add a parameter that expresses the target directory in which to save the built image
    * add a parameter to choose the transport mechanism to save the built image to the SUSE Manager server, depending on Kiwi store transport mechanism is chosen
* `build_id`: unique build id generated by SUSE Manager. It can either be a sequence number, UUID or `action_id`; it just needs to be unique for every build. This id will be used as a temporary directory name to prepare and build the OS image on the Kiwi build host.
* `repos`: a list of repositories to be used when installing packages with Kiwi.
  Kiwi needs to trust SUSE Manager certificate before installing packages coming from it.
  SUSE Manager serves its certificate in two non-HTTPS terminated ways:

    * plain certificate: `http://<SUSE Manager server>/pub/RHN-ORG-TRUSTED-SSL-CERT`
    * RPM package of the certificate: `http://<SUSE Manager server>/pub/rhn-org-trusted-ssl-cert-1.0-1.noarch.rpm`

  During the build phase, Kiwi will call zypper one time to install all the RPMs specified in the configuration file. Kiwi cannot guarantee the order in which specified packages are installed, and it might happen that SUSE Manager's certificate gets installed _before_ `ca-certificates`, leading to an error (`rhn-org-trusted-ssl-cert-1.0-1.noarch.rpm` calls `update-ca-certificates` which is shipped with `ca-certificates`).

  To fix this problem we have two alternatives:
    * generate additional packages containing SUSE Manager's CA certificate that depends on `ca-certificates` and put them in the `/pub` directory. OS: SUSE Linux Enterprise 12 GA, SP1, SP2, and SP3. (NOTE: this is done only once at install time of SUSE Manager).
    After that, create a custom channel and associate it with the parent channel which is tied to the activation key and push just one package of the packages created above to that channel.
    Drawback: lots of channel creations and the custom channel cannot be deleted and will be shown for every client - an end user could wrongly associate that custom channel to a system.
    If Kiwi could install those packages without a repository we can follow this solution.
    * Kiwi building has two phases: unpacking and packages installing. We need to patch Kiwi to inject `http://<SUSE Manager certificate>/pub/RHN-ORG-TRUSTED-SSL-CERT` in `/etc/pki/trust/anchors` in the root file-system and then install all certificates (including `ca-certificates`).

Upon successful building, the OS image is copied back to Kiwi store (SUSE Manager server).

The resulting image already will be provided in a bundled format which includes all needed component (initrd, kernel, partition image). It will be stored as one file.

Let's presume that the Kiwi store directory is:
```
/srv/www/virtual-images
```

SUSE Manager should supply an additional Apache host configuration file to serve this directory and adjust directory and file permissions (if needed). This would give the flexibility to serve the Kiwi store from a different server in the future.

The Kiwi build host has some alternatives to push the images back to the SUSE Manager Kiwi store:

* (already implemented): Use Salt `cp.push_dir` into the SUSE Manager directory `/var/cache/salt/master/minions/minion-id/files`.
This approach also requires:

  * Additional configuration of the Salt master: `file_recv_max_size: 10000` in `/etc/salt/master`
  * Additional configuration of permissions: Salt user *cannot* write in `/srv/www/virtual-images`
  * Additional development on SMR team: a reactor job that moves the images from `/var/cache/salt/master/minions/minion-id/files` to the Kiwi store

* (to be implemented by SMR team) rsync over SSH: as soon as SUSE Manager provision the Kiwi build hosts, SUSE Manager copies its SSH public key (or re-uses the one created in salt-ssh). When the build has finished, SUSE Manager issues an `scp`-copy command to copy the image from Kiwi build host to the SUSE Manager server.
This approach requires:

  * Additional configuration: SUSE Manager must create and copy its public key to the Kiwi build host (upon provisioning of it)

* HTTP endpoint implemented by SUSE Manager to upload a file to the Kiwi store.
This approach requires:

  * Additional development on SUSE Manager team: a servlet to upload a file to the Kiwi store.
  Possibly target of DDoS causing filesystem full
  * Additional configuration: Tomcat configuration must be adapted to accept upload files bigger than 50 MB (current default limit in Tomcat 8.0)
  * Additional configuration of permissions: Tomcat user *cannot* write in `/srv/www/virtual-images`

* Implement an FTP server on the SUSE Manager server.
This approach requires:

  * Additional development on SUSE Manager team: configure and install an FTP server package

Once the built image has been copied back to the SUSE Manager server, the image should be readable by all clients that want to retrieve and deploy it. Clients can retrieve the OS images by accessing `https://<SUSE Manager server>/virtual-images/` without any authentication.

[`images/kiwi-image-build.sls`](https://gitlab.suse.de/SLEPOS/SUMA_Retail/blob/eb80f512963fe28c0eb979c6d04769ef61d05eb2/image-server-sls/image-server/kiwi-image-build.sls) is provided by SMR team and will be included in the `image-server-sls` package. Those files will be installed in `/usr/share/susemanager/salt/images` on the SUSE Manager server.

### Image inspection
After SUSE Manager receives the return value of the execution of the previous Salt state, SUSE Manager must trigger the Salt state contained in [`images/kiwi-image-inspect.sls`](https://gitlab.suse.de/SLEPOS/SUMA_Retail/blob/eb80f512963fe28c0eb979c6d04769ef61d05eb2/image-server-sls/image-server/kiwi-image-inspect.sls):

```
salt buildhost state.apply images/kiwi-image-inspect <pillar>
```

A parameter should be passed using a pillar:

* `build_id`: the parameter passed in the previous invocation of `images/kiwi-image-build`.

The Kiwi build host will:

* delete the built image (and intermediate data)
* return inspect result to the SUSE Manager server. The inspect result contains information on the built image (e.g. packages) that must be saved into the database. [An example of the result of the inspection Salt state](https://gitlab.suse.de/SLEPOS/SUMA_Retail/blob/e46d39433055f7c009848625e726688a6a0b1bca/doc/image-server-sls.md#kiwi-image-inspectsls).

SUSE Manager server will then:

* parse the result and put into a custom pillar using the same logic described in [`kiwi_image_register.py`](https://gitlab.suse.de/SLEPOS/SUMA_Retail/blob/e46d39433055f7c009848625e726688a6a0b1bca/image-server-sls/image-server/kiwi_image_register.py#L22-76).
This must be done in the same way [as already happens for container images](https://github.com/SUSE/spacewalk/blob/Manager/java/code/src/com/suse/manager/utils/SaltUtils.java#L1014-L1086).
[An example of a resulting pillar](https://gitlab.suse.de/SLEPOS/SUMA_Retail/blob/master/saltboot-formula/metadata/images.pillar.example) is provided.

This pillar is needed by SUSE Manager for Retail in the deployment phase in order to fetch all the details regarding the desired image.

[`images/kiwi-image-inspect.sls`](https://gitlab.suse.de/SLEPOS/SUMA_Retail/blob/eb80f512963fe28c0eb979c6d04769ef61d05eb2/image-server-sls/image-server/kiwi-image-inspect.sls) is provided by SMR team and will be included in the `image-server-sls` package. Those files will be installed in `/usr/share/susemanager/salt/images` on the SUSE Manager server.

### Kiwi store listing

The Kiwi store is the directory where all built images are filed. In the user interface, there should be the possibility to:

* list OS images built by Kiwi (same that happens now in `Images > Images` for containers)

### Audit OS images against a particular CVE

In `Audit > CVE Audit`, end users can test a OS image against a particular CVE.
The packages contained in the image are compared to Activation Key (specified in the profile) channels to find the specified CVE and produce a report.

## Future developments

All the following developments will _not_ be part of the first iteration. They will be targeted in future iterations

### Kiwi store improvement and customization

In a second iteration we will let end users:

* customize the OS image store directory

In addition, the current user interface will have tabs to filter and display the various type of images associated with SUSE Manager: KVM, container images, Saltboot/PXE.

### Protecting the Kiwi store

There are two main drawbacks of having images publicly accessible:

  * Images could include partially sensitive data if the customer chooses to build images that are mostly complete (including the application and configuration)
  * PXE boot is not very secure as there is no authentication to download images: it could be very easy to "impersonate" a legit system if we make extremely easy for anyone to download and inspect the images.

For these reasons we should, on a second iteration, protect those images with authentication, but let the PXE server access them without any authentication.

### Image customization with Salt

We decided not to extend Kiwi XML configuration file by injecting Salt pillars (we want to be compatible with plain Kiwi). Instead, Kiwi allows running shell scripts in the final stage.
We could extend Kiwi to call Salt in the final stage of image building and use real Salt states/formulas at that stage.

### SUSE Linux Enterprise 15 support

Kiwi v7 (Perl based) does not support generating SUSE Linux Enterprise 15 images (netboot package is not available).
Kiwi v8 (or newer) is Python-based (easily extendable) and has support for SUSE Linux Enterprise 15 images, but SUSE Manager for Retail team encountered a bug with URL repository parsing when using it.
To enable SUSE Linux Enterprise 15 image building we either:

* Use OBS build whenever its blocking bugs get fixed for SUSE Manager for Retail team
* Use Kiwi v8 (or newer) whenever its blocking bugs get fixed for SUSE Manager for Retail team

SMR team suggested keeping using Kiwi v7 for SUSE Linux Enterprise 12 based builds.

# Drawbacks
[drawbacks]: #drawbacks

# Alternatives
[alternatives]: #alternatives

* We will have two ways of building container images:

  * (already existing) with Dockerfiles as build profile
  * with Kiwi configuration file as build profile

  For now, container building will be with Dockerfiles only. In the future, we could offer Kiwi configuration files to build containers as well.

# Unresolved questions
[unresolved]: #unresolved-questions

* Kiwi repositories CA certificates
