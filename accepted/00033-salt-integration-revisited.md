- Feature Name: salt-integration-revisited
- Start Date: 2017-03-01
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

This RFC is suggesting changes to the architecture of Salt integration in SUSE
Manager that should be done in order to improve the reliability and scalability
of the backend:

1. Actions are currently scheduled in the minions using [the `schedule` module
of Salt][schedule-module]. This causes problems with reliability as minions can
be down at the specified schedule time leading to actions not being executed at
all. Scalability can be another issue as actions being scheduled for many
minions might return results to the server at the same time. It would be better
to keep control over scheduled actions on the server instead. This would allow
us to implement batching or rate limiting of action executions as well as
support for configurable maintenance windows.
2. SUSE Manager is currently relying on a websocket connection to the event bus
of Salt in order to receive action results through job return events. This is
problematic as the websocket connection might be interrupted leading to the
server missing those events. Accumulating events can further cause the process
to run out of available memory as these events usually contain the complete
results of issued Salt calls. Instead we could make use of a
[master-side returner][master-job-cache] to write the action results directly
into the SUSE Manager database. This would even allow setups with multiple Salt
masters returning job results to the same database.

# Motivation
[motivation]: #motivation

The main benefits of the suggested changes are:

- We finally gain correct tracking of all action status, especially `PICKED_UP`.
This was not the case so far: an action that was scheduled for being executed
later would never show this status.
- We finally can implement reliable canceling of actions. This was not the case
so far: an action scheduled for a minion could not actually be canceled as long
as the client machine and minion service were not up and running.
- The server is in control to implement batching or rate limiting of Salt calls.
- The server is in control to implement maintenance windows with reasonable
error handling e.g. in case of minions that are down or unreachable at the
scheduled date and time.
- Job return events will no longer accumulate in the message queue causing the
server to run out of memory.
- There can be setups with multiple Salt masters returning all results into the
same SUSE Manager database.

# Detailed design
[design]: #detailed-design

## Scheduling of actions on the server

### Using taskomatic

With taskomatic we actually have a good tool at hand to schedule and execute
actions on the server side: It uses quartz internally and even supports to run
jobs on a repeated schedule (like cron). Scheduling action execution in
taskomatic is easily implemented by adding a new job type (a Java class and a DB
migration). This job can be triggered via taskomatic's XMLRPC API whenever an
action has been scheduled by a user. This is already implemented in [the current
patch][the-patch]. As all taskomatic schedules are persisted to the database
they will also survive service downtimes.

In case an action is canceled it needs to be unscheduled, examples should exist
in the codebase. Canceling actions should be possible only as long as an action
is still in status `QUEUED`.

### Error handling

As soon as the SUSE Manager server itself is in charge of the action schedule
and the execution of actions we also gain more control over the error handling,
especially regarding minions that are currently not running or unreachable for
some reason. Possible options include:

- Repeat trying to execute actions until the minion is back (or repeat `n` times
until we set the action to `FAILED`).
- Execute actions as soon as a minion comes back after downtime which could be
detected by listening to [minion start events][start-events].

Another option might be to minimize the time a thread would possibly wait on a
timeout by improving the detection of minion unavailability in Salt itself. This
still needs to be investigated though.

### Batching

In order to avoid heavy loads on the server by job results coming in at the same
time some mechanism of *batching* or *rate limiting* of outgoing Salt calls will
be needed that is closely coupled with the server side scheduling. This will be
specified in detail via a separate RFC.

## Using returners for collecting action results

Receiving and processing job results via the message queue can block the queue
from processing other things and happens to cause the process to run out of
memory. In order to avoid this we can use the existing minion action cleanup job
in taskomatic to resolve action results from the Salt job cache instead.

### Setting up an external job cache

In order to gain performance and reliability, a master side job cache other than
the default one should be used. The best option for postgresql based servers
seems to be the [`pgjsonb` returner][pgjsonb] while the [`odbc` returner][odbc]
*might* work for oracle. It is important to understand that **any** job cache
will do (even the default one) as we are interfacing it only via the [jobs
runner][jobs-runner] of Salt.

Using an external job cache requires us to take care of cleaning it up though,
so an additional job might be needed to delete old job cache entries on a
regular basis.

### Trigger the cleanup job

On every incoming job result we might want to trigger the cleanup job in order
to complete (or fail) the corresponding SUSE Manager actions nearly in real
time. Therefore a database trigger can be used that notifies taskomatic via a
listener that it needs to run the cleanup (already implemented in the [WIP
branch][the-patch]). We might want to trigger the cleanup only in case a result
is received that actually corresponds to a SUSE Manager action though. This
could be determined by looking at the Salt call metadata in the trigger
function.

Notifying Java code from a postgresql database trigger could be done using
[LISTEN/NOTIFY][listen-notify] for example. Even though similar technologies
exist for oracle databases as well, it might also be an option to simply set the
regular schedule of the cleanup job to run it once per minute in order to avoid
the need of maintaining two different database specific versions of the code.

# Drawbacks
[drawbacks]: #drawbacks

- Actions in SUSE Manager are not going to be updated in real-time. Only after
the cleanup job did run in taskomatic we can see in the UI if an action has
completed successfully or failed. It's on us to trigger the cleanup job.
- All the suggested patch works only for postgresql, oracle needs to be handled
completely differently: the returner, DB setup and trigger, the listener code in
Java, all this is not compatible. A solution could be to simply run the cleanup
job on top of every minute.

# Alternatives
[alternatives]: #alternatives

So far we tried to resolve action results directly from the job return events
with the described problems. Using the schedule in the minions further turned
out to have many disadvantages, therefore this RFC.

# Unresolved questions
[unresolved]: #unresolved-questions

- How to implement batching or rate limiting (or backpressure) exactly?
- Should we completely remove **all** parsing of job return events in tomcat?
How can we implement the minion *checkin* then?

[schedule-module]: https://docs.saltstack.com/en/latest/ref/modules/all/salt.modules.schedule.html "Schedule module"
[master-job-cache]: https://docs.saltstack.com/en/latest/topics/jobs/external_cache.html#master-job-cache-master-side-returner "Master job cache"
[the-patch]: https://github.com/SUSE/spacewalk/compare/Manager-salt-integration-revisited "WIP patch"
[start-events]: https://docs.saltstack.com/en/latest/topics/event/master_events.html#start-events "Minion start events"
[jobs-runner]: https://docs.saltstack.com/en/latest/ref/runners/all/salt.runners.jobs.html "Jobs runner"
[listen-notify]: https://jdbc.postgresql.org/documentation/head/listennotify.html "LISTEN/NOTIFY"
[pgjsonb]: https://docs.saltstack.com/en/latest/ref/returners/all/salt.returners.pgjsonb.html#module-salt.returners.pgjsonb "pgjsonb returner"
[odbc]: https://docs.saltstack.com/en/latest/ref/returners/all/salt.returners.odbc.html#module-salt.returners.odbc "odbc returner"
