- Feature Name: java_modernization_service_package_organization
- Start Date: 2026-06-30


# Summary
[summary]: #summary

This RFC a proposes package organization patterns and component responsibilities for Uyuni's Java codebase, focusing primarily on **how presentation layers (Web UI and XMLRPC) interact with business logic (Services)** and where different components should live.

The proposal aims to improve code clarity, testability, and maintainability by defining:
- Clear boundaries between presentation (web/xmlrpc), business logic (services), and data access
- Component responsibilities and naming conventions
- Service flow patterns - how requests flow from controllers/handlers through services to data access


# Motivation
[motivation]: #motivation

Uyuni started as a fork of Spacewalk in 2008. Throughout its evolution, development has primarily been driven by the needs of MLM, focusing on stability and long-term maintainability so it can deliver reliable enterprise solutions.

For nearly two decades of development, numerous contributors naturally brought different ideas, coding styles and organizational concepts into the project.
During this time, the Java language, common software design practices, and architectural conventions also evolved.
Without a documented set of project guidelines, it is only natural that similar problems have been solved in different ways.

## Current State

As a consequence of the project's evolution across the years, the codebase today follows a hybrid organization, combining layer-centric and domain-centric approaches across different namespaces.

```
com.redhat.rhn/
├── domain/                        
│   ├── channel/                   # Channel entities, factories, exceptions
│   ├── server/                    # Server entities, factories, exceptions, manager
│   ├── dto/                       # Data transfer objects
│   └── ...                        # All organized by functional domain
│
├── manager/                       
│   ├── channel/ChannelManager     # Business logic for channels
│   ├── system/SystemManager       # Business logic for systems
│   └── ...                        # All organized by functional domain
│
└── frontend/xmlrpc/               # ~65 XMLRPC handlers
    ├── channel/ChannelHandler     # Public API organized by domain + business logic
    ├── system/SystemHandler    
    └── ...

com.suse.manager/
│
├── webui/                         # Web UI Layer
│   ├── controllers/               # ~129 files - Presentation layer
│   │   ├── admin/                 # Domain-organized within layer
│   │   ├── channels/              # Domain-organized within layer
│   │   ├── users/                 # Domain-organized within layer
│   │   └── MinionController.java  # Top-level controllers
│   │
│   └── services/                  # ~45 files - Business logic layer
│       ├── iface/                 # Service interfaces (e.g., SaltApi)
│       ├── impl/                  # Service implementations (e.g., SaltService)
│       └── ...                    # Classes with concrete business logic
│
├── xmlrpc/                        # XMLRPC API Layer (3 handlers)
│   ├── admin/AdminPaygHandler     # SUSE-specific XMLRPC extensions
│   └── ...                        
│
├── api/                           # API Infrastructure
│   └── ReadOnly.java, ApiType.java, etc.
│
└── model/                         # ~58 files - DTOs/Models layer + Factory + 
    │                              # Entities + Business Logic
    ├── attestation/
    ├── kubernetes/
    └── ...                        # Organized by domain
```

The two namespaces reflect different eras: `com.redhat.rhn` is purely domain-centric, while `com.suse.manager` mixes technical/layer-based packages (`webui`, `model`, `api`, `xmlrpc`, ...) with domain-based ones (`attestation`, `kubernetes`, `hub`, `maintenance`). Then layer packages can also be organized by domain internally e.g. `model/attestation`, `model/kubernetes`.

However, package organization is not the only issue.
We use a variety of architectural components and design patterns that provide familiar ways of structuring code.
And each of these concepts is typically associated with a well-defined set of responsibilities, but those are not always applied consistently.

The sections below break down some of these concrete issues.

## Problems with Current Organization

### Package Structure Issues

**1. Inconsistent Organization Strategy**

We have **two competing organizational strategies** without clear guidelines on when to use each:

- **Legacy (com.redhat.rhn):** Pure domain-centric - everything organized by functional area
- **Modern (com.suse.manager):** Mixed approach - some packages are layers (webui, services, model), others are domains (attestation, kubernetes)

When creating new functionality, it's not immediately obvious where it should go:
- Should this be a new domain package like `com.suse.manager.myfeature.*` or should it go under an existing layer?
- Should business logic go in a Manager class, a Factory, or the new Service layer?
- Where do service interfaces belong - we have `webui.services.iface` but services aren't webui-specific!

**2. The service layer misnamed/misplaced**

