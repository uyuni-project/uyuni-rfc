- Feature Name: Saltboot overhaul to support containerized proxy server
- Start Date: 2022-03-09

# Summary
[summary]: #summary

Containerized proxy server no longer contains salt minion service. Saltboot (retail) workflow needs to be overhaul to drop salt minion dependency.

# Motivation
[motivation]: #motivation

- Why are we doing this?
- What use cases does it support?
- What is the expected outcome?

Saltboot workflow heavily relies on salt ecosystem. Actual deployment is not at risk as containerized proxy server contains salt broker service. However all support functionality ( image synchronization, PXE entries management, branch server configuration ) relies on salt minion service available on a branch server and this service is no longer available on the containerized proxy server.

This RFC offers a saltboot overhaul to drop salt requirement on proxy server and in process also simplify overall saltboot configuration and operations.

# Detailed design
[design]: #detailed-design

To better understand the problem at hand lets start with what we have now, what we require and what we will have with containerized proxy.

### What we have - services available on Branch server

#### Networking

- `Branch networking formula` helps with firewall configuration, configures LAN for terminals, ensures forwarding, etc.
- `DHCP and DNS formulas` configures its respective services:
  - minimum mandatory DHCP config is to provide PXE clients next-server and filename options pointing to pxe server
  - dns is nowadays optional if other configurations are done on SUMA server (`MASTER` kernel option passed by pxe and `saltboot_download_server` pillar)
  - minimum mandatory DNS config if no other configuration is done is `salt` CNAME pointing to salt-broker using its FQDN and `ftp` resolvable to proxy where ftp (4.2 and older) or http (4.3 and newer) service is running

#### PXE files management

- `Branch networking formula` setups common kernel options passed to PXE clients such as branch identification, terminal naming schema.
- `PXE formula` ensures common pxe files are installed and present (syslinux, shim, grub2) so both PXE and UEFI HTTP works
- `PXE formula` manages individual terminal entries as they are onboarded (provides salt state which responds to `suse/manager/pxe_update` salt event send by saltboot)
- `Image-sync formula` manages kernel and initrd files and links for default and per image initrds and kernels
- `tftpd-formula` ensures working tftp server. Installation of package and default config to use `/srv/saltboot` directory.

#### Filesystem image cache

`Image-sync formula` manages filesystem image files:
- download of files from SUMA server
- extraction and verification of initrd, kernel and filesystem image
- in case of delta images it completes all images to be in usable format
- data about images are taken from image pillars generated after images are built
- delete images no longer available on SUMA server
- notify SUMA server about image synced and deleted

#### Other services

- `vsftp formula` manages ftp service. But for 4.3 and later images made to use http by default so this formula is to be deprecated.


Now compare that available Branch server services to what Saltboot terminal needs for successful deployment.


### What Terminal requires from the Branch proxy

#### TFTP server

With the exception of UEFI HTTP default boot mode is using PXE boot over TFTP. TFTP is old and vastly inefficient protocol over UDP confirming each and every datagram received and under strict timing. This puts quite a CPU load on branch but more importantly is really inefficient when run over WAN instead of LAN. For this reason having tftp server as close as possible to the booting terminal is a must.

#### PXE files

PXE firmware on the Terminal is instructed to get IP address via DHCP and based on `next-server` option connect specified TFTP server and download binary specified in `filename` option. This binary is a syslinux binary which then download pxe configuration file from the tftp server and based on it it downloads specified initrd and kernel.

There are generic pxe configuration files and configuration files for specified system based on system MAC address or other ID.

