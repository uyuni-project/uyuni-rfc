- Feature Name: Basic SaltStack Integration
- Start Date: 2015-10-22
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

One para explanation of the feature.
Customers are demanding configuration management and a more consistent systems management framework.

Saltstack is a young but popular and active stack that offers both.

This RFC describes how to integrate SUSE Manager with Saltstack in a way that Saltstack becomes the core that powers the product, still allowing SUSE Manager to provide its own value, by focusing in the interesting problems and not so much on the mechanics.

# Motivation
[motivation]: #motivation

* Support configuration management and the application of declarative state to managed clients.
* Use a community maintained client stack with less legacy cruft.
* Aim for better real-time and scalable communication between server and clients.
* A better framework for eventing and monitoring integration.

# Detailed design
[design]: #detailed-design

## Basics

* Old style systems will still be supported.
* Features on minions will be implemented gradually, taking advantage of the new technology.
* SUSE Manager would be able to manage plain minions without the need for additional agents.
* SUSE Manager server is a Salt master
* All the communication happens via salt-api/REST

## The event reactor

* The event reactor is a Java thread/service that keeps an event channel with salt-api (websocket).
* Events coming from Salt are handled and actions are performed.

## The client library

* SUSE Manager will talk to Salt using a client library the team already prepared:
  * https://github.com/SUSE/saltstack-netapi-client-java

## Basic Events Handled

### Minion start

If the minion.up event comes:

* The reactor asks for the machine_id and sees if the minion was already registered with a same or different hostname
* If not, the minion is registered into SUSE Manager with a Saltstack entitlement.
* A custom event is fired (susemanager/minion/registered) including:
  * minion_id
  * machine_id
* Jobs to get the hardware, package inventory, and other data (eg. last boot) are fired.
* Last checkin attribute is updated.

# Drawbacks
[drawbacks]: #drawbacks

* The reactor approach based on the API is not as efficient as connecting directly to
  salt event socket, but keeps things better decoupled and allow for salt-master to
  run in a different machine.

# Alternatives
[alternatives]: #alternatives

* We prototyped the integration using a python based reactor that got the event stream from
  the salt-master socket and wrote directly to the SUSE Manager database.
  * https://github.com/SUSE/spacewalk-saltstack

# Unresolved questions
[unresolved]: #unresolved-questions

## Registration

* which organization should the salt minion belong to?
* who can see the not yet accepted minions and who is allowed to accept them (user role)?
* how to define an organization where a minion should belong to before registration (activation key in the old stack)

## Other features on top of salt

For Future RFCs:

* Package management.
* Repository access.
* Configuration management and SUSE Manager interaction with the sls tree
* Groups and policies applied to groups of systems.
