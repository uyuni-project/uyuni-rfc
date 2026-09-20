- Feature Name: explore_genui_mcp
- Start Date: 2026-09-15

Summary

The "AI Assistant RFC" (LINK_TO_AI_ASSISTANT_RFC) defines an AI assistant integrated into the Uyuni Web UI. Among other things, it proposes a set of predefined presentation types, such as tables, charts, comparison cards, forms, and operation previews. Each presentation type has a validated schema and maps to a React component in the Web UI.

This RFC explores how those presentation components could be selected and composed when the result of an AI interaction is not known in advance.

The main use case is an AI assistant combining the outputs of multiple tools. These tools may belong to the Uyuni MCP Server or, in the future, to different MCP servers. While individual data structures and presentation components may be known, the combination of results produced for a particular user request may not be.

One approach we want to explore is allowing the assistant to select and compose a UI from a finite catalog of predefined components. This RFC refers to this approach as a Controlled Component Catalog.

The goal is not to generate arbitrary frontend code. The available components, their schemas, and their implementation remain defined by Uyuni. The area being explored is how the assistant decides which components to use and how to compose them for a given result.

This RFC does not propose adding Generative UI (GenUI) to Uyuni. Its purpose is to explore this problem, compare possible approaches, and identify the questions that need to be answered before deciding whether this capability would be useful.

Motivation

The AI Assistant RFC defines presentation types that map structured data to predefined React components in the Uyuni Web UI.

For known workflows, the presentation can also be known in advance. For example, a specific operation may always use the same presentation component.

Other interactions may be less predictable. A user request can cause the assistant to call several tools and combine their results. The individual tools and UI components are known, but the final combination may depend on the request and on the data returned by those tools.

For example, an assistant could combine information about systems, available patches, and pending actions. Depending on the request, representing the result may require a table, a summary, a chart, or a composition of several presentation components.

The same problem becomes more apparent if the assistant can interact with multiple MCP servers. For example, it could combine Uyuni system information with monitoring data or information from an issue tracker.

The question explored by this RFC is therefore not how to generate arbitrary user interfaces, but:

How should an AI assistant select and compose a predefined set of presentation components when the final combination of data is not known in advance?

Proposed Exploration

We propose exploring a Controlled Component Catalog.

The Web UI would provide a finite set of components that the assistant is allowed to use. These components could initially correspond to the presentation types defined by the AI Assistant RFC.

For example:

- text or markdown
- tables
- charts
- comparison cards
- forms
- operation previews

Each component would have a defined schema describing the data it accepts.

Instead of generating HTML, JavaScript, or React code, the assistant would produce a structured description indicating which component or components should be used and the data required by each one.

Conceptually:

User request
     |
     v
AI Assistant
     |
     +--> MCP tool A
     |
     +--> MCP tool B
     |
     +--> MCP tool C
     |
     v
Combined result
     |
     v
Select / compose presentation components
     |
     v
AG-UI
     |
     v
Uyuni Web UI
     |
     v
Predefined React components

The Web UI remains responsible for rendering the components.

This keeps the set of possible UI elements controlled by Uyuni while allowing the assistant to decide how to use them for results that were not explicitly designed as a predefined workflow.

Levels of Control

There are several possible levels of control that could be explored.

Deterministic mapping

The simplest approach is to map known tool results or workflows to predefined presentation components.

For example:

list systems -> table
compare systems -> comparison
historical metric -> chart

In this case, the LLM does not decide how the result is presented.

This approach could provide a baseline and cover predictable use cases.

LLM component selection

A second approach would allow the assistant to choose a component from the available catalog.

For example, given some structured data, the assistant could decide whether it is better represented as a table or a chart.

The output would still need to follow one of the schemas defined by the Web UI.

LLM component composition

A further step would allow the assistant to compose several components.

For example, a response could contain:

summary
+
chart
+
table
+
operation preview

This may be useful when the assistant combines the results of several tools and there is no single predefined presentation for the complete result.

These approaches are not necessarily mutually exclusive. Deterministic mappings could be used for known workflows, while model-based selection or composition could be explored for less predictable cases.

Example

Consider a request such as:

«Show me the systems with pending critical patches and compare their recent CPU usage.»

The assistant might need to:

1. retrieve systems with pending patches,
2. filter or classify the relevant patches,
3. retrieve monitoring information,
4. combine the results.

The resulting UI could contain:

Summary

5 systems have pending critical patches.

[Systems table]

[CPU usage chart]

The table and chart would be predefined components from the catalog. The assistant would decide how to compose them based on the results of the tools.

The initial experiments do not require multiple MCP servers. The same idea can be tested by combining several tools from the Uyuni MCP Server.

Multi-server scenarios can be considered later if they become relevant to the AI Assistant architecture.

MCP Apps

MCP Apps was also considered as part of this exploration.

