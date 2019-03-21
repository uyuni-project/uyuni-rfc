- Feature Name: Prevent systems from being registered twice
- Start Date: 2016-04-25
- Update Date: 2016-04-29
- Update Date: 2016-05-12

---
- Johannes Renner <jrenner@suse.com>
- Michael Calmer <mc@suse.com>

# Summary
[summary]: #summary

This RFC describes how we would like to technically prevent systems from being registered twice (traditional registration vs. Salt minion).

# Motivation
[motivation]: #motivation

A system managed by SUSE Manager is either managed in the traditional way **or** in the new way via Salt. There were many questions already about this topic prior to the release of SUSE Manager 3.0. In order to technically prevent systems from being registered twice we want to make sure that for every managed server there is only **one system entry** at any time.

# Detailed design
[design]: #detailed-design

Whenever the SUSE Manager server is processing a system registration (triggered either via traditional bootstrap script or minion start event), it would first see if there is already an existing entry for this system, which could be a traditionally managed system or a Salt minion. A unique identifier is used for this, the `machine-id`. This id is saved for Salt minions during the registration, so we will need to patch the traditional registration in order to make it store the machine id as well. In order to achieve that it will be necessary to migrate the database because the machine id field is currently part of the table `suseMinionInfo` that holds information relevant to minions only.

In case the server finds an existing entry with the same machine id, it would either delete this record before performing a new registration, overwrite the existing record and perform a `reactivation` or fail and do not allow this transaction. The following possible actions were identified and should be handled in the following way:

1. traditional => traditional without re-registration key

    In this case delete the old server and register a new one. We ignore a possible problem with a Cobbler System which may exist because this is the current bahavior and until now, nobody complained about this.

2. traditional => traditional with re-registration key

    Update the existing entry (reactivation).

3. salt => traditional with or without re-registration key

    Forbidden! Because we are unable to cleanup the old entry correctly regarding the salt key and files, we forbid these migration. The traditional stack should detect this and fail with an error message. The user should remove the system manually via the WebUI or API and register the system new.

4. salt => salt

    Update the existing entry (reactivation).

5. traditional => salt

    Update the existing entry (reactivation).


A `reactivation` should generate a new `secret` for the server record to invalidate the existing systemid file. In case an `rhnsd` daemon is still running on a system after its migration to `Salt`, it would not be problematic since the systemid file is now invalid. Users should manually shutdown and disable a potentially running `rhnsd` daemon though.

In addition to generate a new secret to invalidate the existing systemid file on the client, an additional check of the base entitlement should be added to python backend of the traditional stack. Only if the base entitlement is `enterprise_entitled` or `bootstrap`, execution of the XMLRPC functions should be allowed. Otherwise a meaningful message should be written into the logs and returned to the client if possible.

In case of a system being migrated from traditional `Management` to `Salt`, a re-registration will happen automatically similar to the currently available *reactivation* feature of the traditional stack.

There will be no changes being made to re-registrations using the same method: a traditional re-registration (without reactivation key) will always create a new system entry, re-registration of a minion will update an existing profile if necessary.

# Drawbacks
[drawbacks]: #drawbacks

- There is a database migration necessary before we can store the machine id for traditionally managed systems and the clients must run the updated software which send the machine_id. The new column can be populated via a hardware refresh of a system. This is not called automatically, but the machine_id does not fit into a software refresh. The idea is, to display the `machine_id` on the Hardware Details page and add a text **not available** together with a tip to install the latest tools on the client and run the hardware refresh.
- traditional => traditional without re-registration key will keep a Cobbler System record.

# Alternatives
[alternatives]: #alternatives

Another option that we considered is to change package spec files to make it impossible to install both client stacks at the same time (using `conflicts`). We decided against this approach mainly because it would cause problems as we would like to support the migration of traditional systems to Salt minions.

Apart from that there is the option to use the SCC/NCC credential instead of the machine id as the identifier to detect existing system entries. This id seems to be obsolete though at the moment and is currently not being queried from Salt minions during their registration. The effort needed to query and store this credential should be about the same in both cases.

# Unresolved questions
[unresolved]: #unresolved-questions

- Q: How do we handle already registered systems in production environments? Those will most likely be the ones to be migrated to Salt, but they don't have the machine id yet!
- A: We can populate the machine id column via a hardware profile update. The Hardware Details page should show a tip if the machine_id is not present.
- Q: How are we going to handle traditional stacks that are not providing the machine id, e.g. official Spacewalk or RHEL packages?
- A: n/a
