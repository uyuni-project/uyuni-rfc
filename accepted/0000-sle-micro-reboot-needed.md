- Feature Name: SLE Micro: report when a reboot is needed
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
To be able to have up-to-date information regarding reboot needed, we need to update this information after every state apply.
For that, this proposed solution is based on the following steps:
 - Create an execution module to check if a reboot is required
 - After every state apply run this execution module
 - Store the result in a postgresql column
 - Report reboot needed in the UI based on this column

[This draft Pull Request](https://github.com/SUSE/spacewalk/pull/19036) can help to understand the general idea, and the details are explained below.

### The execution module

To check if a reboot is needed we can use `snapper` to determine if the default snapshot is not active. If so, a reboot is pending. One can find more details about this strategy in [Jira](https://jira.suse.com/browse/CSD-95) discussion. The execution module based on this strategy can be seen [here](https://github.com/SUSE/spacewalk/blob/3c2031bac04fbe88cd5b6692a3e511a457cdf5e7/susemanager-utils/susemanager-sls/src/modules/rebootutil.py).

### Running the module after every state apply

There are at least two possible approachs to run the execution module after every state apply:

1. Create an `sls` file to run the module trough `mgrcompat.module_run`, include this `sls` in the context of all other state files (as example, in the draft PR, it is included in `pkginstall` and `pkgremove`), and consider it when parsing the results in `JobReturnMessageAction`.

or

2. When parsing any state apply results in `JobReturnMessageAction`, if there is an SLE micro system involved, make an additional remote call to execute the module checking if a reboot is needed and then store the result. Although this approach adds an extra remote call, it simplifies the implementation and doesn't involve changes in the existing `sls`, also reducing the risk of the change.


# Drawbacks
[drawbacks]: #drawbacks

Including the new module in the existing `sls` files will affect other parts of the product and some unexpected behaviour in this module can eventually propagate to other features.
Making an extra call after every state apply may have an impact on performance.

# Alternatives
[alternatives]: #alternatives

One alternative to be considered is to not have a synchronization mechanism and just call the module asynchronously from the UI, having hot loaded information being displayed to the user.

# Unresolved questions
[unresolved]: #unresolved-questions

- Is there a way to run the execution module after state apply in the same remote call without having to change all the `sls` files?

- Is it possible to have a parameter when running `state.apply` to indicate that no new transaction is necessary and thus make the module work in `state.apply`?  Currently the execution module is working only when running in isolation. When running `state.apply`, by default in SLE Micro, the state is going to be executed inside a new transaction and things like `dbus` used by `snapper` are not available in this new transaction, causing the command to fail.
