- Feature Name: Salt Rate Limiting
- Start Date: 2017.05.09

# Unimplemented note

This RFC was not ultimately implemented due to time constraints. It might be revived in future.

# Rate Limiting on SUSE Manager for Salt clients

# Summary
[summary]: #summary

This RFC describes the implementation of a Rate Limiting mechanism for the Salt Master to allow SUSE Manager to deal with Salt clients when an excesive amount of jobs are reaching the Salt event bus.
This mechanism allows enforcing limits in order to avoid crashes caused by running out of resources (eg: memory, disk space).

# Motivation
[motivation]: #motivation

We need the Rate-Limiting mechanism in order to prevent SUSE Manager overloading when dealing with an excesive amount of job returns.
Currently, in a scenario with a high number of Salt Minions connected to a Salt Master, running a job on all those minions at the same time can generate an excesive amount of Salt job return events that crashes SUSE Manager.
Minions can also be overloaded by scheduling too many jobs at the same time, that could produce out of memory problems due the amount of Salt Minion processes that have been spawned in the client.
These two situations can be avoided by configuring this mechanism.
Having a way to define limits would also be useful to prevent Salt from using all the resources of the machine.

Part of the motivation comes from the [FATE entry 322994](https://fate.suse.com/322994)

Improving SUSE Manager's Job Returns processing capability is not addressed here.

# Detailed design
[design]: #detailed-design

## Overview
The control component described in this RFC is named: **Salt Job Handler**

The purpose of `Salt Job Handler` is to control the flow of jobs that comes from the Salt Job Generator to the Salt Event Bus.

This `Salt Job Handler` component is implemented inside the core of the salt-master process and it controls what happens to a Salt job before it is published.
It integrates in Salt as shown in diagram below:
![Overview Left](images/overview-left.png)

As mentioned, `Salt Job Handler` is placed inside the Salt master core just after master generates the `JID` for a Salt Job. Then, instead of directly publish it on the Salt event bus, the job would be taken by this new `Salt Job Handler` which will decide whether the job can by published at that moment or should be put into queue due the overloaded environment.

In order to define the criteria or strategy that will be used by the `Salt Job Handler`, an "External Criteria Module" needs to be supplied. This is a pluggable and customizable module which lives outside the Salt master core as an external Salt module (like ext. pillar modules, master_tops, etc).
That way, this mechanism allows to easily switch the strategy, allowing Salt users to define their own criterias with only providing a simple "decision" interface which will be called by the `Salt Job Handler`.

This "Rate Limiting" mechanism will not be enabled by default in the Salt master. The user must explicitely enable it in the master configuration files (i.a, `/etc/salt/master`). The "External Criteria Module"  will be also set via Salt master configuration file. Ex:
    
```
rate_limiting:
  criteria: suma_criteria_mod.py
```

If rate limiting is not enabled, then `Salt Job Handler` won't be attached to Salt master and jobs will go directly from the Salt Job Generator to the Salt Event Bus (Salt default behavior).


## Salt Job Handler

![Overview Right](images/overview-right.png)

The `Salt Job Handler` has the following internal components:

- API

- Job Queue

- Queue Manager


The `Queue Manager` component processes the items accumulated in the Queue and it delegates the decision strategy to the `External Criteria Module`.

### API
The `Salt Job Handler API` is an interface used by external components to add items to the internal `Job Queue`.

### Job Queue
Is a Queue exposed through the API described above to the `Salt Job Publisher`. This Queue stores the jobs that cannot be executed at the moment because we're dealing with an overloaded environment.

### Queue Manager
This is core component of the `Salt Job Handler`. It communicates the internal Queue, the External Criteria Module and also the Salt Event Bus, and define the interface allowed with the External Criteria Module


## Queue Manager: Detailed [generic]

![Queue Manager Generic](images/queue_manager_generic.png)

The main task of the Queue Manager is to dispatch jobs from the internal Queue to the `Salt Event Bus` according with decision taken by the `External Criteria Module`. It continously fetchs the first element of the internal queue, checks if the job is still valid (in case of possible timeouted synchronous jobs) and will ask to the `External Criteria Module` if this job can be executed in that particular moment.

The `External Criteria Module` will evaluate the job internally (depending on the implemented strategy) and it will take a decision that will be then executed by the `Salt Job Handler`.

### Job Queue Consumption
#### Timeouts on synchronous calls
When a synchronous call is made from Salt CLI or Salt API, it would be create internally a async job which will be published and returned to the CLI or API. Then it will be waiting to gather all the the responses. If it reaches the timeout without having all the responses then CLI or API will trigger a new job to the unresponsive minions to check if they are still running that job:

- If the job is still running on the minion then Salt CLI or API will wait until it finished (checking every gather_job_timeout interval if the job is still running)

- If minion does not response or the job is not present in the minion, then we will get a timeout exception.

This is important because, if the User gets a timeout exception via CLI or API, it means that the job cannot be executed on that minion. With this approach, it may happen that a job originated as synchronous is **placed on the Queue for more time than the `timeout` for that particular call**, which actually means that the CLI or API has already raised a timeout exception. In such case, it doesn't make sense to publish it when we fetch it from the queue, therefore **that job will be discarted even without asking to the `External Criteria Module`**.

### Decision Execution
The possible decision are:
- Put the job back into the queue (as the first element)

- Publish the job on the Salt Event Bus

On this first version of the RFC we're considering the Queue as a **FIFO**. In case that we consider that non-FIFO strategies would be also valid we could just improved this current version to also allow that new type of strategy.


## Proposed External Criteria Module for SUSE Manager

![Queue Manager SUMA](images/queue_manager_suma.png)

With the `External Criteria Module` proposed for SUSE Manager we introduce the concept of Master and Minions capacities.
Master and all the Minions have each a capacity assigned.

The Master capacity represents how many Job returns the Master can handle at a particular point in time. If this limit is reached, no more jobs will be published until the already scheduled jobs finish.
`Master Load Tracker` is in charge of keeping the current Master capacity.

The Minion capacity represents the maximum number of published jobs that target that Minion at a particular point in time.
`Minions Load Tracker` is in charge of keeping the current capacity for each of the Minions.

These are configuration parameters set via Salt Master configuration file. Ex:
```
rate_limiting: 
  criteria: suma_criteria_mod.py
  max_master_jobs: 2000
  max_minion_jobs: 10
```

For the initial implementation, we choose a simple approach and assign the same capacity to each Minion and 1 point to each job.
The `External Criteria Module` will keep track of Master's capacity and each Minions capacities and when the `Queue Manager` asks for a decision, it will decide based on the capacities.
The `External Criteria Module` takes care of replenishing the capacities once the jobs have been executed.
The `Salt Event Handler` takes care of replenishing the capacities by listening at events on the Salt event bus.
The `Maintenance` component prevents capacity leaks due to missed events or other malfunctions. It will periodically check, according to Master and Minion Tracker, for jobs that has been running on a minion for more than a seteable amount of time. It will consider those jobs as "long-running" jobs, then the `Maintenance` component is going to trigger a `saltutil.running` command targeting all long-running minions to sync minions capacities.

An example of this workflow would be:

- Given a Master with 100 capacity and 2 Minions with 10 capacity each.

- When the `External Criteria Module` is asked to decide for an incoming job, as all jobs are assigned to consume 1 point, the decision will be to publish the job into the `Salt Event Bus`.

- Before returning this decision to the `Queue Manager`, the `External Criteria Module` would also update its internal capacities for the Master and Minions.

- Then new Master capacity will be 98 (100 initial capacity - 2 minion x 1 point) and the Minions capacities will be 9 each.

- These new capacities will be used for the next decision.

- The capacities for Master and Minions would be added back accordingly when `Salt Event Handler` gets a `Job Return Event`. In case of a `Minion Start Event`, it would reset minion's capacity. The `Maintenance` component is also able to change the capacities for both Master and Minions accordingly depending of job information gathered from the Minions.

### Decision Component: Detailed

![Decision Component](images/decision_component.png)

- Running out of capacity on Master: The job is not published. It would be put back in the queue as the first element. The job will be reevaluated later.
- Running out of capacity on Minions: If the Master has enough capacity but some of the minions don't, then this approach will exclude those overloaded minions from the target list of the Job. Therefore, once we get the return event for that job containing all the minions reponses, we'll see that some of then are missing. This would be the exact same behavior when you target some unreachable minions.

### Salt Event Handler

![Salt Event Handler](images/salt_event_handler.png)

As shown above, the `Salt Event Handler` is responsible for replenishing the capacities in the `External Criteria Module`.
It listens on the `Salt Event Bus` for the following events:
 - Minion start events
 - Job return events
 
The `Minion Start Event` triggers a capacity reset for that particular Minion and an adjustment of the Master capacity.
The `Job Return Event` means a job was executed so the points spent for that job need to be added back to the capacities.


### Maintenance

![Maintenance](images/maintenance.png)

This component prevents capacity leaks by running periodically and check if there are jobs that the `External Criteria Module` believes are still running but they are not.
If there are jobs like that, the capacity spent on them is added back both to the Master and the Minions Load Trackers. This is done by triggering a `saltutil.running` call to those minions that, according to the internal trackers, has been executing a job for too much time. After gathering the actual jobs which are running on those minions, the `Maintenance` task is able to synchronize the Minion and Master Trackers capacity data according to this actual information from the minions.


# Extra notes
## Synchronous calls
In an overloaded scenario, a Salt synchronous call should work as it does so far but it would take more time to be executed if the job is put on queue. In case of overloaded minions, User would get the return of the job execution from all minions except for those overloaded minions which were excluded from the job by `Salt Job Handler` + the usual `minion didn't response` error for those overloaded minions. Same output that you expect if some minions are down and you make a synchronous call to them.

## Asynchronous calls
Asynchronous calls work in the same way as synchronous calls, but you won't get a timeout exception because it does not make sense for an async calls. User would get the `jid` just after it's created (as usual) and, in case that the job is put on queue due overloaded scenario, it would take more time until responses from minions are attached to the generated Salt job. In case of overloaded minions, there will be no returns included for those minions related to that Job. Same as when doing asynchronous calls to some unreachable minions.

## SSH Minions (salt-ssh)
This mechanism might also work for SSH minions, this is not clear so far as salt-ssh works in a different way as normal minions. SSH minions are handled by `salt-api` (even using `salt-ssh` CLI). It using the information provided in a roster file and maybe this works differently.


# Future steps:

- Support Minions with different capacities based on their resources
- Support non-FIFO strategies on Queue Manager and External Criteria Modules
- Assign different capacity costs to Salt jobs depending on how many resources the job would actually use
- Make the External Criteria Module able to gather live information from SUMA which helps to improve the strategy. (Ex: Hardware info, etc)


# Drawbacks
[drawbacks]: #drawbacks

Why should we *not* do this?


# Alternatives
[alternatives]: #alternatives

What other designs have been considered? What is the impact of not doing this?


# Unresolved questions
[unresolved]: #unresolved-questions

What parts of the design are still TBD?

### Preventing `test.ping` calls from being queued

SUSE Manager has an internal mechanism to prevent from reaching timeout when doing synchronous calls in Salt. This is call Salt presence ping, and is basically a Salt `test.ping` call with a short and fixed timeout values. That way, SUSE Manager knows if there are unreachable minions and then exclude them from the actual call. 

With this `Salt Job Handler` approach, it may be necessary to exclude the `test.ping` commands from being put in the queue. That way, SUMA will not produce empty calls due the salt presence ping didn't get any response from a minion in the expected short fixed time.

Seems it makes sense to exclude those `test.ping` jobs from being queued.

### Limiting the size of the Queue
Since the internal Queue of the `Salt Job Handler` might grow up to the infinite in such a hardly overloaded scenario, it seems that it makes sense to set a limit on the size of the Queue, so that way we prevent `salt-master` process to crash due running out of memory in such cases where the Queue is taking almost all memory of the master.

This is rare scenario, as there're mechanism to increase capacities and get enough to run the next job, but in theory it could be reached in such a extreme load scenario.

Limiting the size of the Queue would mean that, when this Queue size limit is reached, `salt-master` would not be able to handle a new job without running out of memory, therefore `salt-master` needs to reject that job completely (without place it on the Queue), and return a new error expection meaning that `salt-master` is overloaded and cannot handle that job at the moment. That way, User knows that they have to retry it later (instead of crashing the Salt Master) but at the same time all the components would need to be aware of this new possible exception code meaning that the job cannot be run at the moment.
