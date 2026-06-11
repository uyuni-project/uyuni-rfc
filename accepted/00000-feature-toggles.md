- Feature Name: feature_toggles
- Start Date: 2026-06-08
- RFC PR:

# Summary
[summary]: #summary

This RFC proposes a configurable **Feature Toggle** system for Uyuni that allows
satellite administrators to selectively disable UI features and their associated
backend endpoints globally. Features are controlled via a single
`java.disabled_namespaces` configuration key in `rhn.conf` that lists RBAC
namespace prefixes to disable. The system leverages the existing RBAC
infrastructure for enforcement: the `DisabledNamespaces` utility checks each
namespace at the existing RBAC gate points (`Access.aclAuthorizedFor()`,
`UserManager.verifyRoleBasedAccess()`), and the `FeatureFilter` servlet filter
blocks URLs matching disabled features. The system is managed via an
administrative UI page that persists changes through
`ConfigureSatelliteCommand`.

# Motivation
[motivation]: #motivation

Uyuni supports a broad and growing set of capabilities — content lifecycle
management, system provisioning, auditing, hub federation, Ansible automation,
virtual host management, and many more. Not all deployments need or want every
feature:

- **SLE-only sites** have no use for patch management on non-SUSE systems and
  may want to hide the "Patches" menu entirely.
- **Minimal-footprint deployments** (e.g., edge gateways) never use Kickstart or
  PTF (Program Temporary Fix) workflows and prefer a cleaner UI.
- **Multi-tenant or peripheral servers** acting as Uyuni Hub clients should not
  expose Hub Configuration or Subscription Matching menus locally.
- **Security-hardened environments** want to reduce attack surface by completely
  disabling endpoints rather than merely hiding menu items.

Today, Uyuni already has *ad-hoc* toggles (`java.disable_remote_commands_from_ui`,
`java.disable_supportdata_upload`), but they are scattered, inconsistently
enforced, and lack a unified management surface. Administrators must edit
`rhn.conf` manually, restart services, and hope the change took effect.

A **unified Feature Toggle system** gives operators explicit, reversible control
over which features are exposed. It reduces UI clutter, lowers the attack
surface, and makes per-deployment customization a first-class concern rather than
a configuration hack.

# Detailed design
[design]: #detailed-design

## Overview

The system uses a **single configuration key** `java.disabled_namespaces` in
`rhn.conf` that holds a comma-separated list of RBAC namespace prefixes. When a
namespace prefix is listed, **all** namespaces that match or start with that
prefix are disabled. For example, `java.disabled_namespaces = cm,patches`
disables `cm`, `cm.image.list`, `cm.build`, `patches`, and `patches.security`.

Enforcement happens in **three layers** that reuse the existing RBAC
infrastructure:

1. **URL blocking** (`FeatureFilter` servlet filter) — intercepts every request
   to a disabled feature's URL patterns and returns HTTP 403 before any
   controller or handler runs.
2. **Menu visibility** (`MenuTree.java` via `isUserAuthorizedFor()`) — calls
   `Access.aclAuthorizedFor()` which now checks `DisabledNamespaces.isDisabled()`
   **before** the SAT_ADMIN bypass. Disabled items are hidden from the sidebar.
3. **API/backend blocking** (`UserManager.verifyRoleBasedAccess()`) — checks
   `DisabledNamespaces.isDisabled()` **before** the SAT_ADMIN bypass. API calls
   to disabled features are rejected.

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Request                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. FeatureFilter (servlet filter)                               │
│     • Checks request path against disabled feature URL patterns   │
│     • If match → HTTP 403 (before auth / controller)            │
│     • Excludes login, logout, and admin toggle page             │
└────────────────────────┬────────────────────────────────────────┘
                         │ (passthrough)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. RBAC Gate Points (reused from existing RBAC)                │
│     • Access.aclAuthorizedFor() → checks DisabledNamespaces     │
│     • UserManager.verifyRoleBasedAccess() → checks              │
│       DisabledNamespaces                                        │
│     • Both run BEFORE the SAT_ADMIN bypass                      │
│     • Disabled features are blocked for ALL users               │
└────────────────────────┬────────────────────────────────────────┘
                         │ (rendered page / API response)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Admin UI (FeatureTogglesAction)                              │
