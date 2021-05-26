- Feature Name: Hub Retail Extension
- Start Date: 2020-11-30
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

This RFC describes an extension of retail features for Hub environment.

# Motivation
[motivation]: #motivation

Reasons for use of Hub with Retail environment
----------------------------------------------

- scalability
  - support large environments with the number of terminal exceeding limits of one SUMA server

- disconnected operation
  - Peripheral server must stay fully functional when the Hub connection is down

See [Hub requirements](https://github.com/SUSE/spacewalk/wiki/Hub-requirements) for details.

Possible configurations
-----------------------

1. Standard
```
    Terminal -> Branch Server -> SUMA Server
```
  This is the currently supported configuration.
  It is suitable for one large department store.
  For larger deployments there may be problems with the number of terminals or with network outages.
  The SUMA Server must be reachable in order to perform any change of Terminal configuration.

  Terminal
    - deployed from OS Image during boot (by applying Saltboot state)
    - then works as standard SUMA minion

  Branch Server
    - SUMA Proxy
    - downloads Images from SUMA (over HTTP) and distributes them to Terminals (over HTTP, TFTP, etc.)
    - runs services needed by Terminals (DHCP, TFTP, HTTP, ...). The services are configured via Formulas with Forms.

  SUMA Server
    - standard SUMA operations
    - holds the configuration for Branch server services in Formulas
    - controls boot process of each Terminal by applying Saltboot state
    - triggers update of PXE data on Branch Server


2. Full
```
    Terminal -> Branch Server -> Peripheral Server -> Hub
```
  Adding Hub on top of previous configuration solves the problems with scalability and offline operations.
  It is suitable for for large organization with many department stores. It can look like this:

  - Branch server on each floor
  - Peripheral server in each building
  - Hub in datacenter


3. Combined Peripheral and Branch server
```
    Terminal -> Branch + Peripheral Server Combined -> Hub
```

  Customers with many small shops do need Hub for offline operations but do not need
  separate Branch server and Peripheral Server because the number of connected terminals is low.
  Running Branch + Peripheral Server on one machine could save resources.
  The Proxy part of Branch server is not needed then.


4. Single server
```
    Terminal -> Branch + SUMA Server Combined
```
  Suitable for one small shop.
  This scenario is not a hard requirement but there were such requests for SLEPOS
  so it would be nice to have it too.


Global Retail data
------------------

The following items are typically shared in whole organization, so they should be visible and
manageable via Hub.

  - Images - distributed as large tarballs via http
  - Image metadata - pillars (sls files), list of repos and packages (in DB)
  - [HWTYPE](https://www.uyuni-project.org/uyuni-docs/uyuni/retail/retail-deploy-terminals.html#_create_a_hardware_type_group) configurations

Local data
----------

The following items do not need central management and can stay on Peripheral Server (like in the current implementation).

  - Branch groups -  groups containing Branch Server and connected terminals
  - Branch formulas - describe configuration of Branch services - network, pxe, dhcp, dns
  - Branch PXE data - entries describing how to boot each terminal

# Detailed design
[design]: #detailed-design

Images + Image metadata
-----------------------

Current situation: an image is built on Buildhost, then pushed to the Server's htdocs directory. Then the Server
[creates a DB entry](https://github.com/uyuni-project/uyuni/blob/master/java/code/src/com/suse/manager/utils/SaltUtils.java#L1311)
(including package list) and
[a pillar file](https://github.com/uyuni-project/uyuni/blob/master/java/code/src/com/suse/manager/webui/services/SaltStateGeneratorService.java#L128).
The pillar conains URL of image tarball, checksums and additional deployment details. It is used for image synchronization and deployment. These data are extracted
on the build host at the end of build phase. Some of the data are only available on the build host and, not being contained in the image tarball, can't be extracted later.

The SUMA API related to images is rather docker-centered. For Kiwi images it allows to list images and packages and delete an image.

Use cases currently not covered:

- Move image tarball to external HTTP server
  In current implementation the image tarballs are stored in htdocs directory and distributed
  via SUMA http server.
  Branch Server via [Image Sync Formula](https://github.com/uyuni-project/retail/tree/master/image-sync-formula) downloads the tarball
  from the URL in pillar, unpacks it and prepares the image for PXE service.

  With Hub we can just extend this schema - tarball will be stored in Hub htdocs directory and copied to Peripheral servers via ISS.
  This might not be optimal for certain cases (many small shops with combined Peripheral and Branch server).

  So the alternative is to allow use of independent http servers and proxies (set up in customers infrastructure or in public cloud)
  for distributing the tarballs. The http server structure does not have to strictly follow the Hub - Peripheral Server - Branch Server structure,
  for example the Branch servers can download tarballs directly from datacenter or cloud.

- Copy image metadata from one SUMA Server to another
  Most common way of distributing image metadata is from Hub to Peripheral servers - this should be handled by
  [ISS](https://github.com/uyuni-project/uyuni-rfc/blob/master/accepted/00063-hub-iss.md)

  Another use case, not covered by the above, is this:
  - Customer has one SUMA server in Lab environment and use it for developing images
  - Only the images that pass all tests can be moved to production (which means move
  them to Hub and distribute them)
  - The approved image must stay the same (so it can't be rebuilt again)
  - The development SUMA server should be as much separated from Hub as possible,
  to be sure that the development does not break anything in production. Building
  images on Hub is quite dangerous from this point of view.

- Adjust deployment details
  - currently the image pillars are write-only in SUMA, the users might want to change some details


Proposed solution:

- Implement API calls to
  - Get Kiwi Image pillar
  - Update Kiwi Image pillar
  - Export Kiwi Image (complete metadata)
  - Import Kiwi Image
    - The server that exported the image might use differnt repos, activation keys, etc. This call must make sure that
    everything is consistent.

- Implement a tool that handles the use cases above
- Use the API in ISS

HWTYPE configurations
---------------------

This is currently implemented as a formula assigned to a group with special name.

FIXME: pick one alternative

Alternative 1:
Extend retail_yaml to create the groups and formula data via Hub and Peripheral Server API.
This is relatively small change to the code.

Alternative 2:
Central creation of groups is covered in [Hub Users RFC](00061-hub-users.md). The salt states
can be extended to handle also formula data.
This approach is probably more flexible.

Both alternatives will have to cope with authentization and Hub vs. Peripheral server user credentials.

In long term, alternative 2 is clean solution.

Alternative 1 might be used as a short term fix and also to keep compatibility.

Note:
The Formula pillar files depend on group IDs. The IDs differs between Hub and Peripheral server so
direct file-based synchronization of pillars is not possible.


YAML configuration
------------------

FIXME: optional, related to Alternative 2 in previous section

We have retail_yaml tool for initial configuration of Retail environment from
[YAML](https://github.com/uyuni-project/retail/blob/master/python-susemanager-retail/example.yml) file.
[Hub Users RFC](00061-hub-users.md) introduced similar concept, based on Salt.
Maybe these parts could be merged.


Combined Peripheral and Branch server
-------------------------------------

Branch services are configured by Salt formulas. Also PXE entries for each terminal are generated
by Salt (currently via reactor).
With combined Peripheral and Branch server, these formulas should be applied on SUMA server itself.

Terminals connect to SUMA directly, SUMA Proxy is not needed.


FIXME: pick one alternative

Alternative 1: Hub as a Salt Master for Combined Peripheral and Branch server

- this is already used for [Hub Users RFC](00061-hub-users.md)

problems:
- does not work for PXE entries https://github.com/uyuni-project/uyuni-rfc/pull/46
  The event from each booting Terminal must be stopped on Peripheral server, on
  Hub it would cause the same scalability problems as before.

- mixed environment with Hub, Peripheral Servers with standalone Branch Serveres and
  Combined Peripheral Servers will have non-optimal configuration
  For example: A shop uses Combined Peripheral and Branch server, then the number of terminals grows and
  at some point it is necessary to add standalone Branch Server. Then the configuration of the
  shop would be split between Hub and Peripheral Server, or the shop would have to be reinstalled
  with 2 Branch Servers and standalone Peripheral Server

- does not cover the "Single server" setup


Alternative 2: Multi-master setup of Combined Peripheral and Branch server

- Salt minion running on Combined Peripheral and Branch server has 2 masters - Hub and itself
- the Branch Server configuration via formulas can stay unchanged

problems:
- SUMA registered to itself cause many problems
  - we already have clients that do not allow certain actions (containers) so this should be fixable
  - if we allow and test this scenario for Retail, we will know how it behaves for
  non-Retail use and the most severe problems will be fixed (instead of just saying "we don't know")
- possible security implications - users will gain access to the server
  - this is not a problem for Retail. Peripheral server will be managed by Hub admins who can access everything
  and optionally by local admins who should access for example all machines in one building.
  There is no need for other roles.

- Salt Multi-master might not be reliable


Alternative 3: Use salt-call --local for Branch server part of combined server

- how to represent such setup in GUI and API ?
- would need significant changes in SUMA code:
  - use salt-call --local instead of Salt API
  - make sure that pillars are available
  - maybe changes in handling salt events


Alternative 4: Virtualize Branch server part of combined server

- use separate VM / container for the Branch server
- the minion connects to SUMA on the same physical host

- solves all the problems of other alternatives
- Branch server as VM could be solved by documentation only - the user might be
aready using some virtualization setup and we don't want to break it.

Problems:
- higher HW requirements


# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?

TBD

# Alternatives
[alternatives]: #alternatives


Images + Image metadata:

- Implement Kiwi Image Store - HTTP server + API to handle metadata (similar functionality as Docker store)

- Work with Kiwi upstream to include all the data to the image tarball, so the import functionality can be simplified
  - it will not work for old images build without the metadata,
  - some metadata are too SUMA-specific - for example activation key.
  - need to download and unpack the tarball, which can be stored on different machine.

- Use of Bittorrent protocol to distribute images from Hub to branches
  - It is expected that the VPN network topology is star-like, with Hub in the center. In this setup Bittorrent protocol won't help.


HWTYPE configurations:

TBD

Combined Peripheral and Branch server:

TBD

# Unresolved questions
[unresolved]: #unresolved-questions

- is nested Hub needed?
  The use case with one Peripheral Server per shop might exceed the maximum number of Peripheral Servers.
  This can be decided later, based on feedback.

