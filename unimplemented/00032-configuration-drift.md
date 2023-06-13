- Feature Name: Managing Configuration Drift in SUSE Manager
- Start Date: 2016-12-30
- RFC PR: (leave this empty)

# Unimplemented note

This RFC was not ultimately implemented due to time limitations. It is still archived here for historical purposes.

# Summary
[summary]: #summary

Add support for managing Configuration Drift based on Snapper baselines in SUSE Manager

# Motivation
[motivation]: #motivation

One of the main purposes of SUSE Manager is acting as a central Configuration Management panel.
Since Salt integration with SUSE Manager, we are able to set and apply desired actions, define systems configurations by using user-defined Salt states, or running the highstate (which is the set of Salt states that defined a certain system), and even more by using the Salt Formulas integration which allows the user to define those system states using web forms.

Therefore, SUSE Manager gives to the user an easy way to handle and apply custom user-defined configurations but it's lacking from a clear way to detect and revert configuration deviations or unwanted changes in our systems.

The purpose of this RFC is provide "Configuration Drift detection and management support" to SUSE Manager based on the Snapper baseline approach for Salt minions.

**This feature would have the following requirements on the Minion:**
- Snapper.
- Salt Snapper module (included in upstream Salt 2016.11 and also backported to our 2015.8 branch).
- D-Bus Python Bindings (`dbus-1-python` package on SLE11+ and `dbus-python` on RHEL).
- Snapper GRUB2 plugin (`grub2-snapper-plugin` package on SLE12+). Required for booting from previous snapshots if thing goes wrong.
- A working SUSE-style btrfs snapper root configuration. (Including all common subvolumes `/var/cache/`, `/var/log/`, etc)

If the minion is able to run `snapper.list_configs` then we have a working Salt Snapper module on it, which means that "Configuration Drift Audition" feature is available for this minion.

**Of course, it could be possible to support this feature in non-SUSE-style snapper root config, but we'll first start expecting SUSE-style configutarions.**

The idea is to enable SUSE Manager to be able to easily follow the Audit cycle using the UI:

```
      Initial baseline is
     created in the system
               |
               |
               V
    System in a correct state --> Configuration Drift is detected --> Revert the unwanted changes
      (Content according to         (Some files are deviating            (Changes are reverted
         the baseline)                  from the baseline)             according to the baseline)
           ^      ^                             |                                  |
           |      |                             |                                  |
           |      |                      Changes are OK.                           |
           |      |              Updating baseline and documentation               |
           |      |                             |                                  |
           |      |                             |                                  |
           |      --------------<----------------                                  |
           |                                                                       |
           -------------------------------------<-----------------------------------
```

# Detailed design
[design]: #detailed-design

## The Snapper Salt module and the baseline approach.
Snapper is a tool for managing filesystem snapshots allowing you to create, delete, compare and revert differences between them.
Currently it supports `btrfs` filesystem snapshots, LVM thin-provisioned snapshots and it also has an experimental support for `ext4` (with an special kernel version).

