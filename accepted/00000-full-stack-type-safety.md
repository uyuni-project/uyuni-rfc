- Feature Name: Full Stack Type Safety
- Start Date: 2021-05-28

# Summary
[summary]: #summary

Add type safety to frontend and backend communications to achieve type safety across the whole project.

# Motivation
[motivation]: #motivation

With the wrapup of the Typescript migration, we now have type safety both in the backend project by itself and in the frontend project by itself. What we do not have is type safety in the communications between the two. If an entity changes on the backend but the corresponding code is not updated on the frontend, the regression can go unnoticed unless this specific interaction is covered by an E2E test. Adding type checks to backend and frontend communications will catch these regressions. In addition, shared types will also help write sturdier frontend code since it will alert the developer to possible nullable values and other similar edge cases which might otherwise go unnoticed.  

# Detailed design
[design]: #detailed-design

In the order of increased difficulty but also increased payoff, there's two possible approaches. The easier but more laborious option is to generate a set of exposed types and manually annotate requests.  

```ts
// Type definitions generated from the backend project...
namespace Space {
  export interface Foo {
    goodExample: boolean;
  }
}
```

```ts
// ...can be used to manually annotate expected types in the frontend project.
- const result = await Network.get("/rhn/manager/getFoo");
+ const result = await Network.get<Space.Foo>("/rhn/manager/getFoo");

// 'goodExample' is correctly identified as a boolean value
if (result.goodExample) {
  // ...
}

// Throws an error whereas previously this passed silently
if (result.badExample) {
  //       ^^^^^^^^^^
  // Property 'badExample' does not exist on type 'Foo'
}
```

The general workflow for using this approach would be to add a step to the backend build process which generates a type declaration file as shown above. There are existing tools which provide this functionality, I've considered evaluating them out of scope for the time being. The generated file can be added to the frontend project scope and the type definitions can be used accordingly where needed. This change can be adopted gradually over time.  

An alternative option would be to try to automatically annotate requests. It's unclear whether this is realistically implementable, but I've included it for pink dreams' and completeness sake.  

This relies on a [suggested Typescript feature](https://github.com/microsoft/TypeScript/issues/41160) that's not approved and might not be approved. In addition to the Typescript limitation, it would also be necessary to find a way to map request URLs to corresponding types which might not be technically realistic.  

```ts
// Types generated similar to the above option
namespace Space {
  export interface Foo { /* ... */ }
  export interface Bar { /* ... */ }
}
```

```ts
// Generated overload definitions
function get(url: "/rhn/manager/getFoo"): Promise<Space.Foo>;
function get(url: "/rhn/manager/${^[a-zA-Z0-9]*$}/getBar"): Promise<Space.Bar>;
function get(url: string) {
  // Implementation omitted
}
```

```ts
// 'result' is automatically inferred as 'Space.Bar'
const result = await Network.get("/rhn/manager/1234/getBar");
```

# Drawbacks
[drawbacks]: #drawbacks

Given how Java handles `null`, it may be infeasible to try export types that realistically reflect the expected entity state. Optionally chaining every field in a nested object and adding fallbacks where we know values to actually be present would quickly outweigh benefits we might otherwise get from type safety simply by adding a lot of overhead and additional complexity. This is mostly a tooling question and I don't know what the current state of the art is in this regard.    

Depending on the volume of types that will be exposed, the time to export those types as well as the time to then build the frontend project with them may be too large. Depending on the tooling, hot reload performance may take a considerable hit, slowing down development. Likewise, if those types are in scope for the IDE autocomplete, past some large number of types it might start slowing down opening the project, using autocomplete, etc. I don't have an estimate for what order of magnitude would become problematic.  

If type annotation can't be automated, finding the correct types manually would become a chore, even if adopted gradually. Manual type annotations are likewise susceptible to rot over time especially in cases where instead of an interface changing, a new one is used entirely. If the types overlap initially, the change may go unnoticed until some later time when they diverge.  

Implementing automatic annotations based on overloads or similar may be infeasible for performance reasons, this is not something I have seen another project implement at this scale before, in large part because Typescript added some of the tools to make this possible only fairly recently.  

Type names will need to be consistent and uniquely identifiable. Depending on the tooling we use this may pose considerable challenges. Based on the use case, similar entity names crop up in many different contexts and disambiguating them may be difficult or downright impossible without renaming one or the other if the tooling doesn't specifically consider this. Scoping and other similar solutions can help here, but this is largely implementation specific.  

Implementing type safety across the full stack can make quick prototyping harder. Depending on the implementation and the developer's workflow, having the frontend build error out on backend changes may hamper fast iterative development. This can be overcome by manually annotating the type to be `any` on the frontend side while prototyping.  

# Alternatives
[alternatives]: #alternatives

The easiest alternative is to keep things as they are and fix any related bugs as they come up. Depending on the implementation, the effort to reach full stack type safety can be considerable, and it may be easier to reactively fix bugs rather than proactively try to avoid them.  

It is also possible to manually write the types we expect to receive and use them today. Those are highly susceptible to rot though, since a developer making a change in the backend code may not be aware of these annotations in the frontend or might not find them.  

# Unresolved questions
[unresolved]: #unresolved-questions

It is unknown whether any currently existing tool for type generation matches all of the requirements outlined in this document.  

The automated type annotation proposal relies on a [suggested Typescript feature](https://github.com/microsoft/TypeScript/issues/41160) that's currently being discussed, hasn't been approved and might not be approved. Without this feature, automated annotations may not be feasible even if the URL to type mapping is possible. Whether this feature will ever be implemented and in what timeframe is unknown.  

The performance impact on the IDE, the change in build times, and other similar overheads are all unknown for a project of this size.  
