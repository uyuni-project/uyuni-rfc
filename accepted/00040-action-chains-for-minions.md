- Feature Name: Action Chains for Salt Minions
- Start Date: 2017-11-29
- RFC PR: #65

# Summary
[summary]: #summary

This RFC describes how to implement the "Action Chains" feature parity for Salt minions.

# Motivation
[motivation]: #motivation

On SUSE Manager 2.1 we introduced the feature of "Action Chains" where the user is able to define a chain of different actions (patch installation, remote command, etc) that are going to be executed following a predefined order by the user. These actions can be targeted individually either to a single system or set of systems, and each action will require the previous one in the chain to be successfully executed in order to allow the execution of current action defined in the chain.

We introduced Salt on SUSE Manager 3.0 but "Action Chains" are not yet implemented for Salt minions. This is a requirement in order to achieve feature parity between traditional and Salt systems.

The "Action Chains" are widely used across SUSE Manager customers, as this feature allows customers to define a list actions which are executed on their systems following certain order. Some uses cases are: adding nodes to a load balancer, updating keys and restarting services, etc.

This RFC proposes how to bring the traditional "Action Chains" feature to Salt minions (reusing the current UI, with no extra feature or functionality) in a way to achieve feature parity with a minimal implementation effort.

# Detailed design
[design]: #detailed-design

## Add support on minions for traditional Action Chains

Looking at the current "Action Chains" implementation for traditional clients, it seems that it would be easy to add support for minions for the current "Action Chain" feature. No extra tables are expected as the current schema would fit also with minions. Another good point here is that the customers could mix traditional and minions inside the same Action Chain as there are no separated UI or workflow when dealing with minions.

Currently the "Action Chains" internals work as the following:

- At the time of scheduling a new Action, the UI allows scheduling it individually or to add it as a new entry in an "Action Chain".
- When adding new actions to an "Action Chain", the related SUSE Manager action containing the needed info is also created on the DB, but without having the `prerequisite` attribute set yet. At this time we're only defining the entries of the "Action Chain".

- Once the execution of the "Action Chain" is scheduled, the action chain itself is removed: The corresponding "rhnServerAction" rows are created for each one of the actions and servers related to these actions. These new "rhnServerAction" rows defines the execution information (scheduled time, status, etc). At this point, also the `prerequisite` attribute (which point to the previous action id) is set to each action in order to define the execution order of those.

- When targeting multiple servers on the same "Action Chain" entry, at the time of scheduling, multiple "rhnAction" rows are created: one different action per system included on that action chain entry. That means, each server targeted on the "Action Chain" has their own set of "Action" (with prerequisite ordering) to execute.

- These new actions' status are set to `QUEUE` on their respective "rhnServerAction" row at the time of creation.
- The actions will be consumed and executed by the traditional client, using the same mechanisms like for any other action which is not part of an action chain, but following the predefined order.

So, we need to do some adaptations in order to enable this feature on Minions:
- Enable Action Chains UI fragment to enable adding actions to an Action Chains when targeting minions.
- Adapt logic to avoid creating one action per system but instead create actions that targets multiple minions.
- Adapt logic to actually trigger the action execution when the Action Chain is scheduled to be executed.
- Handle actions to be executed on the Minions and get the responses.
- Think about providing a reliable "reboot" and "update salt" action.

### How actions are handled once the Action Chain is scheduled:
At this point, we have the respective "rhnAction" and "rhnServerAction" rows created and now we need a way actually triggering the execution of these actions following the defined order on the targeted systems. There are few alternatives here that we would need to evaluate, more over in terms of scalability and performance:

