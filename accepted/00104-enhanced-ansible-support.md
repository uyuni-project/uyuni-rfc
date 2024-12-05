- Feature Name: Enhanced Ansible Support
- Start Date: 2024-12-04

# Summary
[summary]: #summary

Uyuni provides support for Ansible, although on a very limited scale. The plan is to enhance the existing integration with some key features. 

# Motivation
[motivation]: #motivation

Users wish to have Ansible more firmly integrated in Uyuni. We currently support the scheduling of Ansible playbooks through control nodes managed by Uyuni.

We identified the following improvements to enhance the current implementation:

1) Show the raw output results of a playbook in the event history of the control node along with a list of targeted inventory systems.
2) Add UI support to allow editing of variables defined in the playbook.
3) Support the recurrent scheduling of Ansible playbooks.
4) Set default playbook and inventory paths when adding a new control node in Uyuni.
5) Add option to filter by Ansible managed systems onboarded in Uyuni in the system list.

These points will be discussed one-by-one in detail in the next section.

# Detailed design
[design]: #detailed-design

## Show the raw output results of a playbook in the event history of the control node along with a list of targeted inventory systems.

#### Raw output

To show the raw output returned by the ansible command itself instead of the output returned by salt a change to the [runplaybook.sls](https://github.com/uyuni-project/uyuni/blob/master/susemanager-utils/susemanager-sls/salt/ansible/runplaybook.sls) will have to be made.

We're currently using the `state module`:
```
run_ansible_playbook:
  ansible.playbooks:
     - .......
```

To get the raw output we will have to use module.run to call the `ansible.playbooks` function from the `execution module`:
```
run_ansible_playbook:
  module.run:
    - name: ansible.playbooks
    - ....
```

The changed `runplaybook.sls` would then look like:
```
run_ansible_playbook:
  mgrcompat.module_run:
    - name: ansible.playbooks
    - playbook: {{ pillar["playbook_path"] }}
    - rundir: {{ pillar["rundir"] }}
    - flush_cache: {{ pillar["flush_cache"] }}
{%- if "inventory_path" in pillar %}
    - inventory: {{ pillar["inventory_path"] }}
{% endif %}
```

#### Displaying targeted systems

Since the list of systems targeted by an ansible playbook can be very long, I propose to display the used inventory as a link in the event history details instead.

In case the selected event details are of the playbook action type we will set an additional request parameter called `inventory` in `SystemHistoryEventAction.java` and render an extra row that would look like:
```
Inventory: <link_to_inventory>
```

Clicking the link would then forward the user to the inventory file in `System` > `Ansible` > `Inventories`.

The inventory then displays the list of systems registered in Uyuni that were targeted by the playbook execution.

Since pre selecting a specific inventory based on the provided URL is not currently supported by the [ansible-path-content.tsx](https://github.com/uyuni-project/uyuni/blob/master/web/html/src/manager/minion/ansible/ansible-path-content.tsx) component, it will have to be adapted to support it.
The URL to load a specific inventory would look like:
```
manager/systems/details/ansible/inventories?sid=<system_id>&iid=<inventory_id>
```
with `<system_id>` being the system id of the ansible control node and
`<inventory_id` being the id of the inventory to load.

## Add UI support to allow editing of variables defined in the playbook

The plan here is to enhance the existing UI in `System > Ansible > Playbooks > select playbook` with generated input fields based on the `vars` defined in the playbook.

For example
```
- name: Example playbook with various variable types
  hosts: all
  vars:
    # List variable
    software_packages:
      - git
      - nginx
      - curl

    # Dictionary variable
    user_info:
      username: "devuser"
      uid: 1001
      home_dir: "/home/devuser"

    # Integer variable
    max_open_files: 1024

    # Boolean variable
    enable_firewall: true

    # String variable
    welcome_message: "Welcome to the server setup!"
```
The UI would generate input fields based on variable type (list, dict, string) that are pre-populated with the default variables set in the playbook (if any).
Changing the values of the generated input fields will allow users to override the defaults and schedule the playbook using the variables set in said UI.

Additionally we should add a `free-form` text field to allow users to define additonal variables that were not part of the `vars` section and thus don't have an input field generated. This input would have to be in JSON format.

Based on the variables we will generate a JSON string called `extra_vars` that will be send to the backend along with other parameters needed to schedule the playbook.

The workflow on the frontend would look like:
1) Parse the selected playbook.
2) Generate input fields based on the `vars` section of the playbook.
3) Compile a JSON string from the inputs that will be send to the backend.

