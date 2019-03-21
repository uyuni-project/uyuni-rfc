- Feature Name: Salt Orchestration States for Salt Minions
- Start Date: 2017-11-29
- RFC PR:

# Unimplemented note

This RFC was not ultimately implemented as a different design was preferred. It is still archived here for historical purposes.

# Summary
[summary]: #summary

This RFC describes how to implement the "Salt Orchestration States" feature for Salt minions.

# Motivation
[motivation]: #motivation

On SUSE Manager 2.1 we introduced the feature of "Action Chains" where the user is able to define a chain of different actions (patch installation, remote command, etc) that are going to be executed following a predefined order by the user. These actions can be targeted individually either to a single system or set of systems, and each action will require the previous one in the chain to be successfully executed in order to allow the execution of current action defined in the chain.

The "Action Chains" are widely used across SUSE Manager customers, as this feature allows customers to define a list actions which are executed on their systems following certain order. Some uses cases are: adding nodes to a load balancer, updating keys and restarting services, etc.

This RFC proposes a completely new approach for "Action Chains" on Salt minions, with new UI, extra features and based on Salt Orchestration. This new approach for minions is based on the following premises:

- Separation of concepts: One guy creates, another executes.
- Action Chains must be reusable multiple times.
- Easy to use UI which can be used without Salt knowledge.
- Make use of the predefined Salt State catalog.

# Detailed design
[design]: #detailed-design

Before going forward, it's important to remark that the traditional action chains are not actually an orchestration chain. Traditional Action Chains don't establish restrictions between steps which targets different systems, it only establishes restrictions for steps (actions) in the same system.

For Salt minion we could use the Salt Orchestration runner to enable a full orchestration engine, which establishes dependencies across different steps and systems, to define our reusable Orchestration States for Salt minions.

## Salt Orchestration States for Salt Minions:

The idea here would be to provide a completely new approach for "Action Chains" on Salt minions. We will use Salt Orchestration to enable us to execute more complex chains of operations (which are defined by our SUMA actions). These orchestration steps, which can point to multiple systems, establish restrictions/dependencies between steps, and in opposition with a Traditional Action Chain, wait until one step has been completed on all the targeted system before going with the next step execution. And of course, getting back the results of all the steps execution.

This new proposal includes a new UI with a new workflow. It would allow reusing our orchestration states multiple times, and add new extra features that would be only available for Salt minions and not for the traditional stack.


### Salt Orchestration Runner:
Salt allows you to create your custom orchestration states using a special type of SLS files. These orchestration SLS files are placed on the Salt `file_roots` (usually inside an `orch` directory) and can executed via `salt-run state.orchestrate orch.my_orch_state`. Notice that Salt orchestration is executed as a runner on the Salt master.

An example of an orchestration SLS file would be:
```yaml
bootstrap_servers:
  salt.function:
    - name: cmd.run
    - tgt: ["minion1", "minion2"]
    - tgt_type: list
    - arg:
      - bootstrap

storage_setup:
  salt.state:
    - tgt: 'role:storage'
    - tgt_type: grain
    - sls: ceph
    - require:
      - salt: webserver_setup

webserver_setup:
  salt.state:
    - tgt: 'web*'
    - highstate: True
```

As you can see, execution modules can be called via `salt.function` and states and highstate can be applied via `salt.state`. The step execution order is sequential by default unless you explicitly set a different order, i.a. using `require` like in the example.

Also notices that the targets are set by step and we can use `tgt_type: list` to set the desire systems for each step even using a minion list injected via custom pillar data during the Salt call made by SUSE Manager:

```
$ cat /srv/salt/orch/mytest
apply_highstate:
  salt.state:
    - tgt: {{ pillar.get('target', []) }}
    - tgt_type: list
    - highstate: True
    - metadata:
        suma-action-id: 100

$ salt-run state.orchestrate orch.mytest pillar='{"target": ["minion1", "minion2"]}'
```

