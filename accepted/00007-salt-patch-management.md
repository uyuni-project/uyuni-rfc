- Feature Name: Salt Patch Management
- Start Date: 2015-12-18

# Summary
[summary]: #summary

This RFC describes how patching minions works in SUSE Manager.

# Motivation
[motivation]: #motivation

With the new [declarative approach](https://github.com/SUSE/susemanager-rfc/blob/master/text/00003-salt-package-installation.md), patch management needs to be defined so that it plays well in this model.

# Detailed design
[design]: #detailed-design

## Concept

This proposal does the following assumptions:

* Patch management is mainly done using channel lifecycle via cloned channels
* Package state allows to define the policy for each package (Absent, Installed, Latest)

Therefore we define patching as the action of reacting immediately to a *Patch alert* from SUSE Manager in order to remmediate it, applying the fixes now or scheduling them.

## Implementation

* For the time being (GA) we scratch fixed version support in the states for now. "Locks" can for now be controlled with the state of the channel. We only support Absent, Installed, Latest.
  * Latest need to be added/implemented

* Minions will already get normal alerts from patches, computed from their uploaded package list

* We implement patching of minions as immediate actions like with RHN style clients.

* As the system gets alerts for patches, they are seen as a "emergency" or tool to patch outside of your channel life-cycle, so:
  *  We implement patch management in the "old" way.
  * we enable the ErrataList page for minions and linking from alerts to the apply patches page.

* We implement the patch action using an immediate action (execution module)
  * We can use pkg module prefixing the package name with "patch:".

* It plays well with package states. If you have a cloned channel and
your package state is:

| State       | Meaning                                                                       |
|-------------|-------------------------------------------------------------------------------|
| Absent      | It will not trigger a patch notification                                      |
| Installed   | New version in the cloned channel. Applying the highstate will not upgrade it |
| Latest      | New version in the cloned channel. Applying the highstate will upgrade it     |

Note that in all cases, after triggering the patch execution, the states are still valid.

### Patch actions

Scheduling can be implemented wrapping execution module calls in the schedule module:

```
salt '*' schedule.add job2 function='cmd.run' job_args="['date >>
/tmp/date.log']" once='2015-12-18T10:40:00'
```

This will schedule cmd.run for later (you can also call `pkg.install` or `state.highstate` of course). The schedule will be added to `/etc/salt/minion.d/_schedule.conf`.

When the job happens, the `ret` event in the master will contain a `schedule="job2"` key. This metadata can be used to clean the job with schedule.delete on the client, otherwise it stays there, which does not hurt because the "once" parameter but it still needs to be cleaned up.

To integrate with the history in Spacewalk the folling can be done:

* When scheduling, we create a generic SaltAction in state pending, with information about the job.
* We use schedule.add to create a job with an id that has the database id of the action eg: `susemanager-action-XXXX`.
* When the action completes, the event is retrieved, and if the schedule key is there the action result is set.
* From time to time, all jobs on minions that have no pending actions are purged using `schedule.purge`.

To install patches without modifying the `pkg` module the prefix `patch:` can be used:

```
pkg.install patch:foo
```

# Drawbacks
[drawbacks]: #drawbacks


# Alternatives
[alternatives]: #alternatives

* Implementing patches as pure state

This alternative has been proposed but the impact on usability and the workflow is not very clear. This does not mean we should not add patches to the general software state but only that that should not be the primary workflow to patch but more an assurance/auditing/control mechanism.

Just imagine the patch state table after hundred of patches had been released.

However, adding the ability to set a state for a CVE or patch name could be very valuable.

# Unresolved questions
[unresolved]: #unresolved-questions

* We still need to figure out how to patch Redhat, as the current implementation resolves the list of packages in the patch calling back the server.

