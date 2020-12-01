- Feature Name: Retail info storage
- Start Date: 2020-12-01
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

After deploying Retail (saltboot) client, also known as terminal, PXE entry for this client is generated on Branch server. These entries are not backed by information available on SUSE Manager/Uyuni and are difficult to recreate. This RFC is addressing this concern.

# Motivation
[motivation]: #motivation

When terminal is booting up, it receives some important information from branch server using kernel command line. In case of first boot, when there is no custom PXE entry for the terminal, these are just information about branch and other custom values. However in case of second and next boot, terminal also receive information about where it should look for salt configuration and also root partition.
If these information are missing, terminal will consider the boot as first boot and will generate new minion id and salt keys and register as a new client to the server.


This is sometimes wanted behaviour, for example when terminal is physically moved from one branch to other branch.
But this also complicates migration of Uyuni/SUSE Manager to newer versions by installing new branch server as there are more files to backup and restore. If there is some unexpected hardware failure on branch server side, it is difficult to recreate these PXE entries for registered terminals and users are facing a task to reregister deployed terminals.


To be able to recreate PXE entries, it is needed to store some additional details about terminals, make them available for the branch server minion and have a state which will recreate them. Idea is that after replacing branch server for any reason, user is able to apply a state and recreate the pxe entries for all connected terminals.

# Detailed design
[design]: #detailed-design


## Workflow description

When terminal is booted up, it sends an event `suse/manager/pxe_update` together with following data:

```
salt_device: $dev_by_id_path
root: $dev_by_id_path
boot_image: $boot_image_name
terminal_kernel_parameters: $hwtype_based_parameters
```

These data are then together with data from branch data used to create pxe and grub entries like:

```
LABEL netboot
        kernel POS_Image_JeOS7-7.0.0/POS_Image_JeOS7.x86_64-7.0.0-5.3.18-24.37-default.kernel
        append initrd=POS_Image_JeOS7-7.0.0/POS_Image_JeOS7.x86_64-7.0.0.initrd.xz  panic=60 ramdisk_size=710000 ramdisk_blocksize=4096 vga=0x317 splash=silent  USE_FQDN_MINION_ID=1 MINION_ID_PREFIX=branch1 root=/dev/disk/by-path/pci-0000:04:00.0-part3 salt_device=/dev/disk/by-path/pci-0000:04:00.0-part3
```

The data send in the `pxe_update` event are not stored anywhere on the Uyuni/SUSE Manager, upon receiving the event reactor applies `pxe/terminal_entry` state on the branch server which will create the pxe entries.


From this example it is clear that the data send in the `pxe_update` event should be stored somewhere on the Uyuni/SUSE Manager and be accessible to branch servers.


## Storage of the data

In this RFC we propose to create new database table `suseRetailMinionInfo` which will reference `suseMinionInfo`. This table will contain at least entries for `root_device`, `salt_device`, `boot_image` and `terminal_kernel_parameters`.

```
CREATE TABLE suseRetailMinionInfo
(
    server_id           NUMERIC NOT NULL
                            CONSTRAINT suse_retail_minion_info_sid_fk
                                REFERENCES suseMinionInfo (server_id)
                                ON DELETE CASCADE,
    branch_id           NUMERIC
                            CONSTRAINT suse_retail_branch_info_sid_fk
                                REFERENCES suseMinionInfo (server_id)
                                ON DELETE SET NULL,
    mac_address         VARCHAR(17),
    root_device         VARCHAR(36),
    salt_device         VARCHAR(36),
    boot_image          VARCHAR(256),
    kernel_parameters   VARCHAR(512)
)
```

To prevent storing long `root_device` and `salt_device` we propose to change saltboot use from dev-by-path to dev-by-uuid and sending only UUIDs of used devices.


`boot_image` points to part of built retail PXE OS image. This part is currently not registered in database itself and information about it are only available in generated pillar data. Information from pillar addressed by `boot_image` is then used in generated pxe entry to correctly set what initrd and kernel should be served to the terminal during pxe boot.

`kernel_parameters` are taken from HWTYPE group given terminal is member of. It is sent in event, because branch server, where pxe entries are to be generated, generally does not have access to pillars from saltboot formula of HWTYPE group.