An important note here is that **each one of these steps defined on an orchestration SLS file are executed on the Salt side as different Salt job, which can contain also metadata about the `suma-action-id`**, so the jobs are processed in the minion side as if they were a normal Salt call (without orchestration). Once the results are returned to the master, the Salt Reactor could even set the results for thoses action on the database.

Of course, when a state or highstate is applied on a minion, the pillar data and grains are available for that minion as usual (even via ext_pillar module), and it's used for rendering the proper state to apply on that particular minion. Remember that each orchestration `salt.state` or `salt.function` calls are handled by the minion as a normal Salt job, so the minion has all resources available like when executing jobs without orchestration.

Therefore, the Salt Orchestration runner is then the component that handles the execution (trigger & track & wait) of all the steps defined in the orchestration SLS file. The execution of each step is handled by the Salt minion as a normal Salt job.

Using the Salt Orchestration runner seems to be a nice, easy and conceptually consistent approach to enable definition of Orchestration states that can be re-used, allows cross-systems actions dependencies and enables Salt to handle all this work instead of doing it on SUSE Manager.

[Salt Orchestration Documentation](https://docs.saltstack.com/en/latest/topics/orchestrate/orchestrate_runner.html)

Proposed class schema (inspired on Traditional Action Chains):

```
OrchestrationState (id, org_id, label, description, created, modified)
OrchestrationStep (id, order, action_id, system_id NULL, orchestration_state_id, created, modified)

OrchestrationExecution(id, orchestration_state_id, created, modified)
OrchestrationExecutionStep(id, order, action_id, system_id, orchestration_execution_id, created, modified)
```

![Proposed Class Schema](action-chains-for-minions/class-schema.png)

On this schema we've created a separation between the "definition" and the "execution" parts of the Orchestration workflow. Therefore, we defined the `OrchestrationState` and `OrchestrationStep` classes which allow storing all needed information about the action and target of such action, as well as its position on the Orchestration State it belongs to.

As you can notice here, each `OrchestrationStep` contains a reference to the specific action to be done on a particular system. This work in the same way than for traditional clients. The difference here is that this design allows `system_id` to be NULL, as we will allow creating Orchestration Steps directly from the Salt State Catalog and then assign the targets later.

At the time of scheduling an execution, `OrchestrationExecution` and `OrchestrationExecutionStep` classes will be created based on its "definition" classes (OrchestrationState and OrchestrationStep). Then a new `Action` object (based on the "Action" linked to the `OrchestrationStep`) and the corresponding `ServerAction` will be also generated at this point defining the execution.

OrchestrationState's are not deleted from the DB once it's scheduled or executed, so they can be reused as many times as you want.

This is what would happen at the time of scheduling the execution of the OrchestationState:

- A new `OrchestrationExecution` with the related `OrchestrationExecutionStep` and `Action` objects will be created based on its respective "definition" class.
- The "rhnServerAction" rows will be now created accordingly for each one of the steps and server using the new `Action` related with the `OrchestrationExectionStep`.
- An orchestration SLS file is rendered which contains each step, dependencies between steps, suma-action-id for each step and targeting.
- The Salt Orchestrator runner is called to execute the previous generated SLS file.
- As the responses from minions reaches the Reactor, the respective results for the suma-action-id will be set for that minion.

## The "reboot" and "salt update" problem
[reboot]: #reboot-problem

As we mentioned on this RFC, each action of an "Action Chains" requires a successful execution of the previous action in the chain. This is not a major problem for most of the Salt actions, as SUSE Manager receives the results from the Salt job once it's executed and then the next action in the chain can start.

The problem comes when we want to upgrade the Salt package on the minion or we want to restart the system.

- **"Reboot"** -> We can schedule a reboot but we don't know when the reboot completes and the minion is ready to accept new jobs.
- **"Update salt"** -> It may happen that the "salt-minion" process crashed during update so we need to provide a way to know when the "salt-minion" process is back again.

These two problems can be easily solved using a Salt orchestration state like for the following "Action Chain":

1. Apply `packages.pkginstall` builtin state to upgrade kernel package.
2. Reboot the system to boot from latest kernel.
3. Apply `webserver` state from State catalog which install apache and setup the server.

```yaml
mgr_orchestration_entry_1_upgrade_kernel_package:
  salt.state:
    - tgt: {{ pillar['targets']['entry_1'] }}
    - tgt_type: list
    - pillar:
        param_pkgs:
          kernel-default: 4.4.21-90.1
    - metadata:
        suma-action-id: 1111
    - sls:
      - packages.pkginstall

mgr_orchestration_entry_2_reboot_system:
  salt.function:
    - name: system.reboot
    - arg:
      - 1
    - tgt: {{ pillar['targets']['entry_2'] }}
    - tgt_type: list
    - metadata:
        suma-action-id: 2222
    - require:
      - salt: mgr_orchestration_entry_1_upgrade_kernel_package

mgr_orchestration_entry_2_wait_for_reboots:
  salt.wait_for_event:
    - name: salt/minion/*/start
    - id_list:
{% for minion in pillar['targets']['entry_2'] %}
      - {{ minion }}
{% endfor %}
    - require:
      - salt: mgr_orchestration_entry_2_reboot_system

mgr_orchestration_entry_3_apply_webserver_state:
  salt.state:
    - tgt: {{ pillar['targets']['entry_3'] }}
    - tgt_type: list
    - sls:
      - webserver
    - metadata:
        suma-action-id: 3333
    - require:
      - salt: mgr_orchestration_entry_2_wait_for_reboots
```

As you can see, the "reboot" step is split into:

- `mgr_orchestration_entry_2_reboot_system`: Schedule a reboot of the system 1 minute in the future and send response to Salt master.
- `mgr_orchestration_entry_2_wait_for_reboots`: Wait until "minion start event" is triggered by the "salt-minion" after rebooting. Then it sends a response to Salt master to inform the minion is back and running again so next steps can now run.

We can follow the same approach when updating Salt during an "Action Chain".

### Handling injected pillar data for different minions:
One of the problem of using a single SLS file for orchestration which targets different minions is that some of the actions (like `packages.pkginstall` state) are designed to be called with some injected pillar data (i.a. `param_pkgs` with the exact list of package/version to install on a given minion). We would manage this situation by injecting the needed custom pillar data as part of the minion pillar data (which is loaded by the `ext_pillar` module):

```yaml
mgr_orchestration_state_action_1234:
  param_pkgs:
    kernel-default: 4.4.73
```

Then, we can directly apply `packages.pkginstall` SLS file (which needs to be adapted) like this:
```yaml
mgr_orchestration_entry_1:
  salt.state:
    - tgt: {{ pillar['entry_1']['targets'] }}
    - tgt_type: list
    - sls: packages.pkginstall
    - pillar:
        action_id: 1234
        mgr_orchestration_pillar: True
```

Notice this `mgr_orchestration_pillar` parameter that we introduce to tell `packages.pkginstall` what is the custom pillar source to use:
```
{% if pillar.get('mgr_orchestration_pillar', False) %}
{% set pillar = pillar.get('mgr_orchestration_state_' ~ pillar.get('action_id'), {}) %}
{% endif %}
```

## Orchestration with Salt SSH:
The Salt Orchestration runner support SSH minion as target. The only limitation is that it's not allowed to mix SSH and pure-minion systems on the same orchestration entry. This can be easily overcomed by spliting the step in two entries on the orchestration SLS file (as a reboot step), so we target pure-minion in one and SSH minion in the other, then the next step will require both two previous steps to continue:

```yaml
orchestration_entry1:
  salt.state:
    - tgt: ["minion1", "minion2"]
    - tgt_type: list
    - sls
      - bootstrap

orchestration_entry1_ssh:
  salt.state:
    - tgt: ["ssh-minion1", "ssh-minion2"]
    - tgt_type: list
    - ssh: True
    - sls
      - bootstrap

orchestration_entry2:
  salt.state:
    - tgt: ["minion3"]
    - tgt_type: list
    - pillar:
        param_pkgs:
          kernel-default: 4.4.21-90.1
    - sls:
      - packages.pkginstall
    - require:
      - salt: orchestration_entry1
      - salt: orchestration_entry1_ssh
```

## Type of actions in an "Action Chain":
There are different types of actions that could be placed into an "Action Chain":

- Packages/Patches Installation.
- Execute Remote command.
- Apply State.
- Apply Highstate.
- Apply Formula.
- Reboot the system.
- SP migration.
- Upgrade Salt.
- Apply/Deploy Configuration Channel.

Each one of these types of actions would be translated accordingly to the corresponding Salt orchestration state step (or 2 steps in case of reboot or Salt upgrade) which point to the selected state we want to apply or call an execution module, etc.

## Pluggable Salt Orchestration States (Orchestration Templates):
As we already do with Formulas, we would provide an easy way to plug builtin Salt Orchestration States into SUSE Manager, i.a. via installable RPMs. The "Orchestration Template" is esentially a collection of predefined states + a metadata file to describe each orchestration step (with or without any hardcoded target) following a fixed convention.

An example would be like this:
```
# /usr/share/susemanager/orchestration/states/update_salt/entry1_update_salt.sls
upgrade_to_latest_salt:
  pkg.latest:
    - pkgs: ["salt", "salt-minion"]


# /usr/share/susemanager/orchestration/states/update_salt/entry2_reboot_system.sls
reboot_system:
  cmd.run:
    - name: "shutdown -r +1"


# /usr/share/susemanager/orchestration/states/update_salt/init.sls
orch_entry1_upgrade_salt:
  salt.state:
    - tgt: {{ pillar['targets']['target1'] }}
    - tgt_type: list
    - sls:
      - entry1_update_salt

orch_entry1_upgrade_salt_ssh:
  salt.state:
    - tgt: {{ pillar['targets']['target1_ssh'] }}
    - tgt_type: list
    - ssh: True
    - sls:
      - entry1_update_salt

orch_entry2_reboot_systems:
  salt.state:
    - tgt: {{ pillar['targets']['target1'] }}
    - tgt_type: list
    - sls:
      - entry2_reboot_system
    - require:
      - salt: orch_entry1_upgrade_salt
      - salt: orch_entry1_upgrade_salt_ssh

orch_entry_2_wait_for_reboots:
  salt.wait_for_event:
    - name: salt/minion/*/start
    - id_list:
{% for minion in pillar['targets']['target1'] %}
      - {{ minion }}
{% endfor %}
    - require:
      - salt: orch_entry2_reboot_systems


# /usr/share/susemanager/orchestration/metadata/update_salt/metadata.yml
description: "This is a test Orchestration Template to upgrade Salt minion to latest version and reboot those systems"
targets:
  target1:
    - description: "Systems to perform upgrade and reboot"
    - allow_ssh: True
steps:
  step1:
    - description: "Upgrade 'salt' and 'salt-minion' packages to latest version"
  step2:
    - description: "Reboot systems after upgrade"
```

The provided metadata would be used by SUSE Manager to allow rendering a wizard UI to visualize the steps of that orchestration template and also allowing to set the needed targets and possible custom pillar data for rendering the jinja2 part of the `init.sls` file.

Notice that, in this example, the metadata.yml file describe an Orchestration template with 2 steps and only one target field. If `allow_ssh` is set to True, the Salt Orchestration `init.sls` must also handle the ssh targets.

Once the user set the targets and fill all the needed pillar data required by the metadata. The values provided by the user on the wizard UI will be stored on the master filesystem, in `/srv/susemanager/orchestration_data/update_salt.json` (following the same approach like with Formulas), so the user is able even to reuse this pre-built Orchestration State.

### Triggering execution of an Orchestration Template:
Since the steps of a builtin Orchestration Templates are not coupled to any `rhnAction`s previously created on the SUSE Manager DB, we will create `Action/ServerAction` for the global "Orchestration Template" execution, not one action per step, only 1 action per the entire orchestration.

That way, we allow more flexibility for the builin template design as well as a `ServerAction` per target which reflects the global result and output for the Orchestration Runner execution on the system history.

## UI design for Salt Orchestration States:

It's needed to create a few new pages in the UI to manage the Salt Orchestration States:

### Listing Orchestration States:
- This pages shows a list all the Orchestration states defined for this Organization.
- It allows the user to create a new empty Orchestration State with a given name.
- The user can click on a state to go into the Orchestration State page

### An Orchestration State page:
- Shows Orchestration State title and description.
- It contains a sortable list (like for Action Chains) with the defined steps on this state.
- Each step of the state has "Select targets" link which opens a dialog/box to easily define or change the target of that step.
- A "Clone State" and "Delete State" buttons are available on the upper right corner of the page.
- A datetime placeholder + "Schedule Execution" button is placed below the list of steps.
- Clicking on "Schedule Execution" triggers the Salt Orchestration execution of the given state at the scheduled time.

### Edit Orchestration State Step:
- Shows the title of Orchestration State it belongs to.
- Shows step title (Package installation, Remote Command, Reboot, etc)
- Contains a "Targets" box where you can click to expand the minions targeted for this steps.
- You can also click on a "Delete targets" button.
- This box allows you also to "Add Targets from SSM". This could be also enhanced in the future by allowing targeting directly using grains or glob, to allow a more dynamic targeting.
- An extra box showing the Action details is placed below the "Targets" box. I.a. packages to be installed, Salt state to be applied, etc.

### Add an action as Orchestration Step:
Currently, the SUSE Manager scheduler placeholder for an action allows you to schedule the given action execution on a particular date/time or alternatively to add the action as part of an Action Chain. This needs to be modified to allow an extra option available when targeting Salt minions:
- Add to: Orchestration State.

### From State Catalog to an Orchestration State:
Another different workflow to fill an Orchestration State would be directly from the Salt State Catalog. This proposal includes to add a button inside the State view page which adds a new Orchestration State Step for applying that state as part of the selected Orchestration State. In a similar way as for the scheduler placeholder.


## Development stages:

- Step 1: "Adding Salt Orchestration States for Minions: New UI, Reusable states"
- Step 2: "Support for SSH minions"
- Step 3: "Support for pre-built Salt Orchestration States"


# Drawbacks
[drawbacks]: #drawbacks

### Coexistence of "Traditional Action Chains" and "Salt Orchestration States" for Minions:
In case we decided to start implementing the "Traditional Action Chains" for Minions and later we add this new "Salt Orchestration States" feature, does it really make sense to have the two ways of doing similar things with Salt minions? I'll say that it does make sense to keep both if we clearly define those two as complete separate feature. This mean: "Action Chain" and "Salt Orchestration" as two different things. Maybe there are customers that are used to work with the traditional workflow and restrictions and don't want to use the new "Salt Orchestration" approach.

Maybe we should get rid of the "Traditional" way once we have the "Salt Orchestration State" feature implemented or, alternatively, vote directly for implementing the "Salt Orchestration States" without even implementing the traditional way on Minions.

### Salt Orchestration engine limits:
We don't know exactly how the limit are for this component when dealing with lot of workload. Salt Orchestration runner calls made against the salt-api can be performed asynchronously like we do for local Salt calls. The salt-master process will create a new thread/process to deal with the orchestration execution (triggering the Salt jobs, tracking responses from minion, and waiting).

I don't expect a high impact on performance when dealing with a few Salt Orchestration States on parallel. All load generated by those actions are handled as normal Salt jobs by the salt-master, the extra thread for tracking the orchestration should not consume lot of resources as it's only tracking the Salt bus to catch some events from the Salt bus and trigger next executions. Problems might of course arise if several concurrent Salt Orchestration States are running at the same time, but most of the load would be generated mostly by the Salt jobs themselves and not by the Salt Orchestration tracker thread, so that limit is not by the orchestration itself but for the amount of Actions the user is scheduling at the same time which cannot be handled by Salt.
