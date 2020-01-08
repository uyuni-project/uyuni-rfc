- Feature Name: modular_codebase
- Start Date: 2.1.2020
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

This proposal is about improving the code quality, long term maintainablilty and testabilty of Uyuni by
creating a set of guidelines based on best practices and retroactively applying them to the existing codebase.


# Motivation
[motivation]: #motivation

The codebase of Uyuni has become increasingly hard to understand and maintain. The majority of time is spent on fixing bugs, debugging, fiddling with complex test setups and simply trying to understand what existing code even does (this includes new code). Even the most knowlegable people on the team don't always know how Uyuni would behave in a certain scenario or how its supposed to behave. Those problems are symptoms of the same underlying issue which is only adding new features without any big picture or architecture in mind and the complexity and lack of quality resulting from that. This creates a feedback loop where too much busywork leaves not enough time for proper reseach and development leading to rushed features leading to more bugs, complexity and busywork. This proposal is an attempt at breaking this loop by investing into a maintainable codebase that requires less busywork and allows for more time on the things that matter.

# Detailed design
[design]: #detailed-design

The core of this proposal will be modulerizing our codebase driven by the following aspects:

- testabilty (make it easy to test invidual components of Uyuni in isolation without a full multivm setup running.)
- understandability (make the APIs and Components clear so it is possible to understand how things are supposed to work without the need to look at its implementation and all its interactions.)
- reusablity (decouple components as much as possible to the point where they can be easily reused as a library or run standalone.)

The goal of those aspects is to cut down on busywork and make working with the code more productive.

The proposal is structured in a way that each area can be tackled indiviually and the refractoring can be done gradually in multiple repeatable steps.
After each step the code should be in a compilable state with all tests still passing.


# Preparation 

- pick one of the areas like: salt, filesystem, database, task scheduling, different topics of buisness logic like cve audit, etc.
- The first step is to gather all the requirements Uyuni has towards this area. This means finding all operations Uyuni currently needs from i.e salt. From this set of operations we create an interface.
- Next step is to implement this interface with the existing code we already have for those operations. This can be done by moving code or delegating in case moving requires a lot of extra refactorings.
Note: only put methods in the interface that are actually used outside the implementation of the interface. Everything else will be private and will be considered an implementation detail.
- Then we need to point exising use sites of those operations to use this interface.
- At this point we should have a pretty good overview of what set of operations we have and we have centeralized them in an interface that is now used. We should be in a state where everything works as before.


## Refinement 

- review the interface by consolidation of all the operations, dropping possible duplicates or deprecated functionality, merge similar methods etc.
- Refine the interface with more precise types, consistent method names, signatures and error handling. (in case of salt there are some wildcard methods that let you do anything which leads to people putting fragile parsing logic inside business logic)
- Make batch operations the default and single target a special case. This is so implementations can be done with scalability in mind.
- Merge related existing implementations across the codebase to implement the interface
- Make sure the interface does not imply a specific implementation (i.e don't reference salt if all you do is gathering information from a system.)
- Refactor other components to take an implementation of this interface as an argument instead of reaching into global space.
- write new and reuse existing tests for the interface
- move interface with related datatypes and implementations into package with fitting name for the component.

### Interface guidelines?

- It should be focused on a particular area and not mix different topics.
- It should be minimal meaning only the minimal set of methods needed by our business logic.
- It should give immediately useful information and not burden the user to do much additional work to get to the useful information. (i.e don't return plain json and let business logic parse it).
- it shoud be precise in its types and minimize invalid usage.
- Don't be scared to define multiple interface to separate areas properly and let them build ontop of each other.


## Bootstrapping

Bootstrapping is about creating our instances of our different "services" and assembling them to then pass on into our business logic.
The assembly should happen at the very start and then everything below that will only get things passed down but not instanciate any services themselves.
The Start in this case is kind of multiple places tomcat and taskomatic are differnt processes and have there own entry points so both need to have some bootstrapping code.
In tomcat the situation is maybe a little bit more complicated since our business logic lives below filters which are instanciated by tomcat logic based on xml configuration.

- One way to go could be looking into programatic initialisation and registration of filters.
- Use some limited shared global state just to pass the initial instances between entry points.
- in the worst case duplicating instances per filter so spark and xmlrpc would not share the same instances.



## Minimal example

This ia a minimal example extracting most of the interactions with salt into an interface. Its not complete
as it lacks more refinement i.e getting rid of JsonElement in result or splitting it up into more topical interface i.e having libvirt interaction in its own interface. But it should give a general idea of how this rfc looks applied to our code.

[salt-branch](https://github.com/uyuni-project/uyuni/compare/salt-interface?expand=1)

# Drawbacks
[drawbacks]: #drawbacks

- Refactorings in areas that are not well understood by anyone may be hard and lead to short term breakage.
- measures will have to be found to ensure established interfaces will continue to be respected.


# Unresolved questions
[unresolved]: #unresolved-questions
