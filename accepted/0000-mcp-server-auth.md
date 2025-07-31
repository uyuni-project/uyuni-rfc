# Authenticating Uyuni MCP server through the Uyuni API

# Summary
[summary]: #summary

This RFC presents two architectural patterns for securely connecting the Uyuni MCP server to the Uyuni API. The core challenge is bridging an OAuth-based system with Uyuni's existing credential-based API. This document details two viable solutions: a "Service Account with Internal Authorization" pattern that requires no changes to Uyuni's codebase, and an "OAuth Token Exchange" pattern that offers tighter integration at the cost of modifying Uyuni. Both designs aim to enable secure, user-delegated actions from an LLM-based agent.

# Motivation
[motivation]: #motivation

To enable LLM-powered MCP agents to interface with Uyuni, a secure method for delegating user actions is required. Storing end-user credentials directly on the MCP server is not a viable or secure option, so this RFC defines architectural patterns that respect Uyuni's security model while enabling this new type of interaction.

The expected outcome is a secure and auditable system where the MCP server can reliably execute actions against the Uyuni API. All actions will be authorized based on the end-user's actual permissions (RBAC) within Uyuni, providing a safe and effective bridge between conversational AI and the traditional API workflow.

# Detailed design
[design]: #detailed-design

To solve the authentication and authorization challenge, this RFC presents two distinct patterns. The choice between them depends on the trade-off between implementation effort and the desired level of security and auditing granularity.

---

### Pattern 1: Service Account with Internal Authorization

**Architecture:**

1.  **User Authentication (OAuth)**: The end-user authenticates with the MCP proxy ecosystem via a standard OAuth 2.0 flow. The LLM agent receives a JWT access token representing the user.

2.  **MCP Server Authentication**:
    - A single, non-human **Service Account** (e.g., `mcp-service-account`) is created in Uyuni with a powerful role that includes the permissions necessary to execute any tool within the Uyuni MCP server.
    - An API key is generated for this account and stored securely in the MCP server's environment. The MCP server uses this key to authenticate itself to the Uyuni API.

3.  **Authorization Flow**:
    1. The MCP server receives a tool call from the LLM, including the user's JWT.
    2. After validating the JWT, the MCP server extracts the user's identity (e.g., `user:alice`).
    3. **The MCP server performs a pre-flight authorization check.** It makes a read-only call to the Uyuni API (`access.list_permissions`) to verify that `alice` has the necessary permissions for the requested action on the target resource.
    4. Only if the permission check passes, the MCP server executes the command using its own privileged Service Account API key.

4.  **Auditing**: The MCP server **must** maintain its own immutable audit log that maps every executed command back to the originating user's identity from the JWT. This is critical, as Uyuni's native logs will only show the `mcp-service-account` as the actor.

---

### Pattern 2: OAuth Token Exchange

This pattern is the "gold standard" for security and auditing. It involves modifying Uyuni's code to make it a first-class participant in the OAuth 2.0 flow.

**Architecture:**

1.  **User Authentication (OAuth)**: Same as Pattern 1. The LLM agent receives a JWT access token for the user.

2.  **Custom Authentication Backend in Uyuni**:
    - A new API endpoint is added to Uyuni that is capable of validating JWTs issued by the external Authorization Server.

3.  **Authorization Flow (Token Exchange)**:
    1. The MCP server receives the tool call with the user's JWT.
    2. The MCP server sends the user's JWT to the new API endpoint on Uyuni.
    3. The Uyuni backend validates the JWT. If valid, it creates a **short-lived, temporary Uyuni API session** specifically for that user (e.g., `alice`).
    4. Uyuni returns this temporary session token to the MCP server.

4.  **Execution**: The MCP server uses this temporary, user-specific session token to make the API call. It holds no long-term credentials or privileges itself.

5.  **Auditing**: All actions are natively logged and audited in Uyuni against the actual user (`alice`), as the execution is performed with their temporary session. No secondary audit log is required for tracing actions.

# Drawbacks
[drawbacks]: #drawbacks

**Of Pattern 1 (Service Account):**
- **Indirect Auditing**: Native Uyuni logs are insufficient for user-level auditing. Administrators must correlate logs from the MCP server.
- **Privileged Account Risk**: The Service Account is highly privileged. A compromise of the MCP server or its secret store would be high-impact.
- **Performance Overhead**: The pre-flight authorization check adds an extra API call and thus latency to every action.
- **Implementation Complexity**: The authorization logic must be carefully implemented and maintained within the MCP server.

**Of Pattern 2 (Token Exchange):**
- **Extra Development Effort**: Requires significant changes to the core Uyuni product to support JWT validation and session exchange.
- **Increased Coupling**: Tightly couples Uyuni's authentication mechanism with the external Authorization Server.
- **Complex Setup**: The initial configuration of the trust relationship between Uyuni and the Authorization Server is more complex.

# Alternatives
[alternatives]: #alternatives

The only other significant alternative is to **store user credentials** (e.g., username/password) directly on the MCP server. This is a well-known security anti-pattern that should be avoided. It makes the MCP server a high-value target for credential theft. This alternative is explicitly **not recommended**.

# Unresolved questions
[unresolved]: #unresolved-questions

- For Pattern 1, what is the minimal set of permissions the `mcp-service-account` requires?
- For Pattern 2, what is the scope of the required modifications to Uyuni's core?
- What is the recommended secure process for the initial setup and rotation of the Service Account's API key in Pattern 1?
- For Pattern 1, what is the specification for the MCP server's audit log, and how will it be protected and exposed for administrative review?