Generic configuration file is used when there is no specific system configuration and is used in case of first terminal registration. This will load default initrd and kernel, currently initrd and kernel from the first available image is used (but it might change, see https://github.com/uyuni-project/retail/pull/104 ).

Once terminal is registered and image deployed using saltboot it currently sends out event `suse/manager/pxe_update` based on which pxe formula state will generate system specific pxe configuration pointing to the correct initrd and kernel for image used on that particular terminal together with proper `root` entry where stored salt configuration is located. Without this `root` entry saltboot will generate new random terminal name (random suffix) and will do complete registration again.

Thus we need some way to have generic pxe configuration pointing to the default initrd and kernel. And then a way to generate system specific configuration which would then point to correct initrd and kernel used on the terminal. Without this terminal would be subject to kexec on boot and if kexec fails then terminal would not be able to boot. Reboot would without specific configuration end in loop.

#### Salt broker

Saltboot was mentioned as deployment mechanism. Saltboot consists of who parts - saltboot initrd and saltboot states. Saltboot initrd is prepared during image building and is usually provided by tftp server. Saltboot states are on the SUMA server and are applied on the booting terminal when grain `saltboot_initrd` is set to `True`. Obviously for saltboot we need salt connection.

Terminal can connect directly to SUMA server and work, but then because of how SUMA identifies minions connected though proxy, we would lose information about connection path. Thus terminal needs to connect to SUMA server though salt broker. How does terminal know where its salt broker is?

Saltboot tries to resolve `salt` hostname as CNAME. If `salt` CNAME is resolved to something, then saltboot will use that to connect to salt broker. If it will not resolve as CNAME, it will try to use `salt` directly and connect to that but then SUMA will most probably not be able to correctly resolve terminal is connected through proxy. This method requires `salt` to be CNAME resolvable by used DNS. Either DNS locally provided on branch proxy or dns managed by customers. This may prove to be quite an exercise in dns management and not always feasible thus saltboot understands another way to specify salt-broker FQDN.

If saltboot detects `MASTER` keyword on kernel command line then it will use its value as FQDN where to connect to salt broker. This is useful where DNS usage is unfeasible, on the other hand requires a way to manage default and system specific pxe configuration files as that is the place where kernel command line is specified for PXE boot.

#### HTTP server is optional (FTP server for 4.2 and older is required)

Once connection to salt master (through salt broker) is established, saltboot state is applied on the terminal. Saltboot, among other things, downloads and deploy filesystem image to the terminal. 

Because HTTP is good protocol over WAN, HTTP server is not really required and image can be downloaded even from SUMA server. For performance optimization however branch proxy should have local HTTP server.

How does terminal know from where to download the image? Once terminal is registered to the SUMA it gains access to number of pillars, one of them is images pillar. Images pillars are bound to SUMA organization.
Filesystem image is then downloaded from server specified in images pillar. Because of organization specificity of image pillars, URL in image pillar needs to be generic enough. For this reason URL in image pillar are in format `http://ftp/<image filename`. Assumption is that used DNS will be able to resolve `ftp` hostname to the correct branch proxy. For historic reasons hostname used is `ftp` as many customers with existing setups already configured their DNS to resolve `ftp` hostname even though 4.3 and later use HTTP.

This has the same drawback as `salt` CNAME as DNS configuration may be challenging. Therefor there is a pillar available `saltboot_download_server` which overrides server used for image download.
How can we assign specific pillars to the all terminals which are being booted though particular proxy? For this saltboot uses grains targeting.

During terminal registration to SUMA we gather another kernel command line option `MINION_ID_PREFIX`. This is another name to Branch ID specified in branch network formula and this is saltboot matching to what branch this particular terminal belongs to. Value of that option is stored as `minion_id_prefix` grain.

Combining salt grains targeting with `minion_id_prefix` grain salt can be made that `saltboot_download_server` pillar is accessible to all terminals with specific `minion_id_prefix` value (see [deployment documentation](https://documentation.suse.com/suma/4.2/en/suse-manager/retail/retail-deploy-terminals.html#_customize_the_terminal_image_download_process) ).

With all of this, terminal is able to be registered to SUMA, deployed and skip registration next time it is rebooted.

#### Summary

Terminal needs:
- tftp server
- basic pxe files
- pxe management that is proxy specific - we have at least `MINION_ID_PREFIX` to be written to pxe configuration, optionally `MASTER` as many customers use it
- pxe management that is system specific - we need to have custom entry per registered terminal
- salt broker
- http server for performance reasons

### Containerized proxy services

Containerized proxy consists of several container providing http, salt-broker, squid, ssh tunnel and tftp services.
Proxy containers are initialized from single config.yaml file generated on SUSE Manager/Uyuni server.

## Proposed solution
[solution]: #solution


### Saltboot group
[saltboot_group]: #saltboot_group

Since branch server is not salt minion anymore, it cannot be center of configuration any longer. Instead this RFC propose that center of configuration be a so call `saltboot group`.
Saltboot group is a system group with `Saltboot group` formula assigned. In this formula various saltboot related settings are configured:

- group name as saltboot group id (formerly known as `branch prefix` or `branch_id`)
- associated proxy FQDN
- terminal naming scheme (taken from `branch network formula`)
- configurable default image (with or without version) (taken from `Image sync formula`)
- configurable custom kernel parameters (taken from `PXE formula`)

This group is reminiscent of branch group as used in current retail model. Every terminal is assigned to corresponding branch group on bootstrap thus having access to all group pillars. In this RFC I leverage this fact, particularly for obtaining correct proxy FQDN which is then provided in `saltboot:download_server` pillar parsed by `saltboot` state to directly download image from specified proxy.

### Smart TFTP server

Instead of `image-sync formula`, which is responsible to download, extract and verify of kernel, initrd and filesystem image in this RFC together with [RFC about cobbler sync](https://github.com/uyuni-project/uyuni-rfc/pull/44) I propose usage of wrapper around [Facebook's TFTP server](https://github.com/facebook/fbtftp) which will translate TFTP requests to HTTP requests and forward to proxy HTTP server. HTTP server is then configured that such requests are forwarded to Uyuni server through Squid cache. Images, due to revision number nature and including kernel and initrd, are never stale so after first download through WAN subsequent terminal boots will use cached image, thus increasing performance.

### Image building changes

This direct access to initrd and kernel needs changes in how image are built. Currently after image is built, Kiwi is instructed to prepare so called kiwi bundles, one tar ball with all parts together. There is a choice between collecting this tarball as is and extracting it on the Server, or stop Kiwi bundling and collect individual files.
In this RFC I opt for collecting individual files for simple reason not to waste cycles on build host for creating tarball only to be immediately extracted on the Server and increasing load on it. Negative is that current Retail templates do not use image compression by default, so unbundled images are several times bigger then bundled (e.g. for POS_Image_JeOS7 it is around 400MB in bundle and 1,6GB unbundled). This can be remedied by using compression by default in Kiwi templates.

### PXE Management
[pxe_management]: #pxe_management

Deployment workflow needs two kinds of PXE configuration files - `default` for first time, not yet deployed terminals and `01-MAC` for individual terminals already deployed at least once.

`default` configurations are different for each `saltboot group` as this configuration contains `MASTER=<proxyFQDN>` entry to remove the need of custom DNS server and this entry is different for each proxy server.


### Networking

Managing networking on proxy server is out of scope of containers and left on customer. This means that, similarly as we have with Cobbler autoinstallation now, we will ask customers to set their DHCP environment for PXE booting elsewhere. This eliminates `Dhcp formula` requirement and also majority of `Branch Network formula`. `Dhcp formula` can still be maintained as customer can use that for their separate dhcp management.

`salt` CNAME and `ftp` hostnames are replaced by crafting special PXE kernel command (see [PXE Management](#pxe_management) line and salt pillars (see [Saltboot group](#saltboot_group). We will use this to eliminate `Bind formula`.


# Workflow
[workflow]: #workflow

TBD user story


# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?

  * Change how Retail is configured and done


# Alternatives
[alternatives]: #alternatives

- What other designs/options have been considered?

  * Introducing salt-minion container
  * Mandating salt-minion on container host
  * see [github issue](https://github.com/SUSE/spacewalk/issues/17227#issuecomment-1070735019)


# Unresolved questions
[unresolved]: #unresolved-questions

- cache preheating scripts
- ARM devices support (use special defaults files)
