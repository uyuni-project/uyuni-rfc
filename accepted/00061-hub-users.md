- Feature Name: hub_users
- Start Date: 2019-10-10
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

Uyuni Server has the concepts of System Group, Org, User and permissions. All of those assume there is one central management point for the whole infrastructure.

With the Hub architecture, there will be multiple Servers - this RFC details how those concepts will work in that environment.

See the [Hub general RFC](accepted/00060-hub-general.md) for an introduction to the Hub project.

# Motivation
[motivation]: #motivation

End users might want to define security policies for the whole Uyuni infrastructure (Hub and Servers).

Additionally, from the requirements:

> * in principle any Server configuration can also be done via Salt (eg. creation of pillar stores, users, groups...)

The [Hub XMLRPC RFC](accepted/00062-hub-xmlrpc-api.md) also depends on a definition of the authentication/authorization/access control model.

# Detailed design
[design]: #detailed-design

## Definitions
- a Server-User is a User defined on a Server (a client of the Hub)
  - Server-Orgs and Server-SystemGroups are defined analogously
- a Hub-User is a User defined on a Hub
  - Hub-Orgs and Hub-SystemGroups are defined analogously

## Parts not expected to see code changes

- Servers continue to have Users and Orgs as before, with the current permission semantics. No code changes are expected on Server code
  - Hub, being a Server of Servers, also continues to have its own set of Users and Orgs with current permission semantics (inherited from Server code)
  - Consequently:
    - a Server-User having permissions on a client means that she can administer ("is root on") that client
      - this means she will be able to act on the Client via the Server API, among other things
      - note that she will not necessarily, and not usually, administer ("be root on") the Server itself
    - a Hub-User having permissions on a Server means that she can administer ("be root on") that Server
      - this means she will be able to modify the Server via the Hub's XMLRPC API
      - it is an open problem/separate RFC if and how the Hub-User can act on the Server's clients (current plan is to enable that via an XMLRPC API gateway)
      - note that in principle, given the Hub-User "is root on" the Server, she can also gain "root access" to all its clients. This is not practically preventable, but might not be the typical use case
    - note: in principle, Server-Users and Hub-Users may serve different purposes. Some customers might be OK in conflating them (any Server-Users to also have a corresponding Hub-User) but this is not necessarily universally true

## New code

