- Feature Name: java_components_and_boundaries
- Start Date: 2026-10-30


# Summary
[summary]: #summary

This RFC defines the small set of Java components we use in Uyuni, what each one is responsible for, and what each one must not do.

That is all it does. It is a vocabulary and a set of rules for **new code and code we touch anyway**, so that contributors and reviewers have a shared reference.

## Non-goals

To keep the discussion focused, this RFC explicitly does **not**:

- move, rename or reorganize any package (`com.redhat.rhn`, `com.suse.*` or anything else)
- require refactoring any existing code
- set a migration plan or timeline
- deprecate Managers or Factories as a whole
- define modules, containers or build changes

Where code lives is a separate discussion. The rules below apply regardless of the package a class is in.


# Motivation
[motivation]: #motivation

The same responsibility is implemented today in different places: a business rule can live in an XMLRPC handler, a Spark controller, a Manager, a Factory or a Service. None of these is wrong on its own. The problem is that there is no agreed answer to "where does this go?", so every contributor and every reviewer answers it differently.

Some consequences:

- business logic is duplicated between XMLRPC handlers and Web UI controllers, and the two drift apart
- data access and business rules are mixed in the same method, so neither can be tested alone
- static methods everywhere make components impossible to replace in tests
- code review spends time on the same structural debates in every PR

## Expected outcome

- A contributor can tell where a piece of logic belongs without asking.
- A reviewer can point to a rule instead of a personal preference.
- The XMLRPC API and the Web UI share the same business logic instead of copying it.
- New code is testable without a database or a running Salt master.


# Detailed design
[design]: #detailed-design

## The components

We use six kinds of component. No more are introduced by this RFC.

| Component | One-line responsibility |
|-----------|-------------------------|
| **Entry point** | Receives an external trigger, translates it into a Service call, translates the result back |
| **Service** | Implements a use case: business rules, validation, orchestration |
| **Repository** | Reads and writes persistent data |
| **Entity** | Maps one database row; holds persistent state and relationships |
| **DTO** | Carries data across a boundary; holds no behavior |
| **Mapper** | Converts between representations (Entity ↔ DTO, DTO ↔ protocol structure) |

