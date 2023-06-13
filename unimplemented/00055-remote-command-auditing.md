- Feature Name: Remote Command Auditing
- Start Date: 2019-06-21
- RFC PR: https://github.com/uyuni-project/uyuni-rfc/pull/8

# Unimplemented note

This RFC was not ultimately implemented. It is still archived here for historical purposes.

# Summary
[summary]: #summary

Implement a role-based access model to access `Remote Command` for managed systems.

# Motivation
[motivation]: #motivation

Many customers claim to require a role differentiation for `Remote Command(s)` before migrating from traditional clients to Salt minions.

Reference: https://fate.suse.com/325624 https://fate.suse.com/327158

## Current implementation

At the time of the writing, there are three features to issue a remote command on a managed system or a group of systems registered to the product:
- A `Remote Command` tab is present in the details section of a traditional or minion system (or a `System Set Manager` group)
- `spacecmd` offers `system_runscript` that invokes the API `system.scheduleScriptRun` to issue a command. The API checks for the user role before issuing the command and outputs an error if the user is not entitled
- (Only for minions) a `Salt > Remote Commands` page to launch a command on minions by leveraging [Salt targeting](https://docs.saltstack.com/en/latest/topics/targeting/index.html) to identify the target(s)

There are the following rules already in place:

- Every user that with the proper role can access the tab and run a remote command on the selected system or a group of systems
- For every user registered to SUSE Manager, independent of the role, the menu item `Salt > Remote Commands` is accessible. Only the users that have the proper role can issue any command targeting the systems he/she is entitled to access with his/her role.
- The API is always exposed but checks for the role of the user issuing the command after the API is called

How roles profile the systems that a user can reach?
A user associated with the following roles can issue any command in the associated systems:

- Users associated with any of the `Administrative Roles` (`SUSE Manager Administrator` or `Organization Administrator`) can reach any system within the same organization
- Every other user (from now on: one does not have any of the above roles) can reach all the systems that he is been assigned to in his/her `System Groups` (this is regulated in the `rhnuserserverperms` table)

Any command issues via the `Remote Command` will be run with `root` privileges on the target system(s).

NOTE: starting from SUSE Manager 4.0, every command issued in the `Salt > Remote Commands` page is logged.

## Proposal

The motivations behind the changes introduced in this RFC are _security_ and _auditing_. 
In this RFC we are going to introduce:
- a new role for enabling/disabling the `Remote Command(s)` feature for users that do not have `Administrative Roles`. Users associated with `Administrative Roles` will not be impacted: they are assimilated as being `root` and they are allowed to do anything.
- a new configuration option (`rhn.conf`) that disables the `Remote Command` tab and `Salt > Remote Commands` for every user in the system

## Caveats

From a security point of view, if a user does not have any role associated to him/her the surface of the attack is still not negligible: the user can install and remove packages using SUSE Manager on the systems he/she is assigned to. Those packages can be ad-hoc crafted to contain {pre, post}-install script to execute what an attacker wants. Likewise, if a user is a `Configuration Administrator`, he/she can create and apply states to the systems he/she is entitled to. This offers the same surface of attack, as an attacker could simply drop a `cmd.run` into the desired state.

# Detailed design
[design]: #detailed-design

## A new role `Remote Command Administrator`

The first step is to introduce a new role in the roles list: `Remote Command Administrator` (`RhnUserGroupType` table).
The role is normal (comparable to `Config Administrator`, `Image Administrator`, etc).

This translates to:

  1. For non-`Administrative Role` users that can manage the selected systems who do not have the `Remote Command Administrator Role`, `Remote Command` tab would be unavailable.

  2. `Salt > Remote Commands` will be available but no system will be impacted by the command launched by the user.

In the Java backend:

  1. Traditional systems and Salt systems: `path="/systems/details/SystemRemoteCommand"`, `path="/systems/ssm/provisioning/RemoteCommand"` and `SystemRemoteCommandAction` and `ProvisioningRemoteCommand` Java classes
  2. Salt systems: `path="/manager/systems/cmd"` and `RemoteMinionCommands` Java class.

The role `Remote Command Administrator` will be enabled for all non-`Administrative` existing users. It will be disabled by default for new users: it must be manually enabled by the Administrator that creates the user.

## A new config option `java.allow_remote_commands`

A new `rhn.conf` will be introduced that disables the `Remote Command` tab and the `Salt > Remote Commands` feature. Codepaths are the same as the previous section, but it will be enforced for every user.
The option will be enabled by default for consistency with the current situation.

## Future Developments

If needed, the `Remote Command Administrator` role can be customized with a system group granularity level: every user can access the `Remote Command` tab on a system if he/she is entitled to do via ACL.
Additional tables to system groups associated with the role must be introduced and the associated backend code must be implemented. In order to enable `Remote Command(s)` on a system group, a minimum of the `System Group Administrator` will be required.

# Drawbacks
[drawbacks]: #drawbacks

# Alternatives
[alternatives]: #alternatives

- Assimilate the `Remote Command Administrator` to `Configuration Administrator`. We decided not to follow this path at the moment and clearly distinguish between the two roles.

# Unresolved questions
[unresolved]: #unresolved-questions
