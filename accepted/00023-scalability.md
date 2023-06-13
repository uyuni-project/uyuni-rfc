- Feature Name: Scalability Work
- Start Date: 2016-03-01
- RFC PR: 32

# Summary
[summary]: #summary

We want to study scalability properties of SUSE Manager, explore architectural possibilities, provide blueprints for large deployments.

# Motivations
[motivations]: #motivations

 * there is a customer who expects to run SUSE Manager to manage 300K Linux servers, and we currently do not know how to do that
 * Sales would benefit from Postgres benchmarks to convince remaining Oracle customers to move away from it
 * Support and Consulting would benefit from benchmark results, best practices, etc. related to scalability
 * some sales are slowed down or stuck because of lack of scalability numbers or guarantees from Engineering
 * we could facilitate sales of SLES HA, SUSE CaaSP, SUSE Storage by providing architecture blueprints that include them

# Detailed design
[design]: #detailed-design

## Goals

Primary goal:
 * determine the current upper limit of minions that can be simultaneously connected to a SUSE Manager server while allowing a reasonable patch rate
   * the *patch rate* is the number of minions that can be patched per hour, on reasonable hardware. Our current estimation is 5K, to be confirmed by benchmarks
   * current high level mark is 15K traditional clients per server, 5K traditional clients per proxy

Secondary goals:
 * determine if and how different architectures (eg. proxies, syndics) could help reaching higher limits
   * note: at the moment it has not been determined if the 300K server count mentioned in the motivations is reachable, and at which conditions. It is a goal of this research to either eventually reach this objective or to describe why it is not feasible
 * research a Postgres-based alternative to Oracle RAC from an HA point of view
 * research an overall SUSE Manager architecture from an HA point of view

Expected collateral benefits:
 * documentation improvements (hardware requirements, best practices, wikis, etc.)
 * development/testing tool improvements ([sumaform](https://github.com/moio/sumaform), [evil-minions](https://github.com/moio/evil-minions/), [mgr-db-locks](https://github.com/moio/mgr-db-locks), etc.)
 * bug discovery and fixing
 * contribution to performance/scalability specific features
 * knowledge building

## High level plan
Already completed:
 * survey database architecture options from a performance POV
  * identify alternatives, pros/cons
  * formulate an implementation proposal
 * survey minion simulation possibilities. Identify hardware requirements, accuracy, limitations

In progress:
 * attempt patching 5K, 15K, 30K, 60K, 100K minions. Determine actual limits and bottlenecks
 * research proxy density criterion
 * research the HA topic

## Process
Cards will be prepared to break down the high level plan in workable chunks, and will be proposed Sprint by Sprint.

When the Sirius squad is the Round-Robin-Bug-Squad, performance related bugs will be taken preferably.

Contact will be kept with interested Consultants.

# Drawbacks
[drawbacks]: #drawbacks

None known.

# Alternatives
[alternatives]: #alternatives

 * prioritizing research on HA over scalabillity
 * prioritizing research on scalability over a different variable (eg. number of traditional clients, number of packages, number of channels, etc.)
 * prioritizing research over network delivery problems (eg. geographically sparse networks, limited bandwidth, unreliable channels, etc.)

# Unresolved questions
[unresolved]: #unresolved-questions

As knowledge on the topic is gained, this plan might need revisions that will be proposed via PR.
