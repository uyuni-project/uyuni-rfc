- Feature Name: Remote Command Auditing
- Start Date: 2019-06-21
- RFC PR: TBD

# Summary
[summary]: #summary

Implement a role-based access model to access Remote Command for managed systems.

# Motivation
[motivation]: #motivation

A need coming directly the field has been brought to our attention: limiting what users can run via the Remote Command feature for security purposes.
This need is related to the fact that Remote Command is running any command with root privileges on the target system.
Any user having access to the web interface and the API of the product can issue Remote Command: this opens up the surface to any kind of malicious attacks.
Many customers claim to require this feature before migrating from traditional clients to Salt minions.
In addition, every action issued via the Remote Command feature is not logged.

Reference: https://fate.suse.com/325624 https://fate.suse.com/327158 

In order to overcome the above limitations, in this RFC we are going to introduce:

- Role-based restriction for Remote Command: a new role will be introduced. Every user associated with this role can access the Remote Command feature and issue commands. Every other user cannot access the feature.
- Auditing for Remote Command: the product will log the user that have issued the command, the command itself and its result.

# Detailed design
[design]: #detailed-design

Remote Command feature is by default enabled:

- for single systems or via System Set Manager for a group of systems (traditional and Salt ones) via web and via API (`system.scheduleScriptRun`)
- for all the systems that a user can manage (via Salt > Remote Commands)

Every user can only run commands on a system that he/she is already allowed to manage (there is already an ACL in place).

NOTE: all the systems (target '*') that a user can impact with Salt > Remote Commands are the ones registered under the same organization as the user.
Every system outside the organization is not impacted.

The first step is to introduce a new role in the roles list: "Remote Command Administrator" (`RhnUserGroupType` table).
The role is not an Administrative Role type (e.g. Organization admin) but rather a normal Role (comparable to Config Administrator, Image Administrator, etc).

In the Java backend, the following menu items and associated pages must be hidden and not accessible if the logged in user does not have the Remote Command Administrator" role (`UserImpl.hasPermanentRole`) or there are no systems manageable by the user (count needs to be cached):

- Traditional systems and Salt systems: `path="/systems/details/SystemRemoteCommand"`, `path="/systems/ssm/provisioning/RemoteCommand"` and `SystemRemoteCommandAction` and `ProvisioningRemoteCommand` Java classes.
- Salt systems: `path="/manager/systems/cmd"` and `RemoteMinionCommands` Java class.

NOTE: the API call nor the `spacecmd` command (`system_runscript`) will still be visible independent of the role.

Additionally, the two mentioned Java classes must implement auditing in the form of logging.
A new file that will be living under `/var/log/rhn/` and it will be called `rhn_remote_commands_audit.log` will contain entries in the form:

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

The Remote Command Administrator role must be explicitly set for non-Administrative Roles. By default, the Remote Command Administrator role is not assigned to a new user.

Existing users: it has been suggested that existing users should not have the current behavior modified. In that case, the migration script must assign the Remote Command Administrator role to all user that do not currently have Administrative Roles.

## Future Developments

If needed, the Remote Commands Administrator role can be customized with a system granularity level: every user can access the Remote Command tab on a system if he/she is entitled to do via ACL.
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
