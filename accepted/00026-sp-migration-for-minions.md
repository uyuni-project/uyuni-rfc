- Feature Name: SP Migration for Salt Clients
- Start Date: 2016-10-10
- RFC PR: [#42](https://github.com/SUSE/susemanager-rfc/pull/42)

# Summary
[summary]: #summary

The Service Pack migration (SP migration) feature is currently supported only
for traditionally managed systems, we need to make it work with Salt clients as
well.

# Motivation
[motivation]: #motivation

The SP migration feature includes a UI as well as support in the API. Both are
based on a call to `zypper dist-upgrade` (or `zypper dup`) which is an option of
`zypper` that is currently not implemented in the [`zypper` Salt module]
(https://docs.saltstack.com/en/latest/ref/modules/all/salt.modules.zypper.html).
This is the main reason why the feature was not yet implemented for Salt
clients.

# Detailed design
[design]: #detailed-design

These are the general steps of a SP migration action that we need to implement:

1. Change the channel assignments to the channels that are mandatory for the
selected target products (+ optional channels as selected in the UI or via API)
2. Perform the actual `zypper dup` command (with optional `--dry-run`)
3. In case of a dry run revert the changed channel assignments afterwards

## Changing the channel assigments

Changing the channel assignments needs to happen on the server first. From there
the changes can be propagated to the minion in the usual way right before the
actual `zypper dup` is executed. We usually use a `require` on
`state.apply channels` to achieve that when for instance a patch is being
installed.

If a migration is scheduled for later execution, channel assignments should not
be changed before the actual schedule date. This can be handled by using a
custom Salt event to trigger the respective code on the server when the schedule
date and time has come. Remember that scheduling currently happens
**on the minion** so what will actually be scheduled when performing a SP
migration is a call to `event.fire_master` or `event.send`.

The structure of this event could look roughly like this, but it can be refined
by implementors as needed:

- `tag`: `manager/trigger/sp-migration`
- `data`: `{"action_id": "345"}`

The server side code would react on such an event with the following actions:

1. Look up the action details in the DB (use `action_id` from event data)
2. Change the channel assignments as required for the action
3. Execute the `zypper dup` via an asynchronous call to `state.apply` requiring
the channel changes to be populated first

## Calling `zypper dup`

The actual call to `zypper dup` will be done using the [`zypper` Salt module]
(https://docs.saltstack.com/en/latest/ref/modules/all/salt.modules.zypper.html).
This module can be called from a state making sure that channel assignments were
updated correctly (via `require`), so the actual call to Salt will be using the
`state.apply` module function.

The `zypper` module needs to be extended in order to offer the `dist-upgrade`
functionality. It is important that at least the parameters are available that
we are making use of, which are the following:

- `--from`: Restrict upgrade to specified repositories (only SLE 11)
- `--no-allow-vendor-change`: Do not allow vendor change during `dup` (SLE 12)
- `--dry-run`: Test the upgrade, do not actually upgrade

In case of success as well as error it is important that we get a good result
message even when calling the module from within a `state.apply`.

## Reverting channel assignments after dry run

This should be rather straight forward and can be implemented in
`JobReturnEventMessageAction.java`: The action details include the actual
channel changes that were done before the migration
(use `actionDetails.getChannelTasks()`). We need to do exactly the reverse
actions for each of those and save the changes to the database.

## Solver testcases for debugging
[solver-testcase]: ##solver-testcase

Every SP migration should create a solver testcase on the client to be used for
debugging in case something goes wrong. This will [in the future]
(https://trello.com/c/Lo46CVKQ) automatically be done with every regular call to
`zypper dup`.

Only in case of a dry run we will need to issue a separate call to generate the
solver testcase. This should be done implicitly in the Salt module
implementation by calling the `dup` command with `--debug-solver` before doing
the actual dry run.

We further need to verify that those testcases are included with
`supportconfig`, but it should already be the case.

# Drawbacks
[drawbacks]: #drawbacks

Using a custom salt event to trigger SP migrations server side will not work in
case tomcat is disconnected from the Salt event stream for some reason. In this
case the server will not actually see the event and the migration will never
start. I hope in the future there will be an improved reconnection mechanism so
that it is less likely that tomcat is actually disconnected from the Salt event
stream websocket.

# Alternatives
[alternatives]: #alternatives

What other designs have been considered? What is the impact of not doing this?

# Unresolved questions
[unresolved]: #unresolved-questions

What parts of the design are still TBD?