MCP Apps is an extension to MCP that allows an MCP server to provide interactive UI resources and associate them with its tools. A compatible host can render those resources as interactive user interfaces.

This is useful when a tool has a known UI that should be provided together with the MCP server.

However, this RFC focuses on a different problem: selecting and composing presentation components after the assistant has combined the results of multiple tools.

In that situation, the final presentation does not necessarily belong to a single tool or MCP server.

For example:

Uyuni tool
     \
      \
Monitoring tool ---> Assistant ---> Combined presentation
      /
     /
Another tool

For this reason, MCP Apps is not the approach selected for this exploration.

The architecture described in the AI Assistant RFC, where presentation components belong to the Uyuni Web UI and presentation data is transported through AG-UI, provides a more direct starting point for investigating this use case.

This does not exclude MCP Apps for other use cases where an MCP server should provide a tool-specific interactive UI.

AG-UI

The AI Assistant RFC proposes AG-UI as the protocol between the AI assistant and the Web UI.

This RFC assumes that architecture.

The Controlled Component Catalog does not require a new transport protocol. The result of the component selection or composition could be transported using the AG-UI mechanisms already defined by the AI Assistant architecture.

The exploration should therefore focus on:

- how presentation components are described,
- how the assistant selects them,
- how several components can be composed,
- how their inputs are validated,
- and what happens when the generated presentation is invalid or unsupported.

Fallback

The system should always have a simple fallback representation.

If the assistant cannot produce a valid presentation using the available components, the result should still be representable as text or markdown.

This allows the graphical representation to remain an optional enhancement rather than a requirement for completing an interaction.

Questions to Explore

The exploration should try to answer the following questions:

- Which presentation components are useful enough to include in an initial catalog?
- Which cases should use deterministic mappings?
- When, if ever, should the LLM select the presentation component?
- Should the LLM be allowed to compose multiple components?
- How should component inputs be validated?
- How should invalid component selections or data be handled?
- How should the system fall back to text or markdown?
- How much additional latency and token usage does component selection introduce?
- How deterministic are the generated presentations for equivalent requests?
- How easy is it to test the resulting UI?
- Does the approach provide useful representations for combinations of tools that were not explicitly designed in advance?

Initial Experiments

The exploration can start with a small number of components and use cases.

A possible first experiment could use:

- text
- table
- chart

The experiment could compare three approaches:

1. predefined presentation,
2. LLM selection from the catalog,
3. LLM composition of components.

The same input data and user requests could be used across the three approaches.

Possible measurements include:

- valid component selection rate,
- valid schema generation rate,
- consistency across repeated requests,
- latency,
- token usage,
- fallback rate.

The goal of these experiments is not to prove that one approach is better in general, but to understand the trade-offs and determine whether model-driven presentation provides value for Uyuni use cases.

Drawbacks

Introducing model-driven presentation also introduces additional complexity.

Possible drawbacks include:

- less deterministic UI behavior,
- additional testing requirements,
- additional model calls or token usage depending on the implementation,
- failures where the selected component does not match the data,
- additional validation requirements,
- increased complexity compared with predefined workflows.

These trade-offs should be measured during the exploration rather than assumed.

Alternatives

Predefined UI only

Uyuni could define the presentation for every supported AI workflow.

This provides deterministic behavior and is appropriate when workflows and data structures are known in advance.

It may be sufficient for many AI Assistant interactions.

The limitation appears when the assistant combines tools in ways that were not explicitly designed as a workflow.

Text or Markdown

Another option is to keep unpredictable results as text or markdown.

This is simple and provides a natural fallback.

The purpose of this RFC is partly to determine whether graphical composition provides enough additional value to justify the extra complexity.

MCP Apps

MCP Apps can provide interactive UIs associated with MCP tools.

As discussed above, this is a good fit when the UI belongs to a particular MCP server or tool.

It is not the approach selected for this exploration because the use case considered here is the composition of results from multiple tools by the assistant.

Scope

This RFC explores:

- a finite catalog of predefined presentation components,
- deterministic component selection,
- LLM-based component selection,
- composition of several components,
- validation and fallback mechanisms,
- simple experiments to compare these approaches.

It does not propose:

- generating arbitrary React, JavaScript, or HTML,
- replacing existing Uyuni interfaces,
- making all AI Assistant responses graphical,
- adding MCP Apps support to Uyuni,
- allowing arbitrary external components to execute inside the Uyuni Web UI,
- committing to a production implementation.

Expected Outcome

The expected outcome of this RFC is an experimental implementation and enough evidence to answer:

1. whether model-driven selection of presentation components is useful,
2. whether component composition provides value beyond predefined presentations,
3. what level of control is appropriate,
4. what validation and fallback mechanisms are required,
5. and whether the approach should be considered for a future Uyuni implementation.

A production implementation, if any, should be proposed separately based on the results of this exploration.