The `ansible.playbooks` salt state we use to execute playbooks at the scheduled time supports a parameter called `extra_vars` and accepts a JSON string. Variables set through this parameter will take precedence over the ones defined in the playbook and thus allow us to override them.

To support scheduling playbooks using `extra_vars` on the backend we will have to to add a new column to the `rhnActionPlaybook` table and adapt the corresponding hibernate entity. The JSON string could either be stored as `varchar` or alternatively as `blob` if we expect them to be large.

During execution of the action the `extra_vars` will then be passed as pillar data to the `runplaybook.sls` state that then executes the `ansible.playbooks` state using the pillar data.

This state will have to be changed to look like:
```
run_ansible_playbook:
  mgrcompat.module_run:
    - name: ansible.playbooks
    - playbook: {{ pillar["playbook_path"] }}
    - rundir: {{ pillar["rundir"] }}
    - extra_vars: {{ pillar["extra_vars"] }}
    - flush_cache: {{ pillar["flush_cache"] }}
{%- if "inventory_path" in pillar %}
    - inventory: {{ pillar["inventory_path"] }}
{% endif %}
```

#### Storing of variables edited by the user

To avoid that users have to fill the input field with their custom changes every time, we could implement a mechanism that would store their last used configuration.

To support this I propose adding a new table called e.g. `suseAnsiblePlaybookVars` with the following columns:

- `server_id`
- `user_id`
- `playbook_path`
- `extra_vars`

with the unique identifier being the combination of `server_id`, `user_id` and `playbook_path`.

This data would be stored whenever a playbook is scheduled from the UI.
If there is already a stored config with matching `server_id`, `user_id` and `playbook_path` we would override the previous one.

When loading the playbook scheduling page we would look up, if there is an existing config and merge the data into the generated input fields. Fields without a match (likely because the playbook has been edited by the user) would be omitted.

Along with this we should also provide a reset button to restore the input fields to the playbook defined defaults.

## Support the recurrent scheduling of Ansible playbooks.

To support the execution of Ansible playbooks using recurring actions we'll have to implement the follwoing steps:

1) Create a new `RecurringActionType` called `PLAYBOOK`.
2) Add a new database table called `suseRecurringPlaybook` with the following columns:
    - `rec_id` - The id of the corresponding recurring action
    - `playbook_path` - The path to the playbook we want to execute
    - `inventory_path` - The path to the configured Ansible iventory
    - `test_mode` - If we want to schedule a test execution
    - `flush_cache` - Whether the Ansible cache should be flushed
    - `extra_vars` - The user provided variables to use
3) Create a new `RecurringPlaybook` java class extending the base `RecurringActionType`          class acting as hibernate entity.
4) Add frontend support for handling recurring Ansible action.
Here we'll have to provide UI functionality to set/edit the Ansible action specific parameters. ideally we want to be able to reuse the `ansible-path-content.tsx` components capabilities (including the to be implemented handling of `extra_vars`) to also allow setting action specific parameters for recurring actions.
This includes changes to the `RecurringActionManager/Controller` classes.
5) Make changes to the `RecurringActionJob` taskomatic job to support the new recurring action type.
6) Implement API endpoints to support the managing of recurrent Ansible playbook execution.

This newly created action type would be a minion only recurring action that would only be configurable from Ansible control nodes.

As for the entry point to the new UI I see two options:

1) On `System` > `Ansible` > `Playbooks` UI create a `Schedule Recurring` button that will link to `System` > `Recurring Actions` > `Create`. Here we will add the `Ansible Playbook` option to the dropdown to select the recurring action type. The action specific UI would then generate based on the type selected (like we do for existing types).

