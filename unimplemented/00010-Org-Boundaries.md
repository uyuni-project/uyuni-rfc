- Feature Name: Organization boundaries in Salt clients
- Start Date: 2016-02-15

# Unimplemented note

This RFC was not ultimately implemented as a different design was preferred. It is still archived here for historical purposes.

# Summary
[summary]: #summary

One para explanation of the feature.

# Motivation
[motivation]: #motivation

Suse Manager has the concepts of organizations to group client machines and users. A user that belongs to an organization will have the right to manage only the machines in that organization.

Suse Manager exposes the abiliy to run arbitrary Salt commands. Minions can be targeted using the Salt syntax, without any restrictions imposed on the targeting expression.
Since Salt does not have the concept of organizations if would be possible to execut a command on minions from a diferent organization. 
Therefore Suse Manager must restrict the minions to only those that belong to the user's organization.

# Detailed design
[design]: #detailed-design

The Salt remote execution GUI will work in two steps:

1. Get a list of minions by calling module `match.glob` and then filter it to retain only those minions that belong to the user's organization.
2. Execute the command only for the filtered list of minions. Salt will actually receive a list of minions instead of the targeting expression.

# Drawbacks
[drawbacks]: #drawbacks

Why should we *not* do this?

# Alternatives
[alternatives]: #alternatives

What other designs have been considered? What is the impact of not doing this?

# Unresolved questions
[unresolved]: #unresolved-questions

What parts of the design are still TBD?
