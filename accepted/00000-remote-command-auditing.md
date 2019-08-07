- Feature Name: Remote Command Auditing
- Start Date: 2019-06-21
- RFC PR: TBD

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
- The API exposes the `system.scheduleScriptRun` to issue a command
- (Only for minions) a `Salt > Remote Commands` page to launch a command on minions by leveraging [Salt targeting](https://docs.saltstack.com/en/latest/topics/targeting/index.html) to identify the target(s)

There are the following rules already in place:

- Every user that with the proper role can access the tab and run a remote command on the selected system or a group of systems
- For every user registered to SUSE Manager, independent of the role, the menu item `Salt > Remote Commands` is accessible. Only the users that have the proper role can issue any command targeting the systems he/she is entitled to access with his/her role.
- The API is always exposed but checks for the role of the user issuing the command after the API is called

How roles profile the systems that a user can reach?

A user associated with the following roles can issue any command in the associated systems:

- Users associated with any of the `Administrative Roles` (`SUSE Manager Administrator` or `Organization Administrator`) can reach any system within the same organization
- Every other user (from now on: one does not have any of the above roles) can reach all the systems that he is been assigned to in his/her `System Groups` (this is regulated in the `rhnuserserverperms` table)

NOTE: starting from SUSE Manager 4.0, every command issued in the `Salt > Remote Commands` page is logged.

## Proposal

The motivations behind the changes introduced in this RFC are _security_ and _auditing_. Any command issues via the `Remote Command` will be run with `root` privileges on the target system(s).

To overcome the above limitations, in this RFC we are going to introduce a new role for enabling/disabling the `Remote Command(s)` feature for users that do not have `Administrative Roles`.

Users associated with `Administrative Roles` will not be impacted: they are assimilated as being `root` and they are allowed to do anything.

## Caveats

From a security point of view, if a user does not have any role associated to him/her the surface of the attack is still not negligible: the user can install and remove packages using SUSE Manager on the systems he/she is assigned to. Those packages can be ad-hoc crafted to contain {pre, post}-install script to execute what an attacker wants.

### Comparison with `Configuration Administrator`

A user having the `Configuration Administrator` role can create and apply states to the systems he/she is entitled to. This offers the same surface of attack, as an attacker could simply drop a `cmd.run` into the desired state.

Should `Remote Command Administrator` just another addition to the access control list of the `Configuration Administrator`?

# Detailed design
[design]: #detailed-design

## A new role `Remote Command Administrator`

The first step is to introduce a new role in the roles list: `Remote Command Administrator` (`RhnUserGroupType` table).
The role is normal (comparable to `Config Administrator`, `Image Administrator`, etc).

This translates to:

  1. For non-`Administrative Role` users that can manage the selected systems who do not have the `Remote Command Administrator Role`, `Remote Command` tab would be unavailable.

  2. `Salt > Remote Commands` is unavailable if the user is not associated with any `Administrative Role` or has not any assigned System Group.

In the Java backend:

  1. Traditional systems and Salt systems: `path="/systems/details/SystemRemoteCommand"`, `path="/systems/ssm/provisioning/RemoteCommand"` and `SystemRemoteCommandAction` and `ProvisioningRemoteCommand` Java classes
  2. Salt systems: `path="/manager/systems/cmd"` and `RemoteMinionCommands` Java class.

NOTE: the API call and the `spacecmd` command (`system_runscript`) will still be visible independent of the role.

## Re-using `Configuration Administrator`

In this case, the Java backend changes the ACL for the `Remote Command(s)` page(s) to honor the `Configuration Administrator` ACL.
This approach would be the clearest and consistent security-wise.

The downside of it is that, for every `Remote Command(s)` ACL check, we should add an additional check for the user role:

```
select ugt.label as role
  from rhnUserGroup ug,    
        rhnUserGroupType ugt,
        rhnUserGroupMembers ugm
  where ugm.user_id = :user_id       
    and ugm.user_group_id = ug.id   
    and ug.group_type = ugt.id
```

## Future Developments

If needed, the `Remote Command Administrator` role can be customized with a system granularity level: every user can access the `Remote Command` tab on a system if he/she is entitled to do via ACL.
Additional tables to hold user and systems associated with the role must be introduced and the associated backend code must be implemented.

# Drawbacks
[drawbacks]: #drawbacks

Users are probably using `Administrative Roles` excessively because of some gap in the roles spectrum. This change might not be what a user wants: a stripped-down `Administrative Role` with no access to `Remote Commands` (see next section).

# Alternatives
[alternatives]: #alternatives

By reading the two fate entries linked it seems that customers are looking for a solution to disable Remote Commands for users within the Administrative Roles (SUSE Manager Administrator and Org Administrator). Those users are assimilated as root` so they cannot be changed.

Meeting halfway would be to offer a way to disable Remote Command(s) for users with Administrative Roles.

# Unresolved questions
[unresolved]: #unresolved-questions

- Do we want to decrease the power of the `Administrative Roles` by adding an option to hide `Remote Command(s)` or do we want `non-Administrative Roles` to be required to have the `Remote Command Administrator`?
- Is the `Configuration Administrator` to be merged with the `Remote Command Administrator`?