- Feature Name: schedule_recurring_actions
- Start Date: (2018-11-21)
- RFC PR: #81

# Summary
[summary]: #summary

Allow scheduling recurring highstate / selected states for minions /
minion groups / organizations.

Traditional clients are out of scope here. 

# Motivation
[motivation]: #motivation

Customer asked for this feature. Related issue
https://github.com/SUSE/spacewalk/issues/6009

Another reason: other configuration systems (puppet) have recurring
state application in the core. Salt is missing it (not considering the
minion-centric `schedule` module).

# Detailed design

## UI
### Create schedule
Currently, user can fire a state(s) / highstate application (either
immediate, or delayed) from these UI screens:

* System detail -> States
* System group detail -> States
* Organization detail -> States

The aim here is to allow users to enhance these screens with schedule
definition.

If a System/Group/Organization has any existing schedules, they should
be listed in this UI too.

### List schedules
- Via System/Group/Organization detail screen (see above). Only
  displays schedules affecting current entity.
- Via a new page with aggregation of all schedules visible to the user
(new menu item under "Schedule -> Recurring actions").

### Edit schedules
(later iteration)
Allow changing recurrence and `active`, `skipNext` and `testMode` flags.
This is a prerequisite for the `active` and `skipNext` flags.
Note: recurrence can be change also from the 'Admin -> Task Schedules'
screen.

### Delete schedule
(Same as the "List schedules" scenario)
- Via System/Group/Organization detail screen (see above).
- Via a new page with aggregation of all schedules visible to the user
("Schedule -> Recurring actions").

## XMLRPC
Methods for:
* create/delete schedule (MVP), edit schedule (later iteration, this
  is a prerequisite for the `active` and `skipNext` flags)
* list schedules
* list schedules by System/Group/Organization `ID`

## Backend
The CRUD operations above control state of `TaskoSchedule` instances
(`rhnTaskoSchedule` table). Important attributes:
- `cron_expr` defines the recurrence of the action
- `data` a map with the following entries:
  - `targetType` - enumeration: either `minion` or `group` or
    `organization`
  - `targetId` - ID of target entity (minion/group/organization)
  - `states` - enumeration determining whether only highstate or
    assigned states should be applied. There are 2 possible scenarios:
    1. applying highstate
    2. applying states that an entity has assigned **at the time of
       execution**
  - `testMode` - `true/false` - whether the state (or highstate)
    application is run in the test mode
  - `active` flag - if false -> job is ignored
  - `skipNext` flag - if true && `active` -> next job run is ignored
  - optionally `creatorId` - the ID of user who created the
    schedule. This id can be set on created
    `AppliStatesAction.schedulerUser`.

Taskomatic boilerplate classes must be implemented for this usecase:
`Bunch`, `Template`, `Task`.

New Taskomatic job `RecurringStateApplyJob`. This Job is trigerred
according to its schedule. It instantiates `ApplyStatesAction` based
on the `states` above and `ServerActions` based on the `targetType`
and `targetId` (this can vary on each run (adding/removing `Server`s
from/to Group etc.)). Targets that have still pending execution from
the last schedule run are not skipped. The action is now ready to be
executed by `MinionActionExecutor`.

## Permissions
Required roles for schedule CRUD:

```
|--------------|-------------------------------------------------|
| Target       | Required role                                   |
|--------------|-------------------------------------------------|
| System       | Access to system (Query `is_available_to_user`) |
| Group        | Group admin                                     |
| Organization | Org admin                                       |
|--------------|-------------------------------------------------|
```

## Further questions:
### Handling backpressure
**still open question**
What if schedule is kicking in, but there are still some
`serveraction`s in pending state?

A: At the time of materializing, the previous runs would be checked
(how?). If there are `ServerActions` that are still pending,
corresponding `Server`s could be skipped in the scheduled run
(`ServerAction`s would not be materialized).

### Load spreading
Do we want to support spreading actions execution (in the
Group/Organization case) between the schedules?

A1: At the time of writing this RFC, there is an ongoing effort to bring
batching in the async calls. When this gets merged, no explicit load spreading
will be necessary.

RFC: https://github.com/saltstack/salt/blob/develop/rfcs/0002-netapi-async-batch.md

PR: https://github.com/saltstack/salt/pull/50546

A2: Solution outline if the PR in A1 doesn't get merged:
Quartz implementation doesn't support the `H` ("hashed")
character in the schedule, only precise executions at given
time. Emulating this would be possible via randomizing scheduling
action execution between the time of the cron schedule and its next
execution (this time interval can be computed using
e.g. `CronExpression.getNextValidTimeAfter` in Quartz.
Another problem with this would be a need for multiple `Action`s
creation, each containing a subset of all concerned minions that would
run the action in the same point in time.

### Handling failed actions
A: They should be scheduled normally on the next run. Moreover, a
notification should be created to inform the user about the failed
action.

### Defining highstate recurrence using an Activation Key
This could be achieved via a System group as follows:
- admin creates a group (called e.g. "Regular Highstate systems")
- they create an Acivation KEy, that would assign newly registered
systems to group above
- they schedule periodic highstate application for this group, with the
recurrence of their choice

# Alternatives

## 1. General solution for recurring actions
Probably discarded: too complex for getting small benefits.

This way would extend the current `Action` scheduling mechanism, so
that an `Action` could be associated with a taskomatic schedule
(`rhnTaskoSchedule` table) with non-`null` `cron_expr` (currently we
use taskomatic schedule with `cron_expr == null` to schedule one-shot
`Action` runs).

Extending this mechanism would be more complicated than the minimal
implementation, but all `Action`s could benefit from this.
**Question**: Is this true? Do recurring `Action`s (except
`ApplyStatesAction`) make sense? The single action execution is mostly
tied to data specified by user (CVE list, packages list). Recurring
execution would make no sense for these cases (e.g. applying patch for
the same CVE periodically makes no sense).

### UI / XMLRPC
Mostly same as the previous case.

### Backend
`Action` object needs to be extended with a `recurrence`
attribute (CRON format) populated from the UI/API when scheduling
actions (apply highstate button).

`recurence` would be part of `paramList` when calling
`tasko.scheduleRuns` XMLRPC method of taskomatic, where a
`rhnTaskoSchedule` row would be created with the given CRON
expression (when `recurrence` is present).

When the scheduler kicks in, it runs `MinionActionExecutor`, which
calls salt.

After actions complete, `JobReturnEventMessageAction` handles the
`Action` state (setting `COMPLETED`/`FAILED`).

After this, the `Action` needs to be "cloned" (same parameters, new
`ID`, `QUEUED` state) and the `rhnTaskoSchedule` needs to be updated
so that it points to the new `Action` `ID`.

### Advantages
General solution, re-usability for other actions. Re-using
`MinionActionExecutor`.

## 2. Use minion-side schedule state module
Discarded: in the past SUMA used this state module to schedule actions
on minions, but this was re-implemented because of its drawbacks:
* no control of number of parallel actions on the minions
* when minion is disconnected from the master, it's impossible to "unschedule"
  the action
