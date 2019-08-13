- Feature Name: Accept and Manage GPG Keys with Salt
- Start Date: 2019-07-19
- RFC PR: https://github.com/uyuni-project/uyuni-rfc/pull/9

# Summary
[summary]: #summary

When a customer uses an external repository he need to trust the GPG key from
this repository. This key has to be
installed on the minions. When using the bootstrap script we have a solution
but we also need one for onboarding via UI and API.


# Motivation
[motivation]: #motivation

When installing signed packages on a system, the package manager typically
check, if the signature is ok and the key which signed the package is
trusted by the administrator.
As this is the default in most of the OSes, it is impossible to install a
package when the signing key is not installed as trusted on that system.

Uyuni should be able to install all GPG keys defined as trusted for this
system during registration and manage them during the lifetime of the system.

As there is the possibility that a package with an unknown signature is part
of the bootstrap repository, the keys should be trusted before installing
packages from the bootstrap repository.

# Detailed design
[design]: #detailed-design

## GPG key management in salt for all supported package managers

For easier management of GPG keys, salt should handle them in modules.
In the `aptpkg` module for Debian package management the following functions
exists already:

* get_repo_keys()
* add_repo_key()
* del_repo_key()

A rpm based implementation should be added to `rpm_lowpkg` module and also a
state module for managing GPG keys.
It should be possible to specify a URL (salt or https(s)) to download the
key from.


## Implement a formula with forms for managing GPG keys

A Formula with Forms should be written to define trusted GPG keys in the UI.
It could just have fields to enter a list of file names similar to the definition
in a bootstrap script.
When the repo_key state support armored keys directly the whole key could be
defined as an option. This may require adaptions to the formula code to offer a
text area component.
If possible, we should allow to paste a URL where to download the Key from.
Downloading a key is not as secure as pasting the key directly into the formula,
but this is up to the administrator which way he choose to provide the key.

Formulas can be assigned to system groups, which can be assigned to an activation
key. Using this mechanism they could become active at the initial registration.

## Offer to trust GPG keys before registration (optional)

Before the system is registered, it has no minion id where pillar data could
be assigned to. When bootstrapping a system there should be an option to add
a list of keys unique to this task.

Such a list should be applicable to UI and API bootstrap call.
This list is not preserved for later configuration management.


# Drawbacks
[drawbacks]: #drawbacks

- To offer GPG keys before registration you need to specify GPG keys for every
  bootstrap action. This allow maximal flexibility, but at least in the UI
  there is no way to define a general rule which applies to every bootstrap action.
  When using the API a reusable script could be written.
  The implementation effort is high, as UIs, backends and APIs needs to be changed.
  The usefulness is questionable as at this early point in time only trusted RPMs
  should be installed and the bootstrap process only install dedicated packages.
  The list cannot be defined by the user. Additionally the GPG check for the bootstrap
  repo is `off` and secured by an SSL connection and the fact that only `root`
  on the Server can manipulate the content of the repo.

# Alternatives
[alternatives]: #alternatives

- Define GPG keys by Operating System to allow general rules. This option
  prevent flexibility when a specific system must deviate from the general
  rule. The flexible approach was preferred for a security feature where an
  exact selection for every system is important.

# Unresolved questions
[unresolved]: #unresolved-questions

- none.
