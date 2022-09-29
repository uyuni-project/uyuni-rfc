- Feature Name: SLE Micro - report when a reboot is needed
- Start Date: 2021-09-23

# Summary
[summary]: #summary

After a system level change in SLE Micro, SUSE Manager should indicate in the UI when a reboot is needed.

# Motivation
[motivation]: #motivation

Currently, for SLE Micro, we display the following message on the detail page: `OS with transactional updates: please reboot after any packages and/or channel changes`.

This is not ideal when it comes to usability. The user is responsible for knowing when a reboot is needed, and scheduling those reboots.


# Detailed design
[design]: #detailed-design

The SLE Micro uses transactional updates. Transactional updates are atomic (all updates are applied only if all updates succeed) and support rollbacks. They don't affect a running system as no changes are activated until after the system is rebooted.
To be able to have up-to-date information regarding reboot needed, we need to constant read this information from the system.
For that, this proposed solution is based on the following steps:
 - Create a beacon module to constantly check if a reboot is required
 - If the reboot required information changes in the minion, notify Suse Manager
 - Store the status in postgresql
 - Report reboot needed in the UI based on this column

[This Pull Request](https://github.com/SUSE/spacewalk/pull/19036) can help to understand the general idea, and the details are explained below.

### The beacon module

The beacon module will use `transactional_update` module to check for [pending transactions](https://docs.saltproject.io/en/3004/ref/modules/all/salt.modules.transactional_update.html#salt.modules.transactional_update.pending_transaction), and based on its result determine if a reboot is required for that system. Initially the beacon will be configured to run every 10 seconds.

In the beacon, the information will be stored in `__context__` in order to avoid: (a) repeatedly firing the reboot needed event, and (b) unnecessary runs of the `pending_transactions` module. If a reboot is required, the only way to remove the indication is to reboot the system, and rebooting the system will clear the `__context__`. Therefore, it is only necessary to run the check if a reboot required indication has not yet been identified or if an event was not yet been fired (first run, when the `__context__` is clean).

The beacon module will also reiterate (resend the event) every 60 minutes if a reboot is still required.

The Java Salt Reactor will be adapted to identify events coming from this beacon module and update the reboot needed information in postgres. 

The query to identify `Requiring reboot` systems will be updated to consider the new column together with the current strategy, in order to check if a system needs to be rebooted and, if so, display the message in the UI.

# Drawbacks
[drawbacks]: #drawbacks

# Alternatives
[alternatives]: #alternatives

# Unresolved questions
[unresolved]: #unresolved-questions
