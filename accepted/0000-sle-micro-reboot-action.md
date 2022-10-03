- Feature Name: SLE Micro - reboot action
- Start Date: 2021-09-29

# Summary
[summary]: #summary

Provide a suitable approach to handle reboot action in SLE Micro

# Motivation
Transactional systems, like SLE micro, use `transactional-update` to perform management actions including reboot. Transactional update itself supports several different reboot methods, configurable via the REBOOT_METHOD configuration option in `transactional-update.conf`. In order to put Suma in control of the reboot of its managed systems, it is necessary to configure transactional systems in a proper way and carry out the reboot action according to their particularities.

# Detailed design
[design]: #detailed-design

This proposed solution is based on the following steps:
 - Configure transactional systems to use `systemd` as reboot method
 - Disable `transactional-update-timer` and `rebootmgr` services.
 - Use `transactional-update` module to perform the reboot in transactional systems

### Systemd as reboot method
As mentioned, `transactional-update` supports different reboot methods. By default, reboot method is set to `auto`, which means that `rebootmgrd` will be used to reboot the system according to the configured policies if the service is running, otherwise systemctl reboot will be called.

The proposal here is to set, during bootstrap on Suma, `systemd` as `REBOOT_METHOD` for transactional systems, if the system is in its default configuration. The idea behind this strategy is to put Suma on control of the reboot action, considering that `systemd` should perform the reboot immediately. 

Otherwise, the only thing Suma will be able to do is to ask for a reboot and it will be managed in the peculiarities of each reboot method. Not having control of when the reboot should happen, also takes away from Suma the ability to perform the reboot on its own maintenance windows, which is not the ideal configuration.

The user must be able to change reboot method at any time and SUSE Manager will keep it. In any case, we should alert in the documentation that using any method different from `systemd` may cause undesired behavior.

### Disable `transactional-update.timer` and `rebootmgr` services.

If the system was in its default configuration, and we changed the reboot method in bootstrap, we need to disable services that deals with reboot but are not controlled by Suma.

By default, `transactional-update.timer` is configured to automatically reboot the systems each day. The configuration is on `/etc/systemd/system/timers.target.wants/transactional-update.timer`. To avoid undesired reboots in managed systems, this auto reboot service should be disabled.

`rebootmgr` service allows the user to define maintenance windows where the pending reboots should be performed. This also can cause undesired behavior when the system is managed by Suma, so, if we change the reboot method to put Suma in control, we should also disable `rebootmgr` service.

Both these services can be re-enabled by users if they change the reboot method to others that needed them to be enabled. SUSE Manager will not change the configuration of this service after onboard.

### Use `transactional-update` module to perform the reboot

In the end, whatever is configured for reboot method, Suma should perform reboot actions calling the [reboot](https://docs.saltproject.io/en/3004/ref/modules/all/salt.modules.transactional_update.html#salt.modules.transactional_update.reboot) function of `transactional_update` salt module. If `systemd` is configured, the system will reboot immediately and Suma will be aware of the reboot. If other method is configured, Suma will only ask for a reboot and there is no guarantee of when this reboot will be performed. If the reboot doesn't take longer than 6 hours the action will be updated as successfully completed in Suma. But, if there is any peculiarity in the reboot method used (such as a specific maintenance window), and the reboot takes longer than 6 hours, the action will be updated as failed in Suma.

This behavior should be documented to make customers aware with the advice either to stay with `systemd` and let Suma decide when to reboot or they should schedule reboot actions only at a time when their configured method allows to reboot.

# Drawbacks
[drawbacks]: #drawbacks

# Alternatives
[alternatives]: #alternatives

- Create a `suma` reboot method for `transactional-update`. If the user configure the system to use any other method, reboot wouldn't be allowed in Suma to avoid undesired behavior. This alternative would make it necessary to patch `transactional-update` and the only benefit seems to be having a guarantee that Suma only try to perform reboot if it is in control of it.

# Unresolved questions
[unresolved]: #unresolved-questions

- With this proposed approach, we are not covering properly potential users with specific reboot methods configured on systems they manage using Suma, and the plan is to only alert them in documentation about possible problems. Is this scenario of using Suma to manage transactional systems with their own reboot methods really relevant? Does it make sense to use Suma to manage the system but doesn't put it in control of the reboot? If so, we will probably need a next version of this feature improving the support of other reboot methods.
- What to do when there is no pending transaction, but it is necessary to reboot the system? As we run the reboot in the context of `salt x transactional_update.apply activate_transaction=True`, a reboot is only scheduled if there is a pending transaction. So, it is necessary to find an alternative to make it work.
- How to perform reboot in action chains, in order to only perform the reboot action after the current transaction is finished and not as part of it?
