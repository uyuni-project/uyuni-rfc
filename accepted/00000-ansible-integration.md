- Feature Name: Ansible-Gate
- Start Date: 2021-02-01
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

Ansible-Gate allows you to manage your existing Ansible nodes in Uyuni. This means that you are able to import an inventory and you can apply playbooks to nodes from this inventory.

# Motivation
[motivation]: #motivation

There are two main motivations for this:

1. A user might have some investment Ansible in the past but wants to switch to Uyuni now.
Ansible-Gate would offer a transition path for that. The user can start with the already existing playbooks, get familiar with Uyuni and then switch over. It is also be possible to manage clients with Salt and Ansible in parallel. 
2. Managing parts of the infrastructure in Ansible.
If it is not possible or not wanted to move everything to Uyuni, it is possible to just keep using Ansible for the few clients that cannot be transitioned.


_Describe the problem you are trying to solve, and its constraints, without coupling them too closely to the solution you have in mind. If this RFC is not accepted, the motivation can be used to develop alternative solutions._

# Detailed design
[design]: #detailed-design

This is the bulk of the RFC. Explain the design in enough detail for somebody familiar with the product to understand, and for somebody familiar with the internals to implement.

This section should cover architecture aspects and the rationale behind disruptive technical decisions (when applicable), as well as corner-cases and warnings. Whenever the new feature creates new user interactions, this section should include examples of how the feature will be used.

# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?

  * obscure corner cases
  * will it impact performance?
  * what other parts of the product will be affected?
  * will the solution be hard to maintain in the future?

# Alternatives
[alternatives]: #alternatives

* Interfacing AWX.
An alternative would be to use the API of AWX. While this would mean that all options of AWX would be available, it would also mean that we would need to make sure to always stay compatible with all versions used by users, breaking changes could be introduced by AWX and some features might even need to be implemented in AWX first before being able to use them in Uyuni.

# Unresolved questions
[unresolved]: #unresolved-questions

* Where should we move from here? Full integration of Ansible features? Moving Ansible integration to Spacewalk core? Fully interfacing AWX?
