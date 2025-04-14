- Feature Name: Apply Service Packs to SLES and/or openSUSE Leap using SSM
- Start Date: 2023-03-10

# Summary
[summary]: #summary

Provice an easy mechanism to upgrade SLES and/or openSUSE Leap systems from one service pack the next one

# Motivation
[motivation]: #motivation

- Users of openSUSE and SUSE Linux Enterprise Server (SLES) need to update their versions. When doing it for a large installed base, an easier procedure could be performed using SSM.
- As a sysadmin  I want to upgrade my installed base of OpenSUSE/SLES servers to latest version (i.e. SP4 to SP5) using SSM so that I can do it in less time and with control on which systems are selected.
- The outcome would be to have updates for my systems running from Uyuni / SUSE Manager for a set of systems selected with SSM. I could later on review status and check that everythign went fine, or any issue found. 


# Detailed design
[design]: #detailed-design

Apply `zypper migration` to systems selected in SSM

# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?

  * No corner cases observed

# Alternatives
[alternatives]: #alternatives

- Manual upgrade. (Slow, cumbersome and error prone)
- Customized script using API (Common use case, could be included in product)
- Using SALT states (not sure they can apply to SSM selections)

# Unresolved questions
[unresolved]: #unresolved-questions

- None so far.