`com.suse.manager.webui.services.*` classes read as webui-specific, but they aren't. Some XMLRPC handlers import them, and services like `SaltApi`/`SaltService` are shared infrastructure. The `webui` prefix draws an architectural boundary that doesn't exist.

**3. Presentation layers aren't cleanly separated from business logic**
We have two API technologies:
- **XMLRPC** (`com.redhat.rhn.frontend.xmlrpc` + `com.suse.manager.xmlrpc`) - Public programmatic API
- **Web UI** (`com.suse.manager.webui.controllers`) - Browser-based interface using Spark framework

Both should be **thin adapters**, used just for delegating to shared business logic, but:
- XMLRPC handlers (`*Handler` extending `BaseHandler`) often contain business logic directly
- WebUI controllers sometimes contain business logic instead of delegating to services
- Shared business logic exists in `webui.services` (misleading name) but isn't consistently used

### Class Responsibility Issues

**1. Overlapping patterns for business logic**

Business logic is spread across three patterns with no clear boundary between them:
- **Factories** (`domain.*.Factory`) - data access with business rules and validation mixed in
- **Managers** (`manager.*`, `com.suse.manager.*`) - business logic that also does data access
- **Services** (`webui.services.*`) - the modern layer, only partially adopted

The result is bloated, overlapping classes like `ChannelFactory` and `ChannelManager`, each holding **2500+ lines** with responsibilities that duplicate one another.

**2. Inconsistent interface/implementation separation**

- **Managers** - concrete classes of static methods, no interfaces, impossible to mock
- **Services** - some have `iface/impl` separation, applied inconsistently
- **Handlers** - no separation, tightly coupled to Manager/Factory implementations

