- Feature Name: Salt Single Spec Packaging
- Start Date: 2025-01-13

# Summary
[summary]: #summary

Use [Python RPM Macros](https://github.com/openSUSE/python-rpm-macros) in Salt packaging. This enables us to build Salt from one spec file for multiple Python flavors.

# Motivation
[motivation]: #motivation

There are multiple reasons for building multiple Python flavors for Salt. A big part of Salt is a library that can be used by other Python programs. These programs might use a Python version that newer than the one we currently build Salt against. For Salt-the-application, a single Python flavor could be enough. Unlike Salt-the-library, Salt-the-application can't be co-installed in a useful manner. Still, it makes sense for us to allow Salt-the-application to run with different Python flavors and let the user choose between them. This allows for a transition from Python 3.x to Python 3.y when it's convenient for a user. Users that only write Salt state files don't need to care about the Python flavor, but those users who have their custom Salt modules need to make sure everything plays well together.

This RFC does not apply to the Salt Bundle. It strictly targets the classic Salt package that we maintain for openSUSE, SUSE Linux (Enterprise) and some SUSE Multi-Linux Manager Client distributions. This RFC is related to [RFC#00102 Upgrade to Salt 3008](https://github.com/uyuni-project/uyuni-rfc/blob/f403c8db1707fb828dd708c8e67dabff539d4d10/accepted/00102-upgrade-to-salt-3008.md).

# Detailed design
[design]: #detailed-design
## Overall Structure
Salt makes use of [Python RPM Macros](https://github.com/openSUSE/python-rpm-macros) to build sub-packages for different Python flavors. There is one sub-package for Salt-the-library (`python3-salt`) per flavor. The rest of Salt-the-application packages are: `salt-api`, `salt-cloud`, `salt-master`, `salt-minion`, `salt-proxy`, `salt-ssh`, `salt-syndic`. Switching between the Python flavor to use with these scripts is done with `update-alternatives` for SLE15 and Leap and using `alts` in Tumbleweed.

For example, we now build the following sub-packages for Leap 15.5:
- `python3-salt-3006.0-<release>.x86_64.rpm`
- `python311-salt-3006.0-<release>.x86_64.rpm`
- `salt-3006.0-<release>.x86_64.rpm`
- `salt-api-3006.0-<release>.x86_64.rpm`
- `salt-cloud-3006.0-<release>.x86_64.rpm`
- `salt-master-3006.0-<release>.x86_64.rpm`
- `salt-minion-3006.0-<release>.x86_64.rpm`
- `salt-proxy-3006.0-<release>.x86_64.rpm`
- `salt-ssh-3006.0-<release>.x86_64.rpm`
- `salt-syndic-3006.0-<release>.x86_64.rpm`
- `salt-bash-completion-3006.0-<release>.noarch.rpm`
- `salt-doc-3006.0-<release>.x86_64.rpm`
- `salt-fish-completion-3006.0-<release>.noarch.rpm`
- `salt-standalone-formulas-configuration-3006.0-<release>.x86_64.rpm`
- `salt-transactional-update-3006.0-<release>.x86_64.rpm`
- `salt-zsh-completion-3006.0-<release>.noarch.rpm`

### Switching between Python flavors
The idea is to offer choice to our users, in a predictable way. It's possible to co-install different Salt-the-library (i.e. `python<flavor>-salt`) flavors. The user is able to choose the Python flavor to use on their `salt-master`, `salt-minion` and other scripts by:

#### SLE and Leap 15 family

On SLE/Leap 15 family, we use `update-alternatives` to control the Python favor to use with the different salt scripts:

```
# update-alternatives --config salt-minion
There are 2 choices for the alternative salt-minion (providing /usr/libexec/salt/salt-minion).

  Selection    Path                                Priority   Status
------------------------------------------------------------
* 0            /usr/libexec/salt/salt-minion-3.11   311       auto mode
  1            /usr/libexec/salt/salt-minion-3.11   311       manual mode
  2            /usr/libexec/salt/salt-minion-3.6    36        manual mode

Press <enter> to keep the current choice[*], or type selection number:
```

#### SLFO and Tumbleweed
Alternatively, we use `alts` in SLFO and Tumbleweed:

```console
#  # salt-minion --version
salt-minion-3.11 3006.0 (Sulfur)

# alts -l salt-minion
Binary: salt-minion
Alternatives: 3
  Priority: 312   Target: /usr/libexec/salt/salt-minion-3.12
  Priority: 313   Target: /usr/libexec/salt/salt-minion-3.13
  Priority: 1311*  Target: /usr/libexec/salt/salt-minion-3.11

# alts -n salt-minion -p 312

# salt-minion --version
salt-minion-3.12 3006.0 (Sulfur)
```

## Our Python3 Flavors in SUSE Linux Enterprise / openSUSE Leap
Salt Project's 3006 releases don't officially support Python 3.6. We made our Salt 3006.0 release compatible with Python 3.6, but we anticipate problems doing the same for Salt 3008. Following [RFC#00102](https://github.com/uyuni-project/uyuni-rfc/blob/f403c8db1707fb828dd708c8e67dabff539d4d10/accepted/00102-upgrade-to-salt-3008.md), Salt based on Python 3.11 will be added to a new SLE Module. Until this Module is created, and for an overlap period afterwards, Salt based on Python 3.6 is shipped in SLE 15 Basesystem. Eventually, we will disable building the Python 3.6 flavor for Salt. The timeline is not yet determined and will be coordinated with the SUSE Linux Enterprise product management team.

openSUSE Leap shares the Salt packages with SUSE Linux Enterprise and inherits the Python3 flavors choice.

For openSUSE Tumbleweed and openSUSE MicroOS we build for all available Python flavors, i.e. we do *not* re-configure `%pythons`.

## Compatibility Macros

Our `salt.spec` defines fallback RPM Macros for RedHat-family distributions. Additionally, `salt.spec` opts out of the single spec macros when building against old SUSE Linux Enterprise 15 service packs that don't support them.

# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?

- More sub-packages can be confusing users. Providing the old package names as rpm symbols should ease the transition.

# Alternatives
[alternatives]: #alternatives
- We only build one sub-package per component as we do right now. The problem is that we can't release both a Python3.6 based and a Python3.11 based Salt-the-application from the same spec file. While these sub-packages are released in different SLE Modules, they are built together.
- Different spec files for different Python flavors

# Unresolved questions
[unresolved]: #unresolved-questions

- …
