- Feature Name: hub_xmlrpc_api
- Start Date: 2019-10-10
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

Uyuni Server has an XMLRPC API that allows access to most of its functionality.

With the Hub architecture, there will be multiple Servers - this RFC details a new XMLRPC API for the Hub to access Server functionality.

See the [Hub general RFC](accepted/00060-hub-general.md) for an introduction to the Hub project.

# Motivation
[motivation]: #motivation

End users might not want to access single Servers to automate operations across their infrastructure, so a Hub XMLRPC API endpoint would be useful to make third party scripting and integration easier.

From the requirements:

> Hub implements API endpoints to act on SUMA slave Servers
>
>    Main expected use cases:
>        Content management (eg. channel cloning)
>        Automated patching

# Detailed design
[design]: #detailed-design

### Basic funtionality
The Hub is a Server, so as far as it and its minions (Servers) are concerned, the Hub XMLRPC API work as of today.
Content management APIs will work as of today. Inter-Server Synchronization (ISS) will be used to push managed content from Hub to Servers.

### New service and endpoint
A new XMLRPC API endpoint will be created, implemented by a new service called the "XMLRPC Gateway API" (simply called "Gateway" from now on in this document). Technology-wise:
  * Implementation will be based on asynchronous I/O. Calls to several Servers should happen concurrently  
  * The exact technology choice is delegated to the implementation phase and could be:
    * typed Python, based on Tornado and [tornado-xmlrpc](https://pypi.org/project/tornado-xmlrpc/). Rationale: learning Tornado, which is also used in core Salt
    * typed Python, based on the native [asyncio library](https://docs.python.org/3.6/library/asyncio.html) (new to 3.4, similar in intent to Tornado). Rationale: learning latest Python technologies
    * in Go, using goroutines. Rationale: learning Go
  * there will be no backing database. All new methods will delegate to existing XMLRPC APIs (either the Hub's or individual Servers')
    - some kind of storage might be needed for performance/caching purposes, that is left as an implementation detail

### Topology exposure functionality
Gateway methods will be created to expose how Servers, clients and Hubs are connected, in particular methods will be needed to:
  * Get a list of `serverIds`
  * Get a list of clients registered to a Server given its `serverId`
  * Get a list of all clients, with the `serverIds` they belong to
  * Get `serverId`s for a given client (based on `minion_id`, FQDN or other identifier)
    - note: normal client IDs will not work, as they will surely overlap between Servers
    - note: normally only one result is expected, but there could be cases in which `minion_id`s are actually duplicated across Servers

### Gateway functionality

Idea is to expose existing Server XMLRPC endpoints/methods as they are on the Hub. The Hub will simply route calls to the right Server(s) and relay back results, rather than reimplementing any functionality. Areas are detailed below.

* Authorization and authentication
  * Gateway API will be secured via `hubSessionKey` tokens analoguously to Server's API
    * Actually, Gateway will delegate authentication to the Hub API
  * Consuming a Server's API from the Gateway continues to require a valid Server `sessionKey` token
  * There are three ways to attach Server sessions to the Hub session
    * Manual mode: programmer "attaches" Server sessions explicitly to his Hub session. Attachment lasts until logout
      * `hub.login(username, password)` → `hubSessionKey`
      * `hub.attachToServer(hubSessionKey, serverId, username, password)` → `serverSessionKey`
      * `hub.serverMethod(serverSessionKey, parameters)` → `output`
      * N+1 pairs of credentials will be needed (one for the Hub, one per each of the N Servers)
     * Authentication relay mode: as an additional convenience option, which can be activated with a flag, Hub-User credentials can be re-used to authenticate against Servers. So if a certain username/password is uniformly configured on the Hub and across several Servers, Gateway usage becomes simpler: only one log in is needed, with its Hub-User credentials
     * Automatic connect mode: as an additional convenience option, which can be activated with a flag, the Hub gateway API can automatically select the list of Servers a Hub-User works with, based on the list of Servers that same Hub-User has permissions on
       - note: that this only makes sense if users are OK with the idea of using Server sysadmin users to act on Clients
       - If they prefer to manage Clients via users that have no permissions to manage Servers, they can create a Hub-Org with no Servers. Any Hub-User in this Hub-Org will be able to connect to the Gateway, and possibly have permissions on Clients (if Servers have Server-Users with same name and passwords)

* Multicasting: call an XMLRPC method on _N_ Servers at once
  * method name stays the same
  * Assuming the method on the Server accepts _M_ parameters, the same method on the Hub will accept an array of _N_ parameters, each of which contains as elements the _M_ parameters for a given Server
    * eg. `actionchain.listChains(sessionKey)` → `hub.actionchain.listChains([serverSessionKey1, serverSessionKey2, ...])`
    * eg. `channel.org.enableAccess(sessionKey, channelLabel, orgId)` → `hub.channel.org.enableAccess([serverSessionKey1, channelLabel1, orgId1], [serverSessionKey2, channelLabel2, orgId2], ...)`
  * return types would be arrays of _N_ elements
    * special elements would be needed to signal Exceptions

* Availability
  * if a Server is down at the time a Gateway call targeting it is made, call should fail after a configurable timeout. If multiple Servers are targeted, only that call fails and others continue.
  * the timeout should have a default value configured via a file or environment variable, overridable on a per-call basis (eg. extra parameter)


## Impact on existing components and users

All code would be new in a new component, so no change to existing components is expected. No impact on existing users is expected at all.


# Drawbacks
[drawbacks]: #drawbacks

 - we are not adding any Hub-centered functionality basically, this is a little more than a router
 - if Servers are at different versions, some API endpoints might not be available in all Servers or might work differently. This is expected to be rare but possible, and in that case the error (eg. missing method) will be propagated to the calling program
   - note that API stability is guaranteed between major versions, and very broadly implemented between minor versions as well

## Limitations

- implementation of API methods currently not implemented on the Server, eg. downstream [#2361](https://github.com/SUSE/spacewalk/issues/2361) [#2362](https://github.com/SUSE/spacewalk/issues/2362), is explicitly not covered by this RFC

# Alternatives
[alternatives]: #alternatives
## Build on an existing API gateway

Several open source projects exist that offer API gateway functionality on any kind of network API (often, in practice, http-based protocols). Those projects typically offer a range of functionalities such as configurable retry patterns, additional security features, logging, monitoring, rate limiting, circuit breaking, caching and in some cases API aggregations and manipulation of requests and responses. In several cases, such engines provide plugin mechanisms or anyway lend themselves to implementation of ad-hoc modules that could fit in the requirements from this RFC. Summarizing:
 - pros: potentially many features would be provided by such tools. Only automatic retrying is required at this point, but others might also become relevant in future
 - cons: code bases are typically much bigger than the expected size of this project (1K - 2K LOC), and the type of request modifications required will still need they have to be implemented as plugins/extensions, which might lead to an approximately-similar coding effort

Alternatives that were considered come from:
 - GitHub projects with at least 1000 stars
 - [the CNCF category](https://landscape.cncf.io/category=api-gateway&format=card-mode&grouping=category)
 - a list provided as comment to the original version of this RFC
 
| Name                                                                                        | LOC    | Main languages   | Notes                                             |
|---------------------------------------------------------------------------------------------|--------|------------------|---------------------------------------------------|
| [gravitee](https://gravitee.io/products/apim/)                                              | 500k   | Java, TypeScript | Supports MongoDB, Redis, ElasticSearch...         |
| [tyk](https://tyk.io/features/features/)                                                    | 100k   | Go               | No request modification support, security only    |
| [wso2](https://wso2.com/api-management/features/)                                           | 5.636M | Java             | 28 main git repos                                 |
| [apiman](http://www.apiman.io/latest/)                                                      | 225k   | Java, TypeScript |                                                   |
| [krakend](https://www.krakend.io/features/)                                                 | 63k    | Go               | 41 git repos                                      |
| [kong](https://konghq.com/kong/)                                                            | 156k   | Lua              |                                                   |
| [ocelot](https://ocelot.readthedocs.io/en/latest/introduction/gettingstarted.html)          | 55k    | C#               |                                                   |
| [gateway](https://github.com/fagongzi/gateway#features)                                     | 46k    | Go               |                                                   |
| [spring-cloud-gateway](https://github.com/spring-cloud/spring-cloud-gateway#features)       | 39k    | Java             |                                                   |
| [janus](https://github.com/hellofresh/janus#key-features)                                   | 20k    | Go               | No request modification support, maintenance mode |
| [gloo](https://docs.solo.io/gloo/latest/introduction/whygloo/)                              | 202k   | Go               |                                                   |
| [goku](https://github.com/eolinker/goku-api-gateway/blob/master/README.md#product-features) | 183k   | Go               |                                                   |
| [api-umbrella](https://apiumbrella.io/)                                                     | 105k   | ruby             |                                                   |
| [apisix](https://github.com/apache/incubator-apisix#features)                               | 18k    | Lua              |                                                   |
| [apicast](https://github.com/3scale/apicast#features)                                       | 56k    | Lua              |                                                   |
| [expressgateway](https://github.com/expressgateway/express-gateway#main-features)           | 33k    | Javascript       |                                                   |
Note: Lua projects are actually Nginx plugins.

## Features
* Authorization and authentication
  * Alternative idea 1: a configuration file on the Hub contains a list of credentials and `serverIds`. Hub would automatically maintain a pool of Server `sessionKey`s from those credentials
    * `hub.login(username, password)` → `hubSessionKey`
    * `hub.serverMethod(hubSessionKey, serverId, parameters)` → `output`
  * Alternative idea 2: god mode. We would assume Hub is root on Servers, so somehow automatically gets full administrative API access to all anyway

* Multicasting
* Alternative idea 2: each of the _M_ parameters is replaced by an array of _N_ elements
  * eg. `actionchain.listChains(sessionKey)` → `hub.actionchain.listChains([serverSessionKey1, serverSessionKey2, ...])`
  * eg. `channel.org.enableAccess(sessionKey, channelLabel, orgId)` → `hub.channel.org.enableAccess([serverSessionKey1, serverSessionKey2, ...], [channelLabel1, channelLabel2, ...], [orgId1, orgId2, ...])`
  * return types would be arrays of _N_ elements

# Next steps
[Next steps]: #next-steps

* Client-addressed relay (CAR): programmer wants to call a method which is specific to a client, regardless of what Server it is registered to
  * method names, return values would be identical
  * parameters would have to change, in that the numerical `systemId` is typically not unique. `minion_id`, FQDN or some other unique identifier would have to be used
    * eg. `system.listNotes(sessionKey, systemId)` → `hub.system.listNotes(hubSessionKey, FQDN)`
    * note that `minion_id`s and FQDNs give no uniqueness guarantee per se. Server-prefixing might be necessary in absence of guarantees by users
  * there will be new Exception cases if there's more than one client with that `minion_id`/FQDN/ecc

* Topology exposure functionality: also expose Proxies

* Multicasting convenience feature: avoid repeat parameters if they are identical for all targeted Servers

* More Multicasting options:
  * Additional idea 1: Group-addressed relay (GAR): similar to client-addressed relay, but based on groups (not spanning Servers)
  * Additional idea 2: Server-addressed relay (SAR): programmer wants to call a method on a certain Server. Hub receives the call, it relays it to the right Server and brings back results once done
    * method names, return values and Exceptions would be all identical. Parameters would also be all equal apart from `sessionKey`, to be substituted with `serverSessionKey`
      * example: `system.listNotes(sessionKey, systemId)` → `system.listNotes(serverSessionKey, systemId)`
    * Hub-exposed Server methods could be in a separate namespace, or have a completely different API endpoint, or both
  * Additional idea 3: Broadcasting: like multicasting, but on all Servers at once

# Unresolved questions
[unresolved]: #unresolved-questions

None known at the moment.
