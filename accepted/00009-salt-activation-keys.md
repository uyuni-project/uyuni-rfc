* Feature Name: Salt Activation Keys
* Start Date: 2016.01.27

---
* Johannes Renner <jrenner@suse.com>
* Matei Albu <malbu@suse.com>
* Duncan Mac-Vicar P. <dmacvicar@suse.com>
* Michael Calmer <mc@suse.com>

# Summary
[summary]: #summary

This RFC describes how the old concept of Spacewalk activation keys is mapped to Salt system.

# Motivation
[motivation]: #motivation

Activation keys are used to provide the system initial:

* Organization Assignment
* Groups
* Software Channels
* Contact method
* Extra packages
* Configuration channels

For onboarding Salt minions one still need to do some initial assignments.

# Detailed design
[design]: #detailed-design

* The main idea is to fully reuse activation keys, because they are already widely deployed.
* We will duplicate some python code that "applies" an activation key in Java.
  * Most of that functionality (assign channel, etc) is already well serviced on the Java side
* Once we find what registration key a minion has, we will "apply it"

* In a first stage the key will be look into the grains, which can be used for automation and still requires us to implement the code to apply the keys on minions

# Drawbacks
[drawbacks]: #drawbacks

# Alternatives
[alternatives]: #alternatives

* Something using pure sls files.
  * Has to many unresolved questions like how to apply channel assignment or group assignment (chicken-egg problem).

# Unresolved questions
[unresolved]: #unresolved-questions

* We can't get the grains or any data from a minion before accepting the key.
  This is not a problem when bootstrapping via ssh, because we can preseed accepted keys and we can ask the activation key before.
  However, for minion in the accept queue, *who will accept them?*
  * For now we have decided that the Organization Administrators will be able to accept keys for all incoming minions, and then we may add an extra role
  * Still gives the problems org can steal minions intended to be registered for a different organization



