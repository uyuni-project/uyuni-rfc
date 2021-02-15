- Feature Name: Enhance visibility of connected Configuration State Channels
- Start Date: 2020-12-17
- RFC PR:

# Summary
[summary]: #summary

Provide visibility of **inherited** Configuration State Channels connections at a System Details level. The reverse information as well should be provided by giving visibility of those systems they are connected (directly or by **inheritance**) to a certain Configuration State Channel at a Channel Details level.

*Note: everything discussed in this RFC applies to Salt clients only. Traditional clients do not inherit Configuration State Channels.*

# Motivation
[motivation]: #motivation

## Why are we doing this?

By definition a Configuration State Channel is a pool of configuration salt states resources. Once a channel of these types is created, it is possible to subscribe systems to it in order to deploy the content of that channel to them. Alternatively, channels can also be assigned to System Groups and/or to Organizations.

Collecting the possibilities as described above, we can see that:
- a channel can be assigned directly to a system `channel --> system`
- a channel can be assigned to a system group `channel --> group`
- a channel can be assigned to an organization `channel --> org`

On top of this it has to be considered that by design a System is part of an Organization `system --> org`, and it can also be part of a System Group `system --> group`.

The final channel assignements result, from a system perspective, can be:
1. `system --> channel`
2. `system --> group --> channel`
3. `system --> org --> channel`

That said, in the current implementation there is no way to figure out which channels are assigned to a system other than the directly assigned ones (1.).

And here it is the problem this RFC is trying to describe to solve: apart from the direct assignment, the System inherits channels (thus the content) from the Organization it is part of, and the same goes for the System Groups he is part of, but this inheritance is not visible in the Web UI nor in the XML RPC API.

Note: in addition to what has been described so far, for what concerns the Configuration State Channels case, behind all the Salt States collected from the channels, there are also a bunch of default Salt States, the ones the server has to supply during the registration of a salt minion client. Those are not *assigned* in any way because they are not part of any Configuration State Channel, they do just exists due to the logic implementation of a client registration using Salt. In the end, those are not visible Salt States anyway, and the System will be affected by them during the registration, so from the System perspective an additional source of Salt States could be defined as directly assigned: a non-manageable source behaving as a Configuration State Channel that will be named *registration-states*.

Adding the latter to the picture:
1. `system --> channel`
2. `system --> group --> channel`
3. `system --> org --> channel`
4. `system --> registration-states`


## What are the use cases?

A complete but simple use case:

1. create an Organization O1
2. create a System Group G1
3. onboard a System S1 as a Salt client in the Organization O1 and System Group G1
4. create a Configuration State Channel C1 assigned to Organization O1
5. create a Configuration State Channel C2 assigned to System Group G1
6. create a Configuration State Channel C3 assigned directly to System S1
7. go to System Detail > States > Configuration Channels > System
8. the C3 channel is listed as an assignment to S1
9. there is no info about C1 nor C2 channels, but because of step 4. 5. in reality S1 will receive not only C3 but also C1 and C2 as inheritance of its own setup, being part of O1 and G1
10. the reverse logic is valid as well, there is no information about systems assigned to channels C1 or C2 in Configuration > Channels > Channel Overview > Systems because. No system is directly assigned to them, but S1 inherits them.

Adding complexity to the scenario described above:

1. create another System Group G2
2. create another System Group G3
3. create a Configuration State Channel C4 at System group G2
4. create a Configuration State Channel C5 at System Group G2
5. create a Configuration State Channel C6 at System Group G3
6. check the following system groups channels assignments:
  - G1 --> C2
  - G2 --> C4
  - G2 --> C5
  - G3 --> C6
7. add the System S1 to System Groups G2 and G3
8. go to System Detail > States > Configuration Channels > System
9. still only the C3 channel is listed as an assignment to S1, but in reality S1 is inheriting C2 from G1, C4 and C5 from G2 and C6 from G3


## What is the expected outcome?

A transparent representation of all Configuration State Channels assigned to a system from all the possible sources: direct and inherited (from System Groups, from Organization and from the system registration).

# Detailed design
[design]: #detailed-design
<!-- TODO -->
This is the bulk of the RFC. Explain the design in enough detail for somebody familiar with the product to understand, and for somebody familiar with the internals to implement.

This section should cover architecture aspects and the rationale behind disruptive technical decisions (when applicable), as well as corner-cases and warnings. Whenever the new feature creates new user interactions, this section should include examples of how the feature will be used.

# Drawbacks
[drawbacks]: #drawbacks
<!-- TODO -->
Why should we **not** do this?

  * obscure corner cases
  * will it impact performance?
  * what other parts of the product will be affected?
  * will the solution be hard to maintain in the future?

# Alternatives
[alternatives]: #alternatives
<!-- TODO -->
- What other designs/options have been considered?
- What is the impact of not doing this?

# Unresolved questions
[unresolved]: #unresolved-questions
<!-- TODO -->
- What are the unknowns?
- What can happen if Murphy's law holds true?
