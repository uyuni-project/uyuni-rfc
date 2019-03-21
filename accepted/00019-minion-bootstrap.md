- Feature Name: Bootstrapping of Salt Minions
- Start Date: 2016-06-01

---
* Johannes Renner <jrenner@suse.com>
* Michael Calmer <mc@suse.com>

# Summary
[summary]: #summary

SUSE Manager should allow its users to bootstrap clients with the necessary setup to be further managed.

# Motivation
[motivation]: #motivation

Any system needs some setup in order to be connected to SUSE Manager for being managed. In case of a Salt based client this setup mainly consists of the installation and configuration of the `salt-minion` service. This procedure can be automated so that SUSE Manager users can bootstrap new clients from the server's UI.

# Detailed Design
[design]: #detailed-design

## The Procedure

The bootstrapping procedure generally consists of the following steps:

1. Deploy the SSL CA certificate of the server
2. Deploy necessary GPG keys
3. Configure the bootstrap repository
4. Install the `salt-minion` package
5. Configure `salt-minion` to point to the SUSE Manager server
6. Start and enable the `salt-minion` service
7. Disable the bootstrap repo and other non SUSE Manager repos (happens during registration)

This procedure can be implemented as a Salt state to be applied from the server via `salt-ssh`. It should be mentioned here only for reference that customers will also have the option to generate bootstrap scripts to be used in the same way as the bootstrap scripts for traditionally managed clients.

## Bootstrapping Clients from the Server UI

The SUSE Manager server should offer a UI to bootstrap clients allowing the user to provide a certain set of parameters. These parameters may include the following:

- hostname(s) or IP adress(es) of client(s)
- user and password or an ssh identity to be used for logging in
- activation key(s) to be applied during the registration
- list of GPG keys to be deployed

The new UI should be tightly integrated with the existing "System Overview" page since it basically will allow users to add systems there. An initial implementation can support adding only a single system, but during the design phase it should be kept in mind that eventually users will want to bootstrap a list of systems all at the same time.

[Pre-accepted keys] (https://docs.saltstack.com/en/latest/topics/tutorials/preseed_key.html) should further be used in order to avoid the need for manually accepting the key afterwards (onboarding). The bootstrapping procedure should be implemented as a Salt state to be applied to clients via [`salt-ssh`] (https://docs.saltstack.com/en/latest/topics/ssh/) (see the [hackweek prototype] (https://github.com/SUSE/spacewalk/compare/Manager-minion-bootstrap)).

## Activation Keys

Referenced activation key(s) as selected in the user interface can be passed to the `state.apply` call as non-permanent pillar data. Registration code therefore needs to be adapted to read activation keys from the following sources (in this order):

1. From *grains* as stored on the minion
2. From *permanent pillar data* as stored on the server
3. From what is entered in the UI when bootstrapping (passed to the `state.apply` function as *non-permanent pillar data*)

This in consequence should allow users to assign activation keys by adding pillar data matching certain grains like e.g. all machines with `os_release` X and mac address in range foo should get activation key Y applied during registration.

# Drawbacks
[drawbacks]: #drawbacks

Why should we *not* do this?

# Alternatives
[alternatives]: #alternatives

What other designs have been considered? What is the impact of not doing this?

# Unresolved Questions
[unresolved]: #unresolved-questions

- Q: Users who want to bootstrap minions from the SUSE Manager server but don't want to use the UI, how are they supposed to do it?
- A: We could add either API (XMLRPC or Salt API?) or commandline support to trigger the same state application that the UI does.