2) Create a new `Recurring (Playbooks)` tab in `System` > `Ansible` that would allow the creation of Ansible Playbook recurring actions without having to select the action type first. Viewing created action details as well as editing/deleting existing actions would still have to be done from the `System` > `Recurring Actions` tab.

## Set default playbook and inventory paths when adding a new control node in Uyuni

This will be straightforward. Function to add playbooks/inventories already exists. We'll just have to call them with our wanted defaults when adding new control nodes.

These defaults will be:

Playbooks: `/etc/ansible/playbooks/`

Inventory: `/etc/ansible/hosts`

## Add option to filter by Ansible managed systems onboarded in Uyuni in the system list.

We will add a new entity called `ansible_managed (Ansible Managed)` to the `rhnServerGroupType` and `rhnServerGroup` tables.
To get the list of systems managed by an Ansible control node we'll scan all the inventories registered in `suseAnsiblePath`.

There is currently a salt state called `ansible.targets inventory=<some_inventory>` available that returns inventory data. The list of systems can be parsed from that data (this mechanism was already part of the original Ansible implementation).

However there are two problems that need two be solved here:
1) We need a way to automate collecting Ansible managed systems to make sure the list is up to date.

    This can be achieved by adding a `inotify beacon` on every control node. This beacon would contain the list of inventories registered on Uyuni and trigger an event to update the list of systems whenever one of the inventory files receives an update.

    See example beacon below:
    ```
    beacons:
      inotify:
        - files:
            /etc/ansible/hosts:
              mask:
                - modify
            /another/inventory/file:
              mask:
               - modify
        - interval: 5
        - disable_during_state_run: True
    ```

    This beacon would be updated whenever a inventory file is added/removed on Uyuni.

    Along with the beacon we'll have to add a new `reactor` to the salt master that will react to events send by the beacons.

    Additionally we'll trigger a manual update of the minion list whenever inventories are added/removed.

2) Calling `ansible.targets` for every inventory regularly can put a lot of extra load on the salt master if there is a greater number of inventories to be scanned.

    To address this we should update the `ansible.targets` function to be able to receive a list of inventories instead of a single one.
    ```
    salt 'ansible-control-node.tf.local' ansible.targets inventories='/etc/ansible/hosts, <another_inventory>, <yet_another_one>'
    ```
    The output could look something like:
    ```
    ansible-control-node.tf.local:
      /etc/ansible/hosts:
          ----------
          Some_group:
              ----------
              hosts:
                  - some-minion.tf.local
          _meta:
              ----------
              hostvars:
                  ----------
          all:
              ----------
              children:
                  - Some_group
                  - ungrouped
      <another_inventory>:
          ----------
          Another_group:
              ----------
              hosts:
                  - another-minion.tf.local
                  - additional hosts
          _meta:
              ----------
              hostvars:
                  ----------
          all:
              ----------
              children:
                  - Another_group
                  - ungrouped
      <yet_another_one>:
        .
        .
        .
    ```
    This way we'd only have to do one single salt execution per control node. We would then parse the output and compile it into a list of systems. This list will be used to add/remove the `ansible_managed` entitlement from systems registered in Uyuni.

# Drawbacks
[drawbacks]: #drawbacks

I don't currently see any drawback with the proposed implementation.

# Future improvements
- Make Ansible work with Uyunis system groups.
- Allow adding Ansible playbooks to custom state recurring actions to support executing multiple playbooks in order.

# Unresolved questions
[unresolved]: #unresolved-questions

The following points still need to be investigated in:
- It looks like the `inotify beacon` requires `python3-inotify package` to be installed on every control node. Is this beacon already available by other means or do we have to make sure the package is installed when setting up a new control node in Uyuni?
- How to update the `inotify` beacon from the webUI when new inventories added/removed?
- How will the results of the `ansible.targets` state triggered through above beacon be handled by the java backend?
