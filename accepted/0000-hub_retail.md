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


Possible configurations
-----------------------

1. Full
```
    Terminal -> Branch Server -> Peripheral Server -> Hub
```

2. Combined SUMA and Branch server 
```
    Terminal -> Branch + Peripheral Server Combined -> Hub
```

3. Standard
```
    Terminal -> Branch Server -> SUMA Server
```

4. Single server
```
    Terminal -> Branch + SUMA Server Combined
```


Global Retail data
------------------

The following items are typically shared in whole organization, so they should be visible and 
manageable via Hub.

  - Images - distributed as large tarballs via http
  - Image metadata - pillars, list of packages
  - HWTYPE configurations - group formula
  
Local data
----------

The following items do not need central management and can stay on Peripheral Server.

  - Branch groups -  groups containing Branch Server and connected terminals
  - Branch formulas - describe configuration of Branch services - network, pxe, dhcp, dns
  - Branch PXE data - entries describing how to boot each terminal
  
# Detailed design
[design]: #detailed-design

Images + Image metadata
-----------------------

Current situation: an image is built on Buildhost, then pushed to SUMA Server htdocs directory. Then SUMA creates a db entry (including package list) and a pillar file.
The pillar conains URL of image tarball, checksums and additional deployment details. It is used for image synchronization and deployment. These data are extracted 
on Buildhost at the end of build phase. Some of the data can't be extracted later form the tarball.

The SUMA API related to images is rather docker-centered. For Kiwi images it allows to list images and packages and delete an image.

Use cases currently not covered:

- Move image tarball to external HTTP server
  - In large environments it makes sense to use one or more servers for distribution of images, it should not be the Hub itself.
- Copy image metadata from one SUMA Server to another 
  - Hub - copy to all servers
  - Test in lab, then move the same image to production.
- Adjust deployment details


Proposed solution:

- Implement API calls to
  - Get Kiwi Image pillar
  - Update Kiwi Image pillar
  - Export Kiwi Image (complete metadata)
  - Import Kiwi Image

- Implement a tool that handles the use cases above


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

YAML configuration
------------------

FIXME: optional, related to Alternative 2 in previous section

We have retail_yaml tool for initial configuration of Retail environment from YAML file.
[Hub Users RFC](00061-hub-users.md) introduced similar concept, based on Salt.
Maybe these parts could be merged.


Combined SUMA and Branch server
-------------------------------

Branch services are configured by Salt formulas. Also PXE entries for each terminal are generated
by Salt (currently via reactor).
With combined SUMA and Branch server, these formulas should be applied on SUMA server itself.

Terminals connect to SUMA directly, SUMA Proxy is not needed.


FIXME: pick one alternative

Alternative 1: Hub as a Salt Master for Combined SUMA and Branch server

- this is already used for [Hub Users RFC](00061-hub-users.md)

problems:
- does not work for PXE entries and disconnected operation
- mixed environment with Hub, Peripheral Servers with standalone Branch Serveres and 
  Combined Peripheral Servers will have non-optimal configuration
- does not cover the "Single server" setup


Alternative 2: Multi-master setup of Combined SUMA and Branch server

- Salt minion running on Combined SUMA and Branch server has 2 masters - Hub and itself

problems:
- SUMA registered to itself cause many problems
  - we already have clients that do not allow certain actions (containers) so this should be fixable
- Salt Multi-master might not be reliable


Alternative 3: Use salt-call --local for Branch server part of combined server

- how to represent such setup in GUI and API ?
- would need significant changes in SUMA code


Alternative 4: Virtualize Branch server part of combined server

- use separate VM / container for the Branch server
- the minion connects to SUMA on the same physical host

- solves all the problems of other alternatives
- Branch server as VM could be solved by documentation only - the user might be
aready using some virtualization setup and we don't want to break it.



# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?

  * obscure corner cases
  * will it impact performance?
  * what other parts of the product will be affected?
  * will the solution be hard to maintain in the future?

# Alternatives
[alternatives]: #alternatives


Images + Image metadata:

- Implement Kiwi Image Store - HTTP server + API to handle metadata (similar functionality as Docker store)

- Work with Kiwi upstream to include all the data to the image tarball, so the import functionality can be simplified

- Use of Bittorrent protocol to distribute images from Hub to branches
  - It is expected that the VPN network topology is star-like, with Hub in the center. In this setup Bittorrent protocol won't help.


HWTYPE configurations:

TBD

Combined SUMA and Branch server:

TBD

# Unresolved questions
[unresolved]: #unresolved-questions

- What are the unknowns?
- What can happen if Murphy's law holds true?