- Salt [state modules](https://docs.saltstack.com/en/latest/ref/states/writing.html) will be implemented to create Users, Orgs, Server Groups and give them all sorts of permissions from configuration (eg. in SLS form) on the Hub. As an example, consider this SLS fragment to be applied to 10 Servers registered against the Hub:

```yaml
acme_org:
  uyuni.org.present:
    - name: ACME Corp
    - first_username: acmeadmin
    - first_password: adcmesecret

superadmin:
  uyuni.user.present:
    - name: superman
    - password: idontlikekryptonite
    - org: ACME Corp
    - org_admin: true

neophyte:
  uyuni.user.present:
    - name: student
    - password: secret
    - org: ACME Corp
    - org_admin: false
```

- state modules will be implemented in Python leveraging Servers' XMLRPC API
  - [a proof-of-concept has already been implemented to create Users and Orgs](https://github.com/rjmateus/uyuni-salt-modules-example)
  - related: in a past HackWeek [a runner, now in upstream Salt, was contributed](https://docs.saltstack.com/en/latest/ref/runners/all/salt.runners.spacewalk.html#module-salt.runners.spacewalk). It is similar in its intent to is proposed here
- A few example SLS states, or Formulas, will be created to help with typical cases

Notes:
- this will be "just a convenience feature" to let customers more easily define, inspect and apply security policies across many or all Servers. This RFC does not propose any real change of the model and mechanisms that currently exist
- by leveraging Salt this solution benefits from a mechanism which is very flexible:
  - SLS files allow to define a User/Org/SystemGroup/Permission structures as complicated as needed (from a single Server point of view), encouraging but not mandating uniformity across Servers
  - [minion targeting](https://docs.saltstack.com/en/latest/topics/targeting/index.html) allows to select which Servers get which SLS states based on FQDNs/ids, grains, custom information (pillars), SystemGroups and so on
- this proposal will not conflict with the use of PAM modules instead of the integrated authentication code
- this proposal is expected to be orthogonal with any implementation of a Single Sign-On architecture

## Relationship with the Hub gateway XMLRPC API

The Hub _gateway_ XMLRPC API ([RFC here](accepted/00062-hub-xmlrpc-api.md)) gives access to clients from the Hub through Servers. Parts of that RFC that are directly impacted by this RFC are reproduced below.

- Access to the gateway API itself requires Hub-User credentials. Access to individual Server APIs to manage clients requires Server-User credentials
  - in worst case, N+1 pairs of credentials will be needed (one for the Hub, one per N Servers)
  - as a special convenience option, the Hub gateway API can use Hub-User credentials to authenticate against Servers. So if a certain username/password was uniformly configured across several Servers (this is easy to implement with the states above), Hub gateway API usage becomes simpler: only one log in is needed, with its Hub-User credentials. After that a list of Servers to work with will have to be specified. This authentication mode can be optionally activated via a parameter (eg. `relayAuthentication = True`) on the `login` method
    - note: this only makes sense if it is deemed appropriate to use the same credentials of Server sysadmin users (Hub-Users) to also act on Clients (Server-Users). This might not always be the case
    - note: if Server sysadmin credentials must be separate from Client sysadmin credentials are required to be separate, it is still possible to use this option by creating a Hub-Org with no Servers. Any Hub-User in this Hub-Org will be able to connect to the Hub gateway API, and have permissions on Clients (assuming Servers have Server-Users with same name and passwords, again possibly configured via the above states). Org trusts will be needed to be set up if those users also need to perform content management
  - as an additional special convenience option, the Hub gateway API can automatically select the list of Servers a Hub-User works with, based on the list of Servers that same Hub-User has permissions on. Once again this can be optionally activated via a parameter (eg. `autoConnect = True`)
    - note: in this case only a single login with a pair of Hub-User credentials is needed, and then calls can be made directly
    - note: this only makes sense if it is deemed appropriate to use the same credentials of Server sysadmin users to also act on Clients. This might not always be the case

# Drawbacks
[drawbacks]: #drawbacks

## Limitations
 - SystemGroups would continue to be a Server-only concept, although one will be able to manage them via Salt states
 - Server-Users will not be tracked and managed in the Hub database directly, and there will be no UI/API for that. The same is true for Server-Orgs, Server-SystemGroups and permissions

## Impact on existing components and users

All code would be new in new modules and formulas, so no change to existing components is expected.

# Alternatives
[alternatives]: #alternatives

- move all authentication from Servers to the Hub, but keep access control on Servers
  - con: would break Servers in case the Hub is not reachable, or a caching mechanism has to be implemented
  - con: difficult to define a synchronization scheme that covers all use cases
- move all authentication and access control code to the Hub
  - con: a very extensive refactoring would be needed
- God mode: allow Hub free access to any Server, particularly regarding the XMLRPC API (once a User is logged into the Hub, he can do anything on any client)
  - con: it might not adapt to some organizations, which might prefer separating Hub-Users from Server-Users (eg. independent divisions)

# Next steps
[Next steps]: #next-steps
 - add an execution module to call a generic XMLRPC call, to make it possible to cover (potentially) any other area outside of this RFC
 - add Form support to Formulas
 - lift Limitations by adding new functionality to introduce UIs/APIs to centrally manage Users, Orgs, SystemGroups, permissions
 - create states automatically from an existing Server
 
# Unresolved questions
[unresolved]: #unresolved-questions

- it seems that the current set of Server XMLRPC APIs are sufficient to implement all modules, but could we add new endpoints to make it easier to use those modules (eg. not requiring an Org admin credentials if superuser credentials are available)
