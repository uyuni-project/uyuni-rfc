- Feature Name: hub_general
- Start Date: 2019-10-09
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

We want to define an Uyuni-based solution using multiple Servers to be able to manage a bigger number of clients than it is possibly doable with just one Server.

Please note that this will be detailed in several upcoming RFCs. This RFC is only meant to provide context and high-level design directions, but it is not meant to be binding or technically implementable in one step.

# Motivation
[motivation]: #motivation

**Scalability**: some of our users need to manage large amounts of clients (tens of thousands). Currently, this is impossible to achieve using a single Server and there is no forecast of being able to accomplish that in the foreseeable future.
We want to define a new Uyuni-based solution to provide a reasonable subset of Uyuni functionality at that scale.

**Store independence**: an additional specific problem arises in retail environments, where the need is to manage a very large number of clients in a large number of physical locations (stores). Stores should be able to use a reasonable subset of Uyuni functionality locally even in temporary or prolonged absence of a connection to the Internet or a company intranet, in particular to a central data center.

## Requirements
[Requirements]: #Requirements

### Functional requirements (by importance)
  * Hub provides visibility over the whole infrastructure (Servers, Proxies, clients...)
  * Hub manages Servers in terms of upgrades
  * Hub implements API endpoints to act on Servers
    * Main expected use cases:
      * Content management (eg. channel cloning)
      * Automated patching
      * Configuration management
  * Hub implements aggregated reporting
    * client data to be pulled from Servers periodically
  * Hub implements centralized content management of (in order of importance)
    * Packaged software
    * Configuration Management data (states, pillars...)
    * OS Images
    * Container Images
  * Managed content can be selectively synced from Hub to Servers
    * Same order of importance defined above
    * Synchronization has to be atomic
    * Synchronization has to be doable via a storage media instead of a network for certain network-constrained environments (defense, China)
    * Nice-to-have: avoid the download of content from the Hub if it is faster to retrieve it from other locations (SCC, SMT...)
    * Nice-to-have: on-demand downloading from the Hub should be considered (Proxy/Squid model)
  * [Uyuni for Retail extension](https://github.com/uyuni-project/retail) is updated so that either Uyuni Servers or some third-party components can provide services currently made available by the Retail Branch Server
  * Administration of Servers is simplified. In order of importance:
    * automatic application of schema upgrades
    * automatic creation of bootstrap repos
    * Servers do not need to connect to SCC or any external repo (provided they are connected to the Hub)
    * Server/Hub GUI alert when updates are available for the Server/Hub itself
    * installation of Servers is automated via Salt
    * in principle any Server configuration can also be done via Salt (eg. creation of pillar stores, users, groups...)
    * default DB backup via Taskomatic
  * Hub implements UIs to act on clients
  * Optionally centralized definition of users and permissions

### Non-functional requirements
  * Performance: support high number of clients and Servers
    * maximum expected number of clients: above 100k
    * maximum expected number of Servers: 9k
    * typical numbers:
      * 3 to 20 Servers with a few thousand clients each ("large data center scenario")
      * a few thousand Servers with 10-20 clients each ("large retailer scenario")
  * Compatibility: all OSs currently supported by Uyuni (may not be all supported in first version)
  * Maintainability: any new component should be designed in a modern way, with containerization/scalability/HA in mind
  * Performance: Server functionality can stripped down in order to achieve smaller hardware footprint

### Requirements explicitly excluded from this effort's scope
Those are part of the long-term vision but were not given priority over other requirements, will not be analyzed further in the scope of this effort.

  * Monitoring features. It's likely interesting but it's a totally separate research and implementation effort
    * any "real-time" updates of data in the Hub. Hub will only host "high-latency", reporting data
  * Provisioning features: Cobbler/Kickstart/AutoYAST
  * Load balancing/high availability of Servers
  * General backup of Servers (certificates, PKI files, Salt files, configuration files, rpms, own scripts...)
  * SCAP auditing
  * Subscription matching
  * Centralized logging infrastructure

## Long-term solution vision
[Long-term solution vision]: #long-term-solution-vision

* Employ several Servers - each Server managing a distinct subset of clients
  * if **store independence** is required, assume one Server per store
* Implement a new "Server of Servers", called a Hub, to restore the "single pane of glass" concept
* All functionality currently available from a Server is to be available from the Hub. In particular:
  * Hub provides visibility over the whole infrastructure (Servers, Proxies, clients...)
  * Hub aggregates data coming from Servers to provide aggregated reporting
  * Hub provides an APIs/UIs to manage content centrally (packaged software, images...)
  * Hub has APIs/UIs to dispatch commands to Servers which will in turn act on clients
* Some Server functionality, notably the UI, is made optional and de-activated by default. Servers are to be reduced to "headless independent local executors" with a lower hardware footprint
  * Some customers might still want to operate Servers independently, so functionality can't be completely removed
* Hub and Proxies are optional depending on installation size, network topology and other requirements. Several overall configurations are possible

## High-level design choices

- Hub will be a Server with extra components/functionality
- Several (standard) Servers will be connected to the Hub (registered to it as minions). Hub will manage those Servers via standard functionality
- Existing content management functionality will be used as-is in the Hub. By default only the Hub will be connected to SCC/SMT/RMT, and not Servers
- ISS will be overhauled to move more types of managed content from Hub to Servers (channels, Salt states, images...)
- Hub will store data from Servers for reporting. A data collection mechanism to transfer data from Servers to Hub will be implemented
- Hub will have a new API component to allow access to APIs of Servers (XMLRPC and Salt)
- the Uyuni for Retail extension will get Proxy-less capability

Note that, at the moment, it is not planned to reimplement Server functionality on top of the Hub.

# Unresolved questions
[unresolved]: #unresolved-questions

None known at this point.
