- Feature Name: Salt Client Channel Management
- Start Date: 2015-10-22
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

The integration with Saltstack requires us to design a way to manage the software channels on the client.

This RFC proposes a way to manage client channels that relies only on the Saltstack connectivity/registration.

# Motivation
[motivation]: #motivation

SUSE Manager right now manages the client channels through a custom plugin that talks to the server on every zypper service refresh and re-syncs the assigned channels.

This means:

* The client needs to talk to the XML-RPC API
* The client needs all the rhn client library
* The client needs a zypper plugin that refreshes the repository list

[RFC 00001-salt-integration](00001-salt-integration.md) aims for a pure minion system. Therefore it should be possible:

* To rely as much as possible on Salt itself.
* To avoid extra components needed on the client.

At the same time, by side-effect, opens the ability to allow 3rd parties to access the SUSE Manager channels. A long standing customer wish.

# Detailed design
[design]: #detailed-design

## Basic decisions

* A valid minion can access any repository on the server

## Repository access

Right now zypper accesses the channels via the endpoint:

```
https://sumahost/XMLRPC/GET-REQ/channel-label
```

This needs:

* A special token obtained from a previous login call via XML-RPC
  * zypp-plugin-spacewalk injects this token
* Does not allow HEAD requests
  * zypp-plugin-spacewalk appends ?head_requests=no to the URL

So we first fix the XML-REQ/ endpoint or create a new one, so that it accepts:

* A normal access token, with expiration date (eg. using JWT)

This token can be generated even in SUSE Manager itself: A UI to generate tokens than can be
used to access the channels.

## Repository management

The service or list of repositories would then be handled as plain salt state.

SUSE Manager would generate on the server side a sls file that covers all the repository configuration, including tokens, head_request parameters etc.

## Example

You change the channel assignment of a minion to have only the sles-12-pool channel.

When you save, SUSE Manager would:

* Call the token generation API and generate a long lived token
* generate a /srv/susemanager/salt/channels-minionid.sls that specifies that minion should have a set of repository files in /etc/zypp/repos.d with the right url and the token already present.
* Make sure top.sls includes this state for that minion.

When the minion state is applied, the repositories would be configured as desired.

Optionally: the master could trigger applying this state from the server side after saving and generating it.

# Drawbacks
[drawbacks]: #drawbacks

* It requires to apply the highstate to get the repositories. It may be confusing from the client side.* However this problem can be solved as described above, triggering the specific state after saving.

# Alternatives
[alternatives]: #alternatives

* Keep zypp-plugin-spacewalk and solve the missing pieces of it running in a Salt environment.

# Unresolved questions
[unresolved]: #unresolved-questions


