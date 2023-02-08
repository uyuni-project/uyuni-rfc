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

## Possible configurations


### 1. Standard
```
    Terminal -> Branch Server -> SUMA Server
```
  This is the currently supported configuration.
  It is suitable for one large department store.
  For larger deployments there may be problems with the number of terminals or with network outages.
  The SUMA Server must be reachable in order to perform any change of Terminal configuration.

  ##### Terminal

  - deployed from OS Image during boot (by applying Saltboot state)
  - then works as standard SUMA minion


  ##### Branch Server (alternative 1)

  - SUMA Proxy
  - downloads Images from SUMA (over HTTP) and distributes them to Terminals (over HTTP, TFTP, etc.)
  - runs services needed by Terminals (DHCP, TFTP, HTTP, ...). The services are configured via Formulas with Forms.


  ##### [Containerized Branch Server](https://github.com/uyuni-project/uyuni-rfc/blob/master/accepted/00087-containerized-branch.md) (alternative 2)

  - SUMA Proxy
  - TFTP redirected to HTTP
  - Images downloaded via Squid HTTP proxy
  - PXE entries are handled by Cobbler on SUMA Server
  - no salt formulas, DHCP must be configured manually


  ##### SUMA Server

  - standard SUMA operations
  - holds the configuration for Branch server services in Formulas
  - controls boot process of each Terminal by applying Saltboot state
  - triggers update of PXE data on Branch Server


### 2. Full
```
    Terminal -> Branch Server -> Peripheral Server -> Hub
```
  Adding Hub on top of previous configuration solves the problems with scalability and offline operations.
  It is suitable for for large organization with many department stores. It can look like this:

  - Branch server on each floor
  - Peripheral server in each building
  - Hub in datacenter


### 3. Combined Peripheral and Branch server
```
    Terminal -> Branch + Peripheral Server Combined -> Hub
```

  Customers with many small shops do need Hub for offline operations but do not need
  separate Branch server and Peripheral Server because the number of connected terminals is low.
  Running Branch + Peripheral Server on one machine could save resources.
  The Proxy part of Branch server is not needed then.


### 4. Single server
```
    Terminal -> Branch + SUMA Server Combined
```
  Suitable for one small shop.
  This scenario is not a hard requirement but there were such requests for SLEPOS
  so it would be nice to have it too.


## Global Retail data

The following items are typically shared in whole organization, so they should be visible and
manageable via Hub.

  - Images - distributed as large tarballs via http
  - Image metadata - pillars, activation keys, list of repos and packages (in DB)
  - [HWTYPE](https://www.uyuni-project.org/uyuni-docs/en/uyuni/retail/retail-deploy-terminals.html#_create_a_hardware_type_group) configurations

## Local data

The following items do not need central management and can stay on Peripheral Server (like in the current implementation).

  - Branch groups -  groups containing Branch Server and connected terminals, includes Saltboot groups for Containerized Branch Server
  - Branch formulas - describe configuration of Branch services - network, pxe, dhcp, dns
  - Branch PXE data - entries describing how to boot each terminal

# Detailed design
[design]: #detailed-design

## Images + Image metadata

Image files with corresponding metadata and pillars are already synchronized.
Further customization is possible via API

## HWTYPE configurations

This is currently implemented as a formula assigned to a group with special name.


Central creation of groups is covered in [Hub Users RFC](https://github.com/uyuni-project/uyuni-rfc/blob/master/accepted/00061-hub-users.md). The salt states
can be extended to handle also formula data.

This will have to cope with authentization and Hub vs. Peripheral server user credentials.


### YAML configuration

We have retail_yaml tool for initial configuration of Retail environment from
[YAML](https://github.com/uyuni-project/retail/blob/master/python-susemanager-retail/example.yml) file.
[Hub Users RFC](https://github.com/uyuni-project/uyuni-rfc/blob/master/accepted/00061-hub-users.md) introduced similar concept, based on Salt.
These parts could be merged.


## Combined Peripheral and Branch server

The components from Containerized Branch Server can be re-used also in this scenario.

Required components:

- Saltboot group
- Cobbler / TFTP   
- Mapping of branch-local URLs
- DHCP server


### Mapping of branch-local URLs

https://github.com/SUSE/spacewalk/issues/18455

Non-containerized retail branch server uses image pillars to map branch-local image URLs to SUMA server URLs.

Containerized branch server does not have access to pillars, so it currently implements this 
functionality by apache mod_rewrite. This is quite error-prone, because it expect URL in certain 
format. It can't work with images on external server.
https://github.com/SUSE/spacewalk/blob/Manager-4.3/containers/proxy-httpd-image/uyuni-configure.py#L166

Proposed fix: implement the mapping by HTTP redirects in java on SUMA server. Java has access 
to pillars in DB, so it does not have to do any guessing.
This will cover also the Combined Peripheral and Branch server case.


### DHCP server

In Hub setup, DHCP on Peripheral Servers can be configured via formula on Hub.

# Drawbacks
[drawbacks]: #drawbacks

None

# Alternatives
[alternatives]: #alternatives

HWTYPE configurations:

Extend retail_yaml to create the groups and formula data via Hub and Peripheral Server API.


# Unresolved questions
[unresolved]: #unresolved-questions

- is nested Hub needed?
  The use case with one Peripheral Server per shop might exceed the maximum number of Peripheral Servers.
  This can be decided later, based on feedback.