Snapper FAQ: [here](http://snapper.io/faq.html)

Snapper is included in SLES systems since SLE11 SP2 version and `btrfs` is the default filesystem from SLES12 onwards.
We can manage Snapper in a Minion by using the Salt Snapper module. Here are some examples:

```
master# salt 'minion0' snapper.create_snapshot
minion0:
    120

master# salt 'minion0' cmd.run "echo 'test string' >> /etc/motd"

master# salt 'minion0' snapper.diff num_pre=120 num_post=0
    ----------
    /etc/motd:
        ----------
        comment:
            text file changed
        diff:
            --- /.snapshots/120/snapshot/etc/motd
            +++ /etc/motd
            @@ -1 +1,2 @@
             Welcome! You're in a managed system
            +test string
    /var/cache/salt/minion/proc/20170101210713079168:
        ----------
        comment:
            binary file deleted
        old_sha256_digest:
            907ef01e8cb13d81d09500f5f824ecd78492e8359a85997cc935501c1d034a83
    [...]
```

As you can see, it's very easy to see if changes have been done in any file of the filesystem (not only in some explicitely managed files). i.a. `/etc/motd` or `/etc/hosts`.

The Snapper Salt module also provides an state function called `snapper.baseline_snapshot`. This allows you to create a Salt state where you define that the content of the selected btrfs subvolume should be exactly identical as the content in the selected baseline snapshot.

We can ignore some files or paths from the comparison and use different Snapper configs:

```
restore_to_baseline_snapshot:
  snapper.baseline_snapshot:
    - tag: mgr_baseline_tag
    - config: root
    - include_diff: False
    - ignore:
      - /root/.viminfo
      - /var/log
      - /var/cache
    - order: 1

restore_external_storage_to_baseline_snapshot:
  snapper.baseline_snapshot:
    - tag: mgr_baseline_tag
    - config: external
    - order: 1
```

We could even include these states into the `top.sls` and make them part of the highstate for a given minion. Then, when using `order: 1`, it should be executed in the first place ensuring that the other states are applied after restoring to system to a defined baseline.

More info about Salt snapper module:

[Snapper Salt execution module documentation](https://docs.saltstack.com/en/latest/ref/modules/all/salt.modules.snapper.html)

[Snapper Salt state module documentation](https://docs.saltstack.com/en/latest/ref/states/all/salt.states.snapper.html)


## Managing baselines for configuration drift audit with SUSE Manager.

The "Configuration Drift Audit" feature is not enabled by default for the candidates systems.

A SUSE Manager Administrator should go to the new "System page -> Configuration Drift tab" and then:
- **Enabling the feature by setting up a new "BaselineConfig" for the selected system. This would include:**
    - Name. i.e. "Root filesystem"
    - Snapper config to used (SNAPPER_CONFIG). Must be unique for the minion.
      (Available configs could be gathered running `salt 'minion' snapper.list_configs` - default config is "root")
    - List of files or paths to be ignored from the comparison. (array)
    - Extra administrator comments.

    We're expecting a SUSE-style snapper root configuration where certains paths like `/var/log/`, `/var/cache/`, `/var/opt`, `/home`, `/tmp`, etc. are contained as subvolumes and excluded from the "root" snapper configuration so we don't need to explicitely exclude/ignore them from the comparison.

    So, the most common use case would be to setup a "BaselineConfig" for the "root" snapper config (SUSE-style default config) and exclude some custom paths defined by the user.

    In case we decided to support non-SUSE snapper configuration, SUSE Manager should suggest a predefined list of typical directories/files to exclude containing some items like `/var/log/`, `/var/tmp`, `/var/cache/`, `/tmp/`, which can be modified by the Administrator to also exclude their custom paths.

    If the given "SNAPPER_CONFIG" is not available in the Minion, SUMA should raise an error to the UI and do not store the "BaselineConfig" object in the database. Otherwise the "BaselineConfig" object will be stored in the SUMA database.

- **Now, admin is able to create the first "Baseline" based on the current state of the system, which includes:**
    - Description.
    - Creation date. (hidden for the user)
    - Related "BaselineConfig". (hidden for the user)
    - Snapper snapshot ID. (hidden for the user)
    - Status = \["AVAILABLE", "ENABLED", "UNAVAILABLE", "UNCONFIRMED"\] (hidden for the user)

    When a new baseline is created, it first takes the status of "UNCONFIRMED" until the snapshost is actually created in the Minion. Once the Minion confirms the snapshost created then the "Baseline" object automatically takes the status of "ENABLED" and stores the snapshot id and the creation date.

    Only one "Baseline" can be enabled for each "BaselineConfig" at the same time, so when creating a new "Baseline", this will override the previously enabled "Baseline" and set the status to "AVAILABLE" for the old one.

    In case of multiple "BaselineConfig" are defined (for using multiple SUBVOLUME), all stored "Baseline" objects will appear grouped by "BaseLineConfig".

Once the "BaselineConfig" is set and "Baseline" is enabled. Administrator is also able to:

- **Enable or disable "Configuration Drift detection mode" option. (Only available once "Baselines" are enabled)**
    Once there is an enabled "Baseline" for the minion, administrator may want to toggle between "Normal mode" to "Configuration Drift detection mode".
    Enabling this mode will produce the following:
      - System is set to locked.
      - Daily jobs will be executed to looking for "ConfigDrift" issues.
      - Applying patches, updates, states or highstate is not allowed if a "ConfigDrift" issue is detected. Adminstrator must solve the "ConfigDrift" issue before doing these changes.
    (This could be stored in a new `ConfigurationDriftDetectionMode` attribute of the Minion)

- **Enable or disable "Enforce baselines restoring during highstate execution" option. (Only available once "Baselines" enabled)**
    If this option is enabled for a minion, `highstate` will automatically restore the changes in the filesystem according to the enabled "Baseline" and "BaselineConfig" settings.
    (This could be stored in a new `EnforceHighstateBaselineRestoring` attribute of the Minion)


### Pillar data and the new "apply_baseline.sls"

Let's see in more detail what is happening when Administrator saves a "Baseline" in the UI:

1. A "Baseline" object is created in the database with status "UNCONFIRMED", preventing the Admin from scheduling more "Baseline" creations for the same "BaselineConfig".

2. A Salt job is schedule to run `salt 'minion' snapper.create_baseline config=$SNAPPER_CONFIG mgr_$SNAPPER_CONFIG_baseline` in order to create the snapshot in the minion using the selected "BaselineConfig".

3. If this Salt job is successfully executed then it must return the Snapper snapshot ID for the created baseline which would be stored in the related "Baseline" object and the status set to "ENABLED". If there was an error running this job and no snapshot id is returned, then we should report the failure to the Administrator and the "Baseline" object will be removed from the SUMA database so Administrator can try to create a "Baseline" again.

4. When a "Baseline" is set to "ENABLED", SUSE Manager will also render the enabled baseline information for each created "BaselineConfig" as pillar data for this minion in the respective `/srv/susemanager/pillar_data/pillar_{minion}.yml`.

A generated pillar data for a minion should look like this:
```
enforce_highstate_baseline: True
mgr_baselines:
  mgr_root_baseline:    # mgr_$SNAPPER_CONFIG_baseline
    number: 54          # Snapper snapshot ID
    config: root        # $SNAPPER_CONFIG
    ignore:             # List of paths to exclude
      - /foo/bar/
      - /foo/file_to_ignore

  # This is how looks an extra Baseline created
  # for a different BaselineConfig called "external"
  mgr_external_baseline:
    number: 12
    config: external
    ignore: []
```

This pillar data will be consumed by the new `apply_baseline.sls` state file which is now provided by SUMA in `/usr/share/susemanager/salt/` and would contain something like:

```
{% if pillar.get("mgr_baselines") %}
{% for baseline in pillar["mgr_baselines"] %}
{{baseline}}:
  snapper.baseline_snapshot:
    - number: {{pillar["mgr_baselines"][baseline]["number"]}}
    - config: {{pillar["mgr_baselines"][baseline]["config"]}}
    - ignore:
    {% for ignore in pillar["mgr_baselines"][baseline]["ignore"] %}
      - {{ignore}}
    {% endfor %}
{% endfor %}
{% endif %}
```

At this point, since we have now enabled "Baselines" (which have been set as ENABLED at the time that Salt jobs succesfully created it in the minion), we are able to audit the minion by running the following Salt job:
```
# salt 'myminion' state.apply apply_baseline test=True
myminion:
----------
          ID: mgr_root_baseline
    Function: snapper.baseline_snapshot
      Result: True
     Comment: Nothing to be done
     Started: 02:09:15.559931
    Duration: 6.267 ms
     Changes:
----------
          ID: mgr_external_baseline
    Function: snapper.baseline_snapshot
      Result: None
     Comment: 1 files changes are set to be undone
     Started: 02:11:06.636227
    Duration: 2762.367 ms
     Changes:
              ----------
              /var/lib/wicked/lease-eth0-dhcp-ipv4.xml:
                  ----------
                  comment:
                      text file changed
                  diff:
                      --- /var/lib/wicked/lease-eth0-dhcp-ipv4.xml
                      +++ /.snapshots/121/snapshot/var/lib/wicked/lease-eth0-dhcp-ipv4.xml
                      @@ -4,13 +4,13 @@
                         <uuid>7c576658-66c0-0e00-fc01-000004000000</uuid>
                         <state>granted</state>
                         <update>0x00000000</update>
                      -  <acquired>1483405131</acquired>
                      +  <acquired>1483311747</acquired>
                         <ipv4:dhcp>

Summary for myminion
------------
Succeeded: 2 (unchanged=1, changed=1)
Failed:    0
------------
Total states run:     2
Total run time:   2.772 ms
```

As you can see, this reports the config drifts for each enabled baseline of all the defined "BaselineConfig" objects.

If we want to audit only one single "Baseline" (instead of all enabled baselines for all "BaselineConfig") we can use the `mgr_$SNAPPER_CONFIG_baseline` ID to refer the enabled baseline for your $SNAPPER_CONFIG:
```
# salt 'myminion' state.sls_id mgr_root_baseline apply_baseline test=True
myminion:
----------
          ID: mgr_root_baseline
    Function: snapper.baseline_snapshot
      Result: True
     Comment: Nothing to be done
     Started: 02:09:15.559931
    Duration: 6.267 ms
     Changes:

Summary for myminion
------------
Succeeded: 1
Failed:    0
------------
Total states run:     1
Total run time:   2.267 ms
```

## Auditing Configuration Drift problems:

So, at this point, with a valid and enabled "Baseline" set for the Minion, we're able to:

- **Live check for configuration drift issues (including a diff) on a defined "Baseline":**
    This could be done by just running `salt 'minion' state.sls_id mgr_$SNAPPER_CONFIG_baseline apply_baseline test=True`


- **See detected configuration drift issues (created via "config-drift-gatherer" Taskomatic job).**
    The idea would be that Taskomatic will periodically (daily) run `salt 'minion' state.apply apply_baseline test=True` to check for configuration drift in all the defined baselines **only for those minions in "Configuration Drift detection mode".** If the state reports a configuration drift, then SUMA must alert to the Administrator via email and create a new "ConfigDrift" object (PENDING status) with the reported information.

    This "ConfigDrift" object should contains:
    - Related "Baseline".
    - Status = \["ACCEPTED", "REJECTED", "PLANNED", "PENDING"\]
    - Reported Diff? - Not sure if we should include the diff here since it could be very big, or even differ from the time in which it was detected and the time of the actual revertion to the baseline.. so audit planning notes might be incomplete or inconsistent.
    - Notes (available for adminstrator edition)
    - Created. (timestamp)
    - Processed (timestamp)


- **Validate or revert the detected changes in the "ConfigDrift" and also add a description/note to it as documentation.**
    In case of validate the changes, a new "Baseline" will be created in the minion to override the previous one. Pillar data is recreated after the new "Baseline" is enabled and the "ConfigDrift" object is updated. Previous "Baseline" status is set to "AVAILABLE".
    If the administrator reverts the changes:
      - A snapper snapshot will be created in the minion (not in SUMA) to allow the system to boot from the unreverted snapshot in case that something goes wrong. This backup snapshot will be available in the grub2 menu to boot from only if `grub2-snapper-plugin` is installed (SLE12+).
      - A Salt job running `salt 'minion' state.apply apply_baseline` will be executed (without `test=True`) in the minion to revert those changes according to the corresponding baseline.
      - **It's a best practice to reboot the minion after reverting changes, but it's up to the administrator to do that.**

    The user might also schedule the job of reverting changes in the next maintenance window.
    **NOTE: Problem here is that audited changes may have changed since the job was scheduled and the time when it is actually executed**

    The status of the "ConfigDrift" should change accordingly with user's choice.

- **Explore all the "ConfigDrift" history.**
    Administrator should be able to explore the "ConfigDrift" history, showing the notes, diff and the status of the "ConfigDrift" (ACCEPTED, REJECTED, etc).
    Manually removing old "ConfigDrift" objects from the history will be also available as well as automatically removing old "ConfigDrift" objects after a certain amount of days.

- **Choose another enabled "Baseline" from the available Baselines.**
    Administrator is able to change the enabled baseline between the available ones, i.e. unwanted changes were added to last baseline.
    After changing the enabled "Baseline", pillar data will be refreshed and the `apply_baseline.sls` will change accordingly.

- **Manual execution of the "snapper-cleanup-and-sync" job.**
    This job is actually executed every time we create a new Snapper baseline snapshot (Baseline) but should be also available for manual execution.
    It removes older defined baselines from Snapper and set the status of these "Baselines" to UNAVAILABLE. We only keep the last 'N' baselines created in Snapper as AVAILABLES baselines in our SUMA UI.
    UNAVAILABLE baselines are keep in the database for history proposes. Admin should be able to explore the "ConfigDrift" history of a given baselines regardless of its status.


## Automatically setting up a "BaselineConfig" (ACTIVATION KEYS):

This feature enables the capability of adding a default "BaselineConfig" definition for an `ACTIVATION KEY`. A new tab called "Configuration Drift" will be added to the "Activation key edit page" allowing the user to go there and set up a new "BaselineConfig" data for that activation key.

The new "Configuration Drift" page for the activation keys should looks like:

- "BaselineConfig" data.
- Enable "Configuration Drift detection mode" for the minion. (checkbox)
- Enforce baseline restoring during highstate? (checkbox)
- Create initial Baseline. (checkbox)

During the onboarding, if the minion is using an `ACTIVATION_KEY` with configuration drift settings, then a new "BaselineConfig" object will be created for that minion using the "BaselineConfig" data provided by the `ACTIVATION KEY` and a new initial baseline will be created in the minion accordingly just after the first `highstate` is executed for the onboarded minion and the minion attributes will be stored.


## Enforce baseline restoring during highstate:
Since the `highstate` could considered as the "default" or well-configure state of the minion, there is the possibility to always apply the `apply_baseline` state as the first step of the highstate. Therefore we ensure that our minion is reverted to the defined baseline and then all next defined states are applied.

We only automatically includes `apply_baseline` in the `highstate` for minion which have a the related "BaselineConfig" set to "Enforce baseline restoring during highstate" (meaning minion already has `pillar["enforce_highstate_baseline"] = True`), or in case the user explicitely checks the new "Enforce baseline restoring during highstate" checkbox in the `highstate` page (only available when there's an enabled Baseline).

An easy way to force the highstate to apply or not the `apply_baseline` state would be:
- Adding a new `baselines` state to the SUMA master_top module.
- Creating `/usr/share/susemanager/salt/baselines/init.sls` containing something like:
```
{% if pillar.get("enforce_highstate_baseline") %}
include:
  - apply_baseline
{% endif %}
```
- If the user explicitely checks the "Enforce baseline restoring during highstate" checkbox in the highstate page, then a temporary override of the pillar data could be done for this particular `highstate` call: `salt 'minion' state.highstate pillar='{"enforce_baseline_restoring": True}'`

Notice that we lose control about auditing changes if we enforces baseline restoring during highstate because the changes are automatically reverted when the highstate is triggered. Even if those changes are good, they will be reverted as they are not included in the current baseline.


## Applying patches, updates, custom states or highstate in "Configuration Drift detection mode":
When a minion is running in "Normal mode", nothing differs from the current minion behavior when installing new packages or patches, updating, etc. even if the minion already has a "BaselineConfig" and "Baselines".

On the other side, running in "Configuration Drift detection mode" means we have the system locked and we want to have the control of auditing all the configuration drift found in the system. This case has special implications:
- No changes are allowed if there are `PENDING` or `PLANNED` "ConfigDrift" objects for the minion. User must first handle that "ConfigDrift" and the it's allowed to try again.
- Just before any patch/update/pkg/state/highstate operation is performed, we must perform a **live check* of configuration drift in the minion. If the check unverified changes then the User should solve that first.
- If no issues reported then the operation is performed on the minion.
- If the operation is succesfully executed then a new "Baseline" creation job is triggered to include the latest changes in a new "ENABLED" baseline.

There is an exception here, if minion is set to "Enforce baseline restoring during highstate" then `highstate` is allowed to run **without checking for possible existing configuration drift issues**. Possible changes are automatically reverted.


## Applying configuration groups of systems (SSM):
This feature needs to be accesible via API, therefore multiple methods need to be implemented:
- `CreateBaselineConfig`, `EditBaselineConfig` and `DeleteBaselineConfig`.
- `CreateBaseline`.
- `EnableConfigurationDriftDetectionMode` and `DisableConfigurationDriftDetectionMode`.
- `SetEnforceBaselineRestoringDuringHighstate`.
- `ValidateConfigDrift`
- `RevertConfigDrift`

This will allow us to manage groups of systems in a "System Set Manager" (SSM).


## Switching from "Configuration Drift detection mode" to "Normal mode" and viceversa:
As per "Locked/Unlocked" systems, User should have an easy way to switch from "Normal mode" to "Configuration Drift detection mode" an viceversa. This could be done via the "Configuration Drift tab" in the Minion page, SSM, or by activation key. It may be interesting to include a button to switch between modes in the minion "Overview" page.

- Changing from "Normal mode" -> "Configuration Drift detection mode": (only allowed if minion have enabled "Baseline")
  - System is set to "Locked".
  - Set `ConfigurationDriftDetectionMode` minion attribute to `True`

- Changing from "Configuration Drift detection mode" -> "Normal mode":
  - System is set to "Unlocked".
  - Set `ConfigurationDriftDetectionMode` minion attribute to `False`


## Phase 2: Turning a snapper diff into a Salt state:
It would be interesting, at least in a phase 2, to implement a way to convert certain "diff" returned by Salt Snapper module into a Salt (file) state. This will allow us to easily re-use these changes and applying them into other minions.

The Salt `file` state module includes a `file.patch` function which allow you to patch a minion file using some patch file located in `salt:/`. [More info](https://docs.saltstack.com/en/latest/ref/states/all/salt.states.file.html)

Turning a Snapper "diff" into a (file) state can be tricky but achivable:
- A text "diff" can be easily converted in a `file.patch` state storing the "diff" as patch file into `salt:/`.
- Files to remove can be set using `file.absent`.
- New files can be created using `file.managed` state using a file source poiting to `salt:/`.
- Generated states files are saved into Salt `file_roots` of the SUMA server: i.e. `/srv/susemanager/salt/configdrift_files/`

An example of a possible generated state stored into `/srv/susemanager/salt/configdrift_somehash_related_to_this_diff.sls`:

```
/etc/hosts:
  file.patch:
    - source: salt://configdrift_files/somehash_related_to_this_diff/etc/hosts.diff

/etc/tmpfile:
  file.absent

/bin/myscript:
  file.managed:
    - source: salt://configdrift_files/somehash_related_to_this_diff/bin/myscript
```


## Accepting or reverting individual files instead the entire baseline diff:
Currently Salt Snapper module allows you to revert only some particular files when reverting changes. The `snapper.baseline_snapshot` state function always reverts the entire snapshot except the ignored/excluded files.

To allow this we should:
- Allowing selecting individual commits in the UI.
- Dinamically set an extra list of ignore/exclude list of files for the `snapper.baseline_snapshot` in the `apply_baseline` state via pillar override data when calling the state. This extra file list is based in the User choices from the UI for this particular "ConfigDrift".
- After changes are applied, a new baseline needs to be created to rebase the previous one with the new changes.


## Integration with "transactional-updates":
MicroOS/CaaSP and next SLE13 introduce the `transactional-updates` concept. Basically, in order to update the running system (zypper up or dup), it creates a read-only snapshot (as backup of the current system and listed in the snapshots grub2 submenu) and then it also creates new read-write snapshot which is actually used to perform the zypper update call there (using chroot, zypper --root, etc). Then grub2 is set to boot from this last snapshot is everything was successfully done. (`grub2-snapper-plugin` is required)

So, with `transactional-updates` the system keeps running with all services up while the system is being updated in other file system snapshot. The system needs to be rebooted in order to boot using the updated snapshot.

Using the same approach of applying changes in a separated snapshot + rebooting could be also a good solution for us when reverting changes of a "ConfigDrift", but currently we're reverting changes using the snapper `undochange` function which **only** revert changes in the current running snapshot.

It could be interesting to implement another way to revert/apply changes into a certain snapshot by:
- Creating RO backup baseline + next boot baseline: `$ snapper rollback`
- Set read-write for next boot baseline: `btrfs.properties /.snapshots/NUMBER/snapshot set='ro=false'`
- Manually copying/removing/modifing the files in the next boot snapshot by the Snapper module itself.

Then we could provide the same solution that `transactional-updates` does: revert changes in a new snapshot separated from the running system and then reboot into the updated snapshot.


## The "snapper-cleanup-and-sync" mechanism.

We have a limitation about creating new "Baselines". Snapper itself cannot store an unlimited amount of snapshots because it will cause a disk full issue, so it implements a few cleanup methods to remove old snapshots.

We can avoid from using the Snapper built-in cleanup methods if we don't set a "cleanup method" during snapshot creation. This will prevent us from having deleted baselines due a Snapper cleanup and gives us all the control about creating but also deleting old snapshots. We need then to provide our own cleanup mechanism for our "Baseline" snapshots.

Since we're creating new "Baselines" each time we validate a "ConfigDrift", it's necessary to have a mechanism to remove older baselines and keep only a defined amount of baselines

So this "cleanup-and-sync" mechanism basically removes older snapshots from Snapper and keeps the enabled one and a certain amount of the latest snapshots. Every time an old Snapper baseline snapshot is removed we must set the "Baseline" status for such baseline to "UNAVAILABLE" in the SUMA database.

This job will also clean older "ConfigDrift" objects after a certain amount of days.

## The SUMA Database

New classes would be created and mapped in the SUMA database:

```
Class BaselineConfig:
  - Minion.
  - Name (string).
  - Snapper config to used. Must be unique for the minion. (string)
  - List of files or paths to be ignored from the comparison. (array)
  - Extra administrator comments. (string)

Class Baseline:
  - BaselineConfig
  - Description.
  - Creation date.
  - Related "BaselineConfig".
  - Snapper ID.
  - Status = ["AVAILABLE", "ENABLED", "UNAVAILABLE", "UNCONFIRMED"]

Class ConfigDrift:
  - Related "Baseline".
  - Status = ["ACCEPTED", "REJECTED", "PLANNED", "PENDING"]
  - Diff? - Not sure if we should include the diff here since it could be very big, or even differ from the time in which it was detected and the time of the actual revertion to the baseline.. so audit planning notes might be incomplete or inconsistent.
  - Notes (available for adminstrator edition)
  - Created. (timestamp)
  - Processed (timestamp)
```


# Drawbacks
[drawbacks]: #drawbacks

**Reverting parts of the filesystem to the status of a given baseline may causes severe problems. These are some examples:**
- Missing boot kernel image. If a kernel image is removed from the filesystem we should update GRUB.
- If we revert executables files, installed packages or services then we should reload these running processes.

To avoid this kind of problems we should ensure that certain file paths are always ignored when generating our `apply_baseline` state. So the idea is using configuration drift not as entire filesystem content rollback but using it more in a way of auditing the content of the configuration files.


# Alternatives
[alternatives]: #alternatives

What other designs have been considered? What is the impact of not doing this?

# Unresolved questions
[unresolved]: #unresolved-questions

### Saving big filesystem "diff" in the "ConfigDrift" history may cause problems:
As mentioned, it may happen that the reported "diff" is too big. This could happend i.a., if we don't ignore `/var/log/` from the detection, or if customer does not explicetly ignore some of their "noisy" custom paths.

Any way to avoid this? We might set an acceptable size for storing the diff in the database in order to keep it in the "ConfigDrift" history. If the actual "diff" is bigger then it will be truncated but Administrators are always allowed to manually run `salt 'minion' state.apply apply_baseline test=True` to get all the "diff" without storing it in the database.

### What happend if the disk is full?
The custom implemented "cleanup" method prevents us from creating unlimited snapshots which ends with an full disk.

If an disk if full, Snapper still be able to create a new snapshots based or even revert changes (at least for some subvolumes) but in case of "/" filesystem run out of space, then `salt-minion` process might and we will have a problem. This is not supposed to happen using the current proposal.
