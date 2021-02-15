- Feature Name: minion_selective_action_blocking
- Start Date: 2020-01-21
- RFC PR: (leave this empty)

# Unimplemented note

This RFC was not ultimately implemented. It is still archived here for historical purposes.


# Summary
[summary]: #summary

The goal is to selectively block certain action types from being executed on a Salt minion.

# Motivation
[motivation]: #motivation

Main use cases:
* Prevent certain action types when a product is installed on a minion, e.g. when a minion is a CaaSP node some actions shouldn't be allowed.
* Feature parity with traditional clients. System locking is available for traditional clients but no such functionality exists for Salt minions.

Usability:
* Salt has a blackout mechanism. This is used for the first version of CaaSP support but it's not flexible enough for Uyuni's use case. Uyuni makes heavy use of `state.apply` to execute actions. Salt blackout allows whitelisting which modules are allowed during blackout. In the case of Uyuni, whitelisting `state.apply` means allowing basically all actions. Additionally the user experience of using Salt blackout is not great, the user can schedule any actions from the UI/API but then gets an error message at execution time that the action is not allowed by Salt.


# Detailed design
[design]: #detailed-design

Traditional clients can be locked by the user. When locked, only certain action types are allowed. Actions that change the state of a system are blocked (package install, upgrade, apply highstate, etc) while read-only actions are allowed (hardware refresh, package profile refresh, etc). A notable exception is remote command execution. In order to be consistent with traditional clients this will be allowed on Salt minions.

The same should be possible for Salt minions. However, in the case of Salt minions, additional flexibility is needed to allow blocking some actions depending on the the products installed on the minion. This is needed to accommodate CaaSP and maybe other clustering products in the future.

To prevent the user from accidentally executing forbidden actions, the selective blocking must work both at the level of the Uyuni UI/XML-RPC API and at the level of the Salt command line.

## Salt level selective action blocking

The Salt blackout mechanism works by defining a special pillar called `minion_blackout` to tell the minion that it must reject all Salt remote executions. Exceptions can be configured using the `minion_blackout_whitelist` pillar. This accepts a list of Salt functions that are allowed during blackout, e.g. `test.ping`, `state.apply`, etc.

However, in Uyuni there are multiple actions that use `state.appply` under the hood. Some actions can change the state of the system while others are read-only but they all use `state.apply`. If `minion_blackout_whitelist` is used to allow `state.apply` then all actions that use this function are allowed.

The blackout mechanism must be enhanced to allow a more fine grained filtering. One approach would be to check the metadata that can be attached to a Salt call. 

A metadata whitelist would be defined. If the Salt call contains metadata that matches the whitelisted metadata then the call would be allowed. 

```yaml
minion_blackout: True
minion_blackout_metadata_whitelist:
    minion-action-type:
    - packages.refresh_list
    - hardware.refresh_list
```

## Uyuni level selective action blocking

For traditional clients the action types that are allowed when a system is locked are configured in the db. The configuration is global and applies to all clients indiscriminately.

In the case of Salt minions, the same approach will be used. The action types that are allowed when a system is locked will be stored in the db.

Additionally, in order to make the approach more flexible and to accommodate CaaSP a new object called a "locking profile" will be introduced.

The locking profile will contain a list of permitted actions. A profile can be reused across multiple minions. A minion will have only one locking profile assigned when locked. 

The locking profile will be provided by application code. It won't be stored in the db. Based on the installed products or any other arbitrary criteria defined in code Uyuni will apply a locking profile. The profile will be applied automatically when the software profile is refreshed (either as a result of registration or when triggered at a later time).

The locked/unlocked state will be stored in the db in the table `rhnServerLock` just like for traditional clients. If the system is locked but there's no suitable locking profile found in code then the global default from the db will be applied (just like for traditional clients).

## UI and XML-RPC API selective blocking

If a system is locked the UI must check if a certain action is blocked and hide/disable the corresponding UI elements. E.g. if package remove is not allowed then the install button must be disabled in the tab Software -> List

## Implementation phases

The implementation can be split in several phases:

1. Enhance Salt blackout to check metadata
2. Feature parity with traditional clients - use global locking configuration that's currently defined in table `rhnActionTypes`
3. Enhance db schema to add locking profiles
4. Disable UI elements and API calls depending depending on action type when a minion is locked

# Drawbacks
[drawbacks]: #drawbacks

In some cases it's not fined grained enough. Some actions might be forbidden only in certain cases. E.g. in the case of CaaSP, package operations are allowed as long as they don't impact the CaaSP packages.

Such cases need a different solution that could be complementary to system locking, e.g. package locking.


# Alternatives
[alternatives]: #alternatives

## Salt blackout

This approach will be used for the initial version of CaaSP support. While simple this is not fine grained enough for Uyuni because it's only possible to whitelist Salt functions and Uyuni can use the same function (`state.apply`) for multiple actions.

# Unresolved questions
[unresolved]: #unresolved-questions

What parts of the design are still TBD?