Existing **Managers** and **Factories** are covered in [Legacy components](#legacy-components).

### Entry point

*Based on:* the Controllers of the "Interface Adapters" layer in [The Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) (Martin): *"a set of adapters that convert data from the format most convenient for the use cases and entities, to the format most convenient for some external agency such as the Database or the Web"*. "Entry point" is our own umbrella term for the adapters on the calling side.

Anything that starts work from outside the business logic:

- Web UI controllers (Spark)
- XMLRPC handlers (`*Handler`)
- Taskomatic jobs
- Salt event / reactor handlers
- message queue consumers and similar

**Responsibilities**
- extract and parse input (request params, XMLRPC arguments, job parameters, event payload)
- check input *shape*: required parameters present, correct types, parseable formats
- resolve the caller (logged-in user, org) and pass it to the Service
- delegate the work to one or more Services
- translate the result into the protocol's format (JSON, XMLRPC struct, job result)
- translate Service exceptions into protocol errors (HTTP status, XMLRPC fault)

**Must not**
- contain business rules. For example, checking that a channel has no child channels before deleting it belongs in the Service, not the Handler.
- call Repositories, Factories or Hibernate directly
- modify Entities
- call an Entry point of a different protocol. For example, a Web UI Controller must not call an XMLRPC Handler. Shared logic belongs in a Service.

### Service

*Based on:* [Service Layer](https://martinfowler.com/eaaCatalog/serviceLayer.html) (Fowler, *Patterns of Enterprise Application Architecture*, 2002).

**Responsibilities**
- implement one use case per public method. For example, subscribing a system to a channel is one method, and scheduling a patch installation is another.
- enforce business rules and *business* validation (permissions, state, invariants)
- orchestrate Repositories, other Services and external systems (Salt, Cobbler, ...)
- throw exceptions that describe what went wrong (for example, `ChannelHasChildrenException`). Each Entry point decides how to report them to its caller: HTTP error, XMLRPC fault, job failure.

**Must not**
- know which protocol called it: no `Request`/`Response` from Spark, no XMLRPC types, no HTTP status codes, no JSON
- build queries or call Hibernate sessions directly; that goes through a Repository
- be static. A Service is an instance that gets its dependencies through the constructor

A Service **may** call another Service. If a workflow is reused by several Services, it becomes its own Service. We do not introduce separate Facade, Helper or Orchestrator components for this.

### Repository

*Based on:* [Repository](https://martinfowler.com/eaaCatalog/repository.html) (Fowler, PoEAA) and the Repository of Evans' *Domain-Driven Design* (2003). Evans defines one Repository per aggregate; ours is the looser "one Entity or a closely related group".

**Responsibilities**
- CRUD and queries for one Entity or a closely related group of Entities
- hide the persistence technology (HQL, named queries, native SQL, `datasource` mode queries)

**Must not**
- contain business rules. For example, deciding whether a user may see a channel based on their org admin role belongs in the Service, not in the lookup query.
- call Services
- return DTOs built for a specific screen or API. Query projections into simple DTOs are fine.

### Entity

*Based on:* the [Jakarta Persistence entity](https://jakarta.ee/learn/docs/jakartaee-tutorial/current/persist/persistence-intro/persistence-intro.html). This is not the DDD Entity, which also carries domain behavior.

**Responsibilities**
- map a database row: fields, relationships, Hibernate annotations
- keep its own state consistent: simple invariants on its own fields (e.g. `setName` rejects null when the column is `NOT NULL`)

**Must not**
- call Services, Repositories, Factories or any static lookup
- open sessions, run queries, or trigger side effects (Salt calls, events, emails)
- know about other users of the data (UI, API)

### DTO

*Based on:* [Data Transfer Object](https://martinfowler.com/eaaCatalog/dataTransferObject.html) (Fowler, PoEAA). Fowler's DTO exists to reduce remote calls; we use the broader Java meaning of a data carrier across any boundary (see [LocalDTO](https://martinfowler.com/bliki/LocalDTO.html)).

**Responsibilities**
- carry data across a boundary: Service ↔ Entry point, Repository projection, external API payload

**Must not**
- contain behavior beyond trivial accessors, `equals`/`hashCode`/`toString`, or derived read-only values computed from its own fields
- call any other component, or any static method that does I/O or lookups
- be a Hibernate-managed Entity

### Mapper

*Based on:* [Mapper](https://martinfowler.com/eaaCatalog/mapper.html) (Fowler, PoEAA). Not to be confused with Fowler's *Data Mapper* (object ↔ database), which is Hibernate's job.

**Responsibilities**
- convert one representation into another, as a pure function

**Must not**
- query, persist, or call Services
- make business decisions. If the conversion depends on a rule, the Service decides and passes the result in


## Dependency rules

The arrows show who may call whom. This is the classic layering of [Service Layer](https://martinfowler.com/eaaCatalog/serviceLayer.html) (Fowler, PoEAA): presentation calls the service layer, which calls the data source layer, never the other way round.

```
Entry point  ──►  Service  ──►  Repository  ──►  Entity
                     │
                     └──►  other Service / external system (Salt, ...)
```

## Where validation goes

Most "where does this go" debates are about validation. The rule:

| Kind | Example | Where |
|------|---------|-------|
| Input shape | parameter missing, not a number, bad date format | Entry point |
| Business rule | user lacks permission, channel has children, system not entitled | Service |
| Single-field invariant | name not null, label max length | Service, so the caller gets a clear error. The Entity and DB schema also enforce it as a safety net. |

A business rule is checked once, in the Service, so every Entry point gets it.

## Legacy components

**Manager** and **Factory** classes stay. Nobody has to rewrite them. For new code and code we touch anyway:

- **Do not add new business logic to a Manager.** Put it in a Service. The Service may call the existing Manager.
- **Do not add new code to a Factory.** New data access goes in a Repository. The Repository may call the existing Factory.
- When you change a Manager/Factory method anyway and it mixes data access with business rules, splitting it is encouraged but not required.

Once their logic has moved to Services and Repositories, Managers and Factories can be deprecated. That is not part of this RFC.

## Exceptions

These are conventions, not laws. Exceptions are fine when there is a good reason for them.


# Drawbacks
[drawbacks]: #drawbacks

- New code will sometimes look different from the legacy code next to it.
- A use case that used to be one Handler method becomes a Handler method plus a Service method.


# Alternatives
[alternatives]: #alternatives

- **Do nothing.** Every PR has to answer "where does this go?" from scratch, logic keeps getting duplicated, and code keeps crossing component boundaries.


# Unresolved questions
[unresolved]: #unresolved-questions

*Design Patterns* (Gamma et al., 1994) recommends to "program to an interface, not an implementation" ([explained by Gamma](https://www.artima.com/articles/design-principles-from-design-patterns)): callers depend on what a component offers, not on how it is implemented. Martin's [Dependency Inversion Principle](https://web.archive.org/web/20110714224327/http://www.objectmentor.com/resources/articles/dip.pdf) states the same: high-level code should not depend on low-level details; both should depend on abstractions.

1. **When to enforce interfaces.** Interfaces bring the following benefits:
   - separate the contract from the implementation. Callers depend only on the contract, never on the implementation, which keeps boundaries and responsibilities respected
   - a second implementation can be added later without touching the callers, as `SaltApi` already shows
   - tests can replace the implementation with a mock or a simple fake ([Test Double](https://martinfowler.com/bliki/TestDouble.html))
   - logging, caching or transactions can be added by wrapping the interface, without changing the implementation ([Decorator](https://refactoring.guru/design-patterns/decorator))

   The cost is one extra file per component, even when there is only one implementation.

   Suggestion: do it at least for every new Service and Repository. Not necessarily because we expect them to have multiple implementations, but because of their role:
   - a **Service** is the contract between every Entry point and the business logic. Many callers depend on it, and it is what tests replace and what gets wrapped for transactions or logging.
   - a **Repository** is the boundary to the persistence technology. Its callers should not know how data is stored; this is Fowler's [Separated Interface](https://martinfowler.com/eaaCatalog/separatedInterface.html) (PoEAA): *"a client that needs the dependency to the interface can be completely unaware of the implementation"*.