│     • Satellite admin toggles checkboxes → form POST              │
│     • ConfigureSatelliteCommand → writes java.disabled_namespaces │
│     • Updates /etc/rhn/rhn.conf in the running container         │
└─────────────────────────────────────────────────────────────────┘
```

## Feature → RBAC Namespace Mapping

A `FeatureNamespace` enum maps each feature to its RBAC namespace prefix:

| Feature | Namespace Prefix | Label |
|---------|------------------|-------|
| `AUTOINSTALLATION` | `systems.autoinstallation` | Autoinstallation / Kickstart |
| `IMAGES` | `cm` | Images |
| `SYSTEM_SET_MANAGER` | `systems.ssm` | System Set Manager |
| `CONTENT_MANAGEMENT` | `clm` | Content Management |
| `CONFIGURATION` | `config` | Configuration |
| `AUDIT` | `audit` | Audit |
| `PATCHES` | `patches` | Patches |
| `VIRTUAL_HOST_MANAGERS` | `systems.vhms` | Virtual Host Managers |
| `HUB` | `admin.hub` | Hub |
| `ANSIBLE` | `systems.ansible` | Ansible |
| `PAID_CHANNELS` | `software.paid_channels` | Paid Software Channels |
| `PRODUCT_MIGRATION` | `systems.software.migration` | Product Migration |
| `PTF` | `systems.software.ptf` | PTF |
| `SUBSCRIPTION_MATCHING` | `clm.subscription_matching` | Subscription Matching |
| `REMOTE_COMMANDS` | `salt.remote_commands` | Remote Commands |
| `SUPPORT` | `systems.details.support` | Support Data Upload |

Two legacy toggles (`REMOTE_COMMANDS` and `SUPPORT`) existed before this RFC
and are included in the enum for unified management.

## DisabledNamespaces utility

`com.redhat.rhn.domain.access.DisabledNamespaces` is a thread-safe utility class:

- Parses `java.disabled_namespaces` config (comma-separated list)
- Caches the parsed `Set<String>` in a `volatile` field for performance
- `isDisabled(String namespace)` — returns `true` if the namespace exactly
  matches or starts with any disabled prefix
- `refresh()` — re-parses the config after runtime changes

## RBAC integration points

### 1. `Access.aclAuthorizedFor()` (UI/menu visibility)

In `com.redhat.rhn.common.security.acl.Access`, the `aclAuthorizedFor()` method
checks `DisabledNamespaces.isDisabled(params[0])` **after** the null check but
**before** the SAT_ADMIN bypass:

```java
if (DisabledNamespaces.isDisabled(params[0])) {
    return false;
}
```

This means disabled features are **completely hidden** from the menu, even for
system administrators.

### 2. `UserManager.verifyRoleBasedAccess()` (API/backend)

In `com.redhat.rhn.manager.user.UserManager`, the `verifyRoleBasedAccess()`
method checks `DisabledNamespaces.isDisabled(namespace)` **after** the null check
but **before** the SAT_ADMIN bypass:

```java
if (DisabledNamespaces.isDisabled(namespace)) {
    return false;
}
```

This means API calls (XML-RPC, HTTP API) to disabled features are **rejected**,
even for system administrators.

### 3. `FeatureFilter` servlet filter (URL blocking)

`com.redhat.rhn.frontend.servlets.FeatureFilter` is a standard Jakarta servlet
filter mapped in `web.xml` to `*.do`, `*.jsp`, `/manager/*`, `/ajax/*`,
`/saltboot/*`. It iterates over `FeatureNamespace.values()` and checks
`feature.isDisabled()` (which delegates to `DisabledNamespaces.isDisabled()`).
If the request path matches any disabled feature's URL patterns, it returns
HTTP 403. Excluded paths (`/newlogin/`, `/Logout.do`, `/manager/login`,
`/admin/config/FeatureToggles.do`) are always allowed so admins can always log
in and reach the toggle page.

## Menu visibility

The `MenuTree` sidebar builder uses `isUserAuthorizedFor(user, namespace)` which
calls `Access.aclAuthorizedFor()`. Since that method now checks
`DisabledNamespaces`, disabled features are automatically hidden from the menu.

The old `checkAcl(user, "not is(java.disable_*)")` calls have been removed from
`MenuTree.java` and the nav XML files (`system_detail.xml`, `ssm.xml`,
`activation_key.xml`). The menu visibility is now controlled purely by the RBAC
`isUserAuthorizedFor()` mechanism.

## Admin UI and persistence

A dedicated admin page at `/rhn/admin/config/FeatureToggles.do` lets satellite
admins view and modify feature states.

- **`featuretoggles.jsp`** — JSP form with a checkbox per `FeatureNamespace` enum
  value. Labels are rendered from the enum's `getLabel()`. The form uses a single
  hidden `disabledNamespaces` field that holds the comma-separated list of
  disabled namespace prefixes.
- **`FeatureTogglesAction`** — Struts action extending `BaseConfigAction`. On
  POST, it collects checked checkboxes, builds the comma-separated string, and
  writes it via `ConfigureSatelliteCommand.updateString()`.
- **Form property** — The `featureTogglesForm` DynaActionForm has a single
  `disabledNamespaces` String property (replacing the previous 16 boolean
  properties).
- **Persistence** — `ConfigureSatelliteCommand` writes to `rhn.conf` through the
  existing `rhn-config-satellite.pl` infrastructure.
- **Security** — The action requires `user_role(satellite_admin)` ACL.

## Testing

- **`FeatureFilterTest.java`** — JUnit 5 test covering 9 scenarios:
  - Passthrough when no features are disabled
  - 403 when a feature URL matches a disabled namespace
  - Excluded paths (login, logout, admin toggle page) always pass through
  - Multiple feature patterns are all checked

# Drawbacks
[drawbacks]: #drawbacks

1. **Testing combinatorics** — With 16 toggles, the state space is 2¹⁶ = 65,536
   combinations. Manual QA of every combination is intractable. We rely on
   the fact that each toggle is independent (no toggle depends on another) and
   that the filter, menu, and API layers are tested individually.

2. **RBAC namespace coverage** — The feature toggle system only works for
   features that have corresponding RBAC namespaces. If a new feature is added
   without a namespace, it cannot be toggled. This requires discipline when
   adding new RBAC namespaces.

3. **SAT_ADMIN bypass change** — Placing the disabled check **before** the
   SAT_ADMIN bypass changes the traditional behavior where system admins could
   access everything. This is intentional (disabled features are truly disabled)
   but may surprise operators who expect admin access to override all
   restrictions.

4. **Toggle accumulation** — Each new feature added to Uyuni should ideally get
   a toggle. Without enforcement (e.g., a CI check), toggles will gradually
   become incomplete as new routes and menus are added.

5. **No per-organization granularity** — The `java.disabled_namespaces` config
   is global. A large multi-org deployment cannot enable Kickstart for Org A
   while disabling it for Org B.

# Alternatives
[alternatives]: #alternatives

1. **Standalone feature toggle system** (original approach)
   - *Pros*: Independent of RBAC rollout state, works immediately without
     waiting for RBAC namespace coverage
   - *Cons*: Duplicates RBAC logic, doesn't cover APIs, more maintenance
     burden, inconsistent with project architecture
   - *Verdict*: Rejected — the reviewer pointed out the significant overlap
     with existing RBAC infrastructure

2. **Positive-config naming** (`java.enable_*` instead of `java.disable_*`)
   - *Pros*: More intuitive
   - *Cons*: Inconsistent with existing toggles; would require migration
   - *Verdict*: Rejected — we use `java.disabled_namespaces` which is
     semantically clear

3. **Database-backed toggles** (new `suseFeatureToggles` table)
   - *Pros*: Easier to query programmatically; could support per-org granularity
   - *Cons*: Adds schema migration overhead; `rhn.conf` is simpler
   - *Verdict*: Rejected — `rhn.conf` is the established admin-config pattern

4. **Environment variables** (`UYUNI_DISABLE_IMAGES=1`)
   - *Pros*: Works well for containerized deployments
   - *Cons*: Requires restart; no admin UI
   - *Verdict*: Rejected — restart requirement is unacceptable

5. **Feature branches** (Git branch per feature)
   - *Pros*: Clean separation
   - *Cons*: Does not solve runtime configuration
   - *Verdict*: Rejected — branching is a development practice, not runtime config

# Unresolved questions
[unresolved]: #unresolved-questions

1. **Toggle expiration** — Should feature toggles have a sunset date? A toggle
   for a brand-new feature might be removed once the feature is stable.

2. **Audit logging** — Should changes to `java.disabled_namespaces` be logged
   in the audit trail (who changed what, when)?

3. **Toggle dependencies** — Some features logically depend on others. For
   example, disabling "Patches" should arguably also disable "System Set
   Manager → Patches". Currently, toggles are independent.

4. **Per-organization granularity** — Should toggles be global or per-org?
   A future extension could add `org_id` to the toggle state.

5. **API exposure** — Should the toggle state be readable via the XML-RPC or
   HTTP APIs so that external automation can query which features are enabled?