Together these boundary problems make code harder to **test** (data access can't be exercised apart from business logic), **maintain** (a query change can ripple into business rules), **reuse** (logic is locked into specific classes and duplicated across Managers and Services), and **understand** (no single owner for a given responsibility).

## What is the expected outcome?

- **Clearer separation of concerns** - Each package has a single, well-defined purpose
- **Improved readability** – Consistent organization and naming convention makes it easier to navigate the codebase and understand the role of each component
- **Better testability** - Interfaces enable mocking, smaller scope objects are easier to test
- **Improved reusability** - Helpers are explicitly named and easy to identify as shared components
- **Clear layering** - Dependencies flow in one direction: api/spec -> implementation -> persistence
- **Gradual adoption** - Can be introduced incrementally without disrupting existing code
- **Long Term maintainability** - Clear architectural boundaries makes the code more predictable and easier to modify, extend, and refactor over time

# Detailed design
[design]: #detailed-design

This chapter proposes an organization that aims to fit the project's most common use cases. It is not intended to be a "one size fits all" solution, nor should it prevent exceptions when they are justified.

Instead, it provides a common starting point that we can discuss, refine, and adapt so it fits our needs. The goal is to establish a shared reference, that contributors can rely on when introducing new code, reworking old code or reviewing existing contributions.

## Concepts
Before diving into a proposal, we should define the concepts used throughout this chapter. While many of them are already familiar, it's important that we share the same understanding of what each one means, their responsibilities, boundaries and how they work together.

### Presentation Layer
**Web Controller** – Handles frontend requests, translates them into service calls. Thin adapter that extracts parameters, delegates to services, and formats responses for the web UI.

**XML-RPC Handler** – Exposes business functionality over XML-RPC. Also a thin adapter that extracts XMLRPC parameters, delegates to services, and formats responses as XMLRPC-compatible structures.

### Business Logic Layer
**Service (Interface/Specification)** – Defines the business operations (use cases) that the application provides, independent of any transport or persistence technology.

**Service (Implementation)** – Implements the application's business logic by coordinating domain objects, factories/repositories, and facades or other services.

**Manager** (Legacy) – Legacy component that encapsulates business logic, use case orchestration, data access. Some classes like `ChannelManager` or `SystemManager` expose static methods. These simplify the Manager usage but do make testing harder. **New code should use Service pattern instead. Existing Managers should gradually migrate logic to Services.**

### Data Access Layer

**Repository (Interface/Specification)** – Defines the persistence operations (CRUD and queries) available for an entity or aggregate, independent of the underlying persistence technology.

**Repository (Implementation)** – Implements the persistence operations using the chosen data access technology. In our case it would be primarily hibernate. But the bottom line is that it isolates persistence concerns from the business logic.

**Factory** (Legacy) – Component responsible for creating and initializing domain objects. It may contain logic directly related to object construction. This includes processes like validation, relationship initialization, assigning default values, etc. But in current codebase, factories sometimes include responsibilities beyond that, that include business logic or use case orchestration. In new code, these should be part of the Service.

### Domain Layer
**Entity (Model)** – Represents a business concept and its persistent state within the domain.

**DTO (Data Transfer Object)** – Carries data across architectural boundaries without containing business logic. Can be shared, specific to a presentation layer (like `webui` or `xmlrpc`), or part of a service contract (e.g. request/response DTOs), Depending on their scope.

### Utilities
**Mapper** – Converts data between different representations, such as DTOs, entities, and domain models. Can be shared or domain-specific.

**Facade (Interface/Specification)** – Defines reusable operations that encapsulate complex workflows supporting one or more service implementations.

**Facade (Implementation)** – Implements reusable workflows by coordinating multiple components behind a single interface. Facades may orchestrate technical or domain-specific operations that are not application use cases themselves, allowing services to remain focused on business use case orchestration


## Proposed Layered Package Structure

```
com.suse.manager/
│
├── api/                          # Presentation Layer (protocol adapters)
│   ├── webui/                    # Web UI Presentation Layer
│   │   └── <domain>/             # e.g., channel, system, user, if you have more than just the controller
│   │       ├── <Feature>Controller.java
│   │       ├── dto/              # Web-specific DTOs
│   │       └── mapper/           # Web-specific mappers
│   │
│   └── xmlrpc/                   # XMLRPC API Presentation Layer
│       └── <domain>/             # e.g., channel, system, user, if you have more than just the handler
│           ├── <Feature>Handler.java
│           ├── dto/              # XMLRPC-specific DTOs
│           └── mapper/           # XMLRPC-specific mappers 
│
├── service/                      # Business Logic Layer
│   ├── spec/                     # Service Contracts (Interfaces)
│   │   └── <domain>/
│   │       ├── <Feature>Service.java
│   │       └── dto/              # Domain-specific service DTOs
│   │           ├── <Name>Request.java
│   │           ├── <Name>Response.java
│   │
│   └── impl/                     # Service Implementations
│       └── <domain>/
│           ├── <Feature>ServiceImpl.java
│           └── <operation>/      # Implementation details, if necessary
│               ├── facades/
│               │   └── <Operation>Facade.java
│               ├── helpers/
│               │   └── <Feature>ValidationHelper.java
│               └── mappers/
│                   └── <Feature>Mapper.java
│
├── common/                       # Shared/Common Components
│   ├── dto/                      # Shared DTOs used across domains
│   │   └── <Common>.java
│   ├── mapper/                   # Shared mappers
│   │   └── <Common>Mapper.java
│   └── util/                     # Shared utilities (helpers, etc)
│
├── entity/                       # Domain Model Layer — target home for entities.
│   └── <Entity>.java             # Migrate here over time.
│
└── repository/                   # Data Access Layer
    ├── <Entity>Repository.java
    └── <Entity>RepositoryImpl.java
```


### Dependency Flow & Responsibility Breakdown

To better understand how these layers work together, let's follow two typical operations through the stack, at different complexity levels.

**Simple operation** — e.g. *"get all users"*, a single read:

```
ChannelController                            api/webui/channel/
    │ calls
    ▼
ChannelService          «interface»          service/spec/channel/
    ┆ served by
    ▼
ChannelServiceImpl                           service/impl/channel/
    │ calls
    ▼
ChannelRepository       «interface»          repository/
    ┆ served by
    ▼
ChannelRepositoryImpl
    │ loads
    ▼
Channel                 «entity»             entity/
    │ propagates back through the service to
    ▼
ChannelController                            maps it into the web response
```

The `Controller` receives the request and delegates it to the `Service`.
The `ChannelServiceImpl`, which holds the business logic, invokes the appropriate method on the `Repository`.
The `Repository` executes the query and returns the matches, which flow back up through the service to the `Controller`, which maps them into the response expected by the web UI.

For this kind of trivial operations, the involvement of service and repository are little more than pass-throughs and may look like they're adding unnecessarily complexity. 
The real value of this layering becomes obvious once an operation grows.   

Building on those basics, lets look at a more **complex operation** like *"update proxy configuration"*, involving processes like data acquisition, orchestration, validation, etc:

```
ProxyConfigurationHandler                          api/xmlrpc/proxy/configuration/
    │ receives ProxyConfigUpdateRequest            (DTO carrying the request data)
    ▼
ProxyConfigurationService      «interface»         service/spec/proxy/configuration/
    ┆ served by
    ▼
ProxyConfigurationServiceImpl                      service/impl/proxy/configuration/
    │ delegates the use case to
    ▼
ProxyConfigUpdateFacade        «interface»         service/impl/proxy/configuration/update/
    ┆ served by
    ▼
ProxyConfigUpdateFacadeImpl                        service/impl/proxy/configuration/update/
    │ coordinates single-responsibility helper classes with dedicated goals
    ├─► ProxyConfigUpdateAcquisitor                acquires the current config and related data
    ├─► ProxyConfigUpdateValidator                 validates the request and the acquired data
    ├─► ProxyConfigFileBuilder                     reuses a sibling facade to generate the config files
    ├─► ProxyConfigPillarWriter                    persists the pillar data
    └─► ProxyConfigSaltStateApplier                applies the Salt state
    │
    ▼ builds
ProxyConfigUpdateResponse                          service/spec/proxy/configuration/dto/
    │ propagates back through the service to
    ▼
ProxyConfigurationHandler                          formats the XML-RPC response
```

This time the entry point is an XML-RPC `Handler`, receives a `ProxyConfigUpdateRequest` dto but its job is exactly the same, it delegates straight to a `Service`.

The difference comes on how much work sits behind that call.
Updating a proxy configuration includes multiple things like: acquiring data, validation, reusing/invoking other existing services, persisting data and applying a Salt state.
So, specific goals for different concerns, boundaries, etc.
And, rather than pile all of that into `ProxyConfigurationServiceImpl`, we can split them into small, single-responsibility **helper** classes. Lets call them `steps`. And because each `step` has a narrow scope and single goal, it makes them really easy to read and to test.
`ProxyConfigurationServiceImpl` then can just delegate the call to `ProxyConfigUpdateFacade`, whose implementation job is then to coordinate the steps of this flow.

### Layer Responsibilities Summary

The table below summarizes what each layer holds, what it is responsible for, and what it should avoid:

| Layer | Contains | Responsibilities | Does NOT Contain |
|-------|----------|------------------|------------------|
| **api/** | `*Controller.java`, `*Handler.java`, presentation DTOs & mappers | Extract request params, delegate to services, format responses | Business logic, validation, data access |
| **service/** | `*Service.java` + request/response DTOs (`spec/`); `*ServiceImpl.java`, facades, helpers, mappers (`impl/`) | Define and implement business use cases: logic, orchestration, validation | Protocol knowledge (HTTP, XMLRPC), persistence details |
| **repository/** | `*Repository.java`, `*RepositoryImpl.java` | CRUD, queries, data access | Business logic, DTOs |
| **entity/** | `<Entity>.java` (`@Entity`) | Represent domain concepts and their persistent state and relationships | DTOs, service/business logic |
| **common/** | Shared DTOs, mappers, utilities | Provide cross-cutting shared components | Domain/business logic |

**NOTE**: `common/` is cross-cutting and may be used by any layer.


# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?

  * More classes
  * Increased complexity initially
  * Inconsistency during transition
  * Learning curve

# Alternatives
[alternatives]: #alternatives

The alternative is to keep the current domain-centric structure. The foreseen impact in the worst-case scenario is that technical debt continues to accumulate, the codebase remains hard to test, and responsibilities remain mixed.
  
# Unresolved questions
[unresolved]: #unresolved-questions

1. **Entity Migration timeline**
   - When should we move entities from `com.redhat.rhn.domain.*`?
   - Should this be done incrementally or in a single migration?

2. **Manager deprecation strategy**
   - Would a manager object become truly deprecated or would the class concept change? 
   - Would there still be room from proper Managers?
   - Maybe we could try making them become thin wrappers calling Services, until they eventually get deprecated

3. **Package Naming**
   - Is `spec/` the right name for service contracts, or would we stick to something that already exists like `services.iface/`?
   - Should we use `impl/` or `services.impl/`?
   - Is `common/` too generic? Some other name?
   - The proposed `api/` package collides with the existing `com.suse.manager.api` (API infrastructure such as `ReadOnly`, `ApiType`). Do we rename one, merge them, or pick a different name for the presentation layer?
   - Open to alternative suggestions that better communicate intent

4. **Concept Naming and Patterns**
   - Is "Facade" the right term for these internal orchestration classes? Maybe orchestrator? workflow?
   - Do these terms align with team understanding and existing conventions?
   - Do these conventions cover all our needs? 
