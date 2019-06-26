- Feature Name: Remote Command Auditing
- Start Date: 2019-06-21
- RFC PR: TBD

# Summary
[summary]: #summary

Implement a role-based access model to access `Remote Command` for managed systems and log every command executed.

# Motivation
[motivation]: #motivation

At the time of the writing, there are three features to issue a remote command on a managed system or a group of systems registered to the product:
- A `Remote Command` tab is present in the details section of a traditional or minion system (or a `System Set Manager` group)
- The API exposes the `system.scheduleScriptRun` to issue a command
- (Only for minions) a `Salt > Remote Commands` page to launch a command on minions by leveraging [Salt targeting](https://docs.saltstack.com/en/latest/topics/targeting/index.html) to identify the target(s)

Each user can only target the systems within the same organization that the systems are registered to, provided that the user has a particular role:
- Every user that has `SUSE Manager Administrator` or `Organization Administrator` role can access the tab and run a remote command on the selected system or a group of systems
- The API is always exposed but checks for the role of the user supplying the command after the API is called
- For every user registered to SUSE Manager, independent of the role, the menu item `Salt > Remote Commands` is accessible. Only users with the `SUSE Manager Administrator` or `Organization Administrator` role, though, can impact systems using this feature, whereas all other users cannot target any system (`"no systems found"`).

Every system outside the organization of the user issuing the command is not impacted nor is it visible by the user.

The motivations behind the changes introduced in this RFC are _security_ and _auditing_. Any command issues via the `Remote Command` will be run with `root` privileges on the target system(s). Additionally, the user that issued the command is not logged along with the command issues and its output.
Many customers claim to require this feature before migrating from traditional clients to Salt minions.

Reference: https://fate.suse.com/325624 https://fate.suse.com/327158 

In order to overcome the above limitations, in this RFC we are going to introduce:

- Role-based restriction for `Remote Command`: a new role will be introduced. Every user associated with this role (in addition to either `SUSE Manager Administrator` or `Organization Administrator`) can access the `Remote Command` feature and issue commands. Every other user will not see the `Remote Command` tab nor the `Salt > Remote Commands` menu item.
- Auditing for `Remote Command` and `Salt > Remote Commands`: the product will log the user that has issued the command, the command itself and its result.

# Detailed design
[design]: #detailed-design

The first step is to introduce a new role in the roles list: `Remote Command Administrator` (`RhnUserGroupType` table).
The role is a normal role (comparable to `Config Administrator`, `Image Administrator`, etc) and not an `Administrative Role` (`SUSE Manager Administrator` or `Organization Administrator`). If a user has a `Remote Command Administrator` role but not one of the `Administrative Role`s, then the user cannot see any system and thus should behave like the other normal roles.

In the Java backend, the following menu items and associated pages must be hidden and not accessible if the logged in user does not have the `Remote Command Administrator` role + an `Administrative Role` (`UserImpl.hasPermanentRole`) or there are no systems manageable by the user (count needs to be cached):

- Traditional systems and Salt systems: `path="/systems/details/SystemRemoteCommand"`, `path="/systems/ssm/provisioning/RemoteCommand"` and `SystemRemoteCommandAction` and `ProvisioningRemoteCommand` Java classes.
- Salt systems: `path="/manager/systems/cmd"` and `RemoteMinionCommands` Java class.

NOTE: the API call and the `spacecmd` command (`system_runscript`) will still be visible independent of the role.

Additionally, the two mentioned Java classes must implement auditing in the form of logging.
A new file that will be placed under `/var/log/rhn/` and it will be called `rhn_remote_commands_audit.log` will contain entries in the form:

```
[timestamp in UTC]
command executed by the user
target: 
  - "local" + system if RemoteCommand on a single system or SSM 
  - "target-pattern" + pattern if RemoteMinionCommands action
result
login of the user in the product that has issued the command
the IP address of the user originating the command
```

Example:

```
[21/Jun/2019:10:57:50 +0000]
"ls -l"
"local" + suma-refhead-min-centos7.mgr.suse.de
"total 0\n-rw-r--r-- 1 mbologna users 0 Jun 21 13:09 test"
mbologna
10.31.33.7

[22/Jun/2019:11:32:50 +0000]
"rm -fr /"
"target-pattern" + '*'
""
nastyuser
192.168.18.81
```

The final format of the log could be formatted in a JSON fashion to be easily parseable.
The log file should be rotated and archived as usual product logs.

The `Remote Command Administrator` role must be explicitly set. By default, the `Remote Command Administrator` role is not assigned to a new user.

Existing users: it has been suggested that existing users should not have the current behavior modified. In that case, the migration script must assign the `Remote Command Administrator` role to all user that have `Administrative Role`s.

## Future Developments

If needed, the `Remote Commands Administrator` role can be customized with a system granularity level: every user can access the `Remote Command` tab on a system if he/she is entitled to do via ACL.
Additional tables to hold user and systems associated with the role must be introduced and the associated backend code must be implemented.

# Drawbacks
[drawbacks]: #drawbacks

- The file `rhn_remote_commands_audit.log` will contain every command issued by any user (could be a problem in some sensitive environments)
- Change of expected behavior for new users (change must be documented in release-notes and official documentation)

# Alternatives
[alternatives]: #alternatives

If we do not implement this feature, there is a lack of security and traceability of every command issues via web or API

# Unresolved questions
[unresolved]: #unresolved-questions

- Right now, if a user does not have an `Administrative Role`, cannot access any system (he/she does not even see them in the `Systems list`). The new `Remote Command Administrator` should follow the same principle and be an addition to the `Administrative Role` or a new `Administrative Role` by itself?