Added `branch_id` column references branch server to which this terminal belongs to. Column `mac_address` specify MAC address of the terminal. Similar column is also present in `rhnServerNetInterface` table, however that information is populated only after hardware refresh is scheduled, which is done only after successful deployment. Whereas pxe entries needs to be available before full deployment because of cases when kernel version of inird is different to kernel version in image and terminal requires reboot to correct kernel version.

Another option is that event handler creates the correct entry in `rhnServerNetInterface` table.

## Storing data in database

As data are provided within salt event, implementing new event handler `SaltbootPxeUpdateEvent` with accompanying `SaltbootPxeUpdateMessageAction` should be sufficient.

Event handler should also schedule generation of new PXE entry.

## Generating PXE entries

In current implementation, consumer of the `pxe_update` event data is `pxe/terminal_entry` state which is part of PXE formula.

In case of keeping the final action in salt space, there is a need to provide pillar data to the state:

  * by supplying directly to state when scheduling pxe generating action.
  * by exposing database data to salt pillar system.

Exposing database data may have some benefit like enabling user to manually apply `pxe/terminal_entry` or similar state to (re)generate pxe entries. This option can save resources by making UI/XML-RPC API changes non-essential.


Database can be exposed to pillar system by external pillar mechanism connecting to the database using postgresql external pillar:

```
postgres:
  db: susemanager
  host: localhost
  pass: spacewalk
  port: 5432
  user: spacewalk

ext_pillar:
  - postgres:
      'retail_terminals':
         query: "SELECT S.name, root_device, salt_device, boot_image, kernel_parameters,mac_address FROM
                (SELECT * FROM suseRetailMinionInfo as RMI, rhnServer as S WHERE RMI.branch_id = S.id AND S.name LIKE %s) AS I JOIN rhnServer AS S ON I.server_id = S.id"
         as_list: False
         depth: 1
```

or by writing pillar files for given branch server.

Keeping data hidden in database prevents manual state application by user, but does not clutter pillar space with rarely used data. To allow user to manually trigger pxe entries regeneration would need development of UI or XMLRPC API endpoint user can call.

Using these data `pxe/terminal_entry` state would need to be adapted to look for pillar data in correct places and also to support generating single pxe entry or all pxe entries depending on the values passed to the state.

## Updating PXE entries

Moving terminal between branches happens. This means event handler needs to be aware of this possibility and adapt `branch_id` field as needed.
  
Removal of the branch server system profile would set `branch_id` to `null` and terminal will need to be rebooted under new branch server to be this entry updated.

# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?

  * obscure corner cases
  
    Currently unknown
  
  * will it impact performance?
  
    Multiple terminals booting at the same time - current state is handled solely by salt, proposed solution adds communication with database - increasing latency and some load on database
  
  * what other parts of the product will be affected?
  
    There should be no affect to other parts of product
  
  * will the solution be hard to maintain in the future?
  
    As is the case even now, the code is split across different projects and github repositories. Saltboot code in [uyuni-retail/saltboot-formula](https://github.com/uyuni-project/retail/tree/master/saltboot-formula), `pxe/terminal_entry` state in [salt-formulas/pxe-formula](https://github.com/SUSE/salt-formulas/tree/master/pxe-formula) next adding java event handler adds third repository. However code itself is not complex and this code split can be mitigated either by moving parts closer together (like [integrating saltboot to uyuni](https://github.com/SUSE/spacewalk/issues/10777)) or good code commenting.
  

# Alternatives
[alternatives]: #alternatives

- Automatic detection of partition where salt configuration is stored

  Draft PR [is here](https://github.com/uyuni-project/retail/pull/71). This removes the need to reregister terminal in case of lost PXE entry. However this does not preserve terminal-specific kernel command line options and always boot default initrd and kernel.

- TPM as storage for salt configuration

  Trusted Platform Module is required to be available on every hardware certified to run MS Windows 10, essentially every new hardware. It can be used as a secure storage for salt keys and minion id instead of storing it on hard drive. This would solve the same problem as automatic detection of salt configuration with the same drawbacks. This would also need some more time for research and packaging ensuring tpm2-tss is available in saltboot initrd.

- Storage of pillar data in pillar files instead of database

  This would allow to reuse of current external pillar mechanism, but suffer from the same issues like existing implementation - maintaining consistency of data and others. (See [overall issue](https://github.com/SUSE/spacewalk/issues/10679))


# Unresolved questions
[unresolved]: #unresolved-questions

- What are the unknowns?
- What can happen if Murphy's law holds true?