**Option 1:** Schedule the first action in Taskomatic and use the Salt Reactor on the Java side to catch the response from an action execution and then check if there is another action which depends on this one to be triggered. If so, the Salt Reactor would schedule next action execution to Taskomatic.
- **Pros:** No extra delay between actions. As soon as SUMA server gets a response, it triggers the next. Same behavior as for traditional clients (one system failure doesn't affect other systems). Easy to implement.
- **Cons:** Possible scalability issues as this reduces Reactor performance, making it to check for possible actions to be triggered on every Salt job return that comes from the Salt bus. The "reboot" problem needs to be resolved using i.a. an orchestration state for that action as we will see later.


**Option 2:** Schedule all actions using Taskomatic: At the time of execution, the taskomatic worker will check if the `prerequisite` action is not set `COMPLETED`, if so, the action will be reschedule some time in the future (30~50 seconds).
- **Pros:** Keep Salt Reactor as faster as possible. Same behavior as for traditional clients (one system failure doesn't affect other systems). Easy to implement.
- **Cons:** Scalability issues. Taskomatic workers will be heavily consumed just by checking if prerequisite actions are completed and rescheduling. As we are rescheduling certain time in the future, the next action doesn't actually start to be executed as soon as the previous one is completed. The "reboot" problem needs to be resolved.


**Option 3:** Scheduling execution of a Salt Orchestration state which contains all the actions: So we delegate the action handling to the Salt orchestrator (wait and trigger next action). Then, as soon as the Salt reactor on the SUMA server is getting the responses for those actions, it would update the status of the respective SUMA action pointed on each action metadata.
- **Pros:** Do not affect either taskomatic or Salt reactor performance. Delegates action handling work to Salt. Solves the "reboot" and "salt update" problem as we will see in a moment. The Salt Orchestration will be also used in the future for more complex orchestration across different systems. Since the Action Chain would be converted into an Orchestration State, it would be easy to also allow storing it in the Orchestration State Catalog to re-use it later.
- **Cons:** Might be like killing ants with a canon, as the Salt orchestration solves this issue but is meant to really do a more complex orchestration between different systems and we're not actually making use of this here. Would be nice to have some performance tests here to know how the Salt Orchestrator deals with a high load of jobs coming on the Salt bus. A change is needed on the Salt Orchestration to allow the behavior we currently have for traditional clients (one system failure should not affect others). A small change is needed in the `saltmod` module of Salt to allow metadata to be passed from the orchestration SLS to actual Salt function to execute: [Git branch](https://github.com/openSUSE/salt/tree/openSUSE-2016.11.4-orchestration-metadata)


**Option 4:** Creating a single SLS state file which contains all actions: This will require implementing a Salt local job cache on the Salt minion side which enables the minion to recover and continue working on a running job when it gets restarted, rebooted, crashed. This would need to be fixed on the Salt core codebase.
- **Pros:** All actions are received by the minion in one shot. Minion then process the entire SLS and makes only one response to the master. Seems the best option in terms of impact on performance & scalability. As we render an SLS which defines the Action Chains, it would be very easy also to place a button to "Save this Action Chain as a new state in the State Catalog". Same behavior as for traditional clients (one system failure doesn't affect other systems).
- **Cons:** Requires implementing a safe local job cache on the Salt minion side which somehow stores the running job so it allows the minion to recover after a crash (due Salt update) or after rebooting the system, and resume their operation to produce a final response for the initial Salt job. As only one Salt job is created which contains all the actions, the response from minion would contain all actions results, that means we needed to parse this response and also modify the `metadata` we pass to the Salt job to be able to allow multiple `suma-action-id` so the Reactor can set the right status for the actions when they are executed. It seems to be kind of tricky. Another option here would be to compact all actions into a single one titled "Applying Action Chain Action" which contains all the output from applying the SLS file but that means we would lose the action/output granularity we already have.

**Option 5:** Generate an SLS file with the actions to be executed and apply it using a custom module in order to handle restarts. Divide the state file in multiple
chunks according to the system reboot or Salt service restart. When applying the state, a custom module will be used to store the name of next chunk to be executed in a local file on the minion.

In order to trigger the execution of the next chunk after a service/system restart the Salt reactor will be used. On receiving a `salt/minion/*/start`
event the reactor will invoke the custom module (e.g. `mgractionchain.resume`) without any parameter. The module will get the next chunk to execute
 from a local file and will apply it. The Reactor will always invoke the `mgractionchain.resume` module without checking the database for pending actions.


_Custom module:_

`mgractionchain.start` - starts the execution of an action chain on a minion:
1. Apply the first action chain state:
    ```
    state.apply actionchain_<id>_<minion>_<chunk>.sls
    ```

`mgractionchain.next` - put the next chunk to be executed in the local store

`mgractionchain.finish` - finish action chain execution by removing next chunk from the local store

`mgractionchain.resume` - resumes the execution of an action chain on a minion:
1. Read the name of the chunk to execute from a local file and remove if from the file
2. Apply the action chain state:
    ```
    state.apply <chunk_name>.sls
    ```
3. If the last chunk was executed remove the local file.


_Example_

E.g.: For an action chain like this:
```
A1 - install a pkg
A2 - restart system
A3 - ...
A4 - ...
```

targeting minions `M1`, `M2` and `M3` as follows:
```
A1 -> M1
A2 -> M1
A3 -> M1, M2, M3, M4
A4 -> M2, M3, M4
```

SUSE Manager generates a state file for each one of minions. These files would be also split in chunks in case a reboot action or salt update is executed in the middle.

E.g. for `M1` - `actionchain_123_M1_1.sls`
```yaml
action_A1:
  module.run:
    - name: state.apply
    - mods: packages.pkginstall
    - kwargs: {
        pillar: {
          param_pkgs: {
            'hoag-dummy': '1.1-2.1'
          }
        }
      }

action_A2:
  module.run:
    - name: system.reboot
    - at_time: 1
    - require:
      - module: action_A1

next_chunk:
  module.run:
    - name: mgractionchain.next
    - chunk: actionchain_123_M1_2
    - require:
      - module: action_A2
```

`actionchain_123_M1_2.sls`
```yaml
action_A3:
  module.run:
    - name: state.apply
    - mods: channels

finish_action_chain:
  module.run:
    - name: mgractionchain.finish
    - chunk: actionchain_123_M1_2
    - require:
      - module: action_A3
```

For `M2` - `actionchain_123_M2.sls`
```yaml
action_A3:
  module.run:
    - name: state.apply
    - mods: channels

action_A4:
  module.run:
    - name: state.apply
    - mods: hardware.profileupdate
    - require:
      - module: action_A3
```
. . .

Then a single Salt call is made to start the execution of the corresponding action chain in all the minions:
```bash
salt 'M1,M2,M3,M4' mgractionchain.start
```

`M1` is restarted and the server receives the `salt/minion/M1/start` event. For this event the Reactors executes:
```bash
salt 'M1' mgractionchain.resume
```
This causes the next chunk (`actionchain_123_M1_2.sls`) to be read from the local file and executed on the `M1` minion.

_Results mapping_:

Currently we add metadata (`suma-action-id`) to the Salt call in order to match the result to the SUSE Manager action. Adding metadata
doesn't seem to be possible when triggering the state apply locally on the minion. Furthermore in a state file for an action chain
there can be multiple actions that would each need their own metadata. To avoid changing Salt core to support such a scenario one
option could be to encode the id of the action in the name of the state, e.g. `action_456`.

_SSH minions_

`salt-ssh` creates individual connections for each minion. The jobs targeting `salt-ssh` minions are executed synchronously by Taskomatic.

Since `salt-ssh` calls are synchronous there is no need to use a custom module. Taskomatic could simply apply the action chain states in 
a synchronous manner. 

In case of multiples chunks Taskomatic should check if the last action from the previous chunk completed successfully (i.e. restart or Salt pkg update)
before applying the next chunk. Reboot is already handled for SSH minions. Something similar should be done for updating the Salt package.


**Pros:**
- Conceptually similar to the traditional action chains, i.e execution happens in parallel.
- No need to use Salt Orchestration.
- No need to change core Salt functionality.

**Cons:**
- Reactor must do an additional Salt call on every minion startup to resume any interrupted action chains. However the
overhead should be low since there are already a number of calls being executed on minion startup.
- `SaltServerActionService` needs to be refactored to allow for better separation between preparing for a call and creating the call object.
The prepare phase is needed before starting the action chain execution while creating the Salt call objects is not needed for action chains.
The prepare phase is especially important for the subscribe channels action and the image build action.

**Performance impact**:
- Generating state files for each minion means a potential performance bottleneck.
- Preparing for the execution of some states requires more overhead (e.g. generate new tokens for changing the channels). This is unavoidable
and would be the same for other options as well.

**After discussion inside the Team, we think Option 5 is the right choice here. The following sections are based on "Option 5" choice**

### The "reboot" and "salt update" problem
As mentioned, the reboot problem is solved by spliting the SLS file in chunks and using the reactor to catch the `minion/start/event` and resume the operations.

Updating the Salt packages is a bit more tricky because it might happens that Salt crashed temporary just after the update, so it might not complete the execution of the latest step on the SLS chunk (the call of `mgractionchains.next`). To avoid this situation, we can always set the Salt update as the latest step on the SLS chunk, then on the next chuck we will add an extra step to check if the Salt package was actually upgraded so the action chain execution can continue.

### Translating Action Chain into an SLS file:
Either if we go with option 3, 4 or 5, it's needed to render a SLS file content based on a given Action Chain definition, making each entry of the Action Chain translated in a new step of this render SLS content. These steps would need to use the `require` attribute to define the dependencies between those (This applies in both cases: normal SLS file or orchestration SLS file).

This new component on the SUSE Manager Java side knows how each type of SUMA Action (pkg install, remote cmd execution, etc) has to be translated, so a final Salty SLS file will be generated (and probably temporary stored on the FS) to be able to apply it later when the action chain is executed.

# Drawbacks
[drawbacks]: #drawbacks

# Unresolved questions
[unresolved]: #unresolved-questions
