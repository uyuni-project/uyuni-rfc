- Feature Name: Salt Single Spec Packaging
- Start Date: 2025-01-13

# Summary
[summary]: #summary

Use [Python RPM Macros](https://github.com/openSUSE/python-rpm-macros) in Salt packaging. This enables us to build Salt from one spec file for multiple Python flavors.

# Motivation
[motivation]: #motivation

There are multiple reasons for building multiple Python flavors for Salt. A big part of Salt is a library that can be used by other Python programs. These programs might use a Python version that newer than the one we currently build Salt against. For Salt-the-application, a single Python flavor could be enough. Unlike Salt-the-library, Salt-the-application can't be co-installed in a useful manner. Still, it makes sense for us to build Salt-the-application for different Python flavors and let the user choose between them. This allows for a transition from Python 3.x to Python 3.y when it's convenient for a user. Users that only write Salt state files don't need to care about the Python flavor, but those users who have their custom Salt modules need to make sure everything plays well together.

This RFC does not apply to the Salt Bundle. It strictly targets the classic Salt package that we maintain for openSUSE, SUSE Linux (Enterprise) and some SUSE Multi-Linux Manager Client distributions. This RFC is related to [RFC#00102 Upgrade to Salt 3008](https://github.com/uyuni-project/uyuni-rfc/blob/f403c8db1707fb828dd708c8e67dabff539d4d10/accepted/00102-upgrade-to-salt-3008.md).

# Detailed design
[design]: #detailed-design
## Overall Structure
Salt makes use of [Python RPM Macros](https://github.com/openSUSE/python-rpm-macros) to build sub-packages for different Python flavors. There is one sub-package for Salt-the-library (`python3-salt`) per flavor, as well as one sub-package per flavor for other sub-packages containing Python code. These other sub-packages are: `salt-api`, `salt-cloud`, `salt-master`, `salt-minion`, `salt-proxy`, `salt-ssh`, `salt-syndic`. For backwards-compatibility, the new flavored sub-packages _provide_ the old sub-package name.

For example, we now build the following sub-packages for Leap 15.5:
- `python3-salt-3006.0-<release>.x86_64.rpm`
- `python3-salt-api-3006.0-<release>.x86_64.rpm`
- `python3-salt-cloud-3006.0-<release>.x86_64.rpm`
- `python3-salt-master-3006.0-<release>.x86_64.rpm`
- `python3-salt-minion-3006.0-<release>.x86_64.rpm`
- `python3-salt-proxy-3006.0-<release>.x86_64.rpm`
- `python3-salt-ssh-3006.0-<release>.x86_64.rpm`
- `python3-salt-syndic-3006.0-<release>.x86_64.rpm`
- `python311-salt-3006.0-<release>.x86_64.rpm`
- `python311-salt-api-3006.0-<release>.x86_64.rpm`
- `python311-salt-cloud-3006.0-<release>.x86_64.rpm`
- `python311-salt-master-3006.0-<release>.x86_64.rpm`
- `python311-salt-minion-3006.0-<release>.x86_64.rpm`
- `python311-salt-proxy-3006.0-<release>.x86_64.rpm`
- `python311-salt-ssh-3006.0-<release>.x86_64.rpm`
- `python311-salt-syndic-3006.0-<release>.x86_64.rpm`
- `salt-3006.0-<release>.x86_64.rpm`
- `salt-bash-completion-3006.0-<release>.noarch.rpm`
- `salt-doc-3006.0-<release>.x86_64.rpm`
- `salt-fish-completion-3006.0-<release>.noarch.rpm`
- `salt-standalone-formulas-configuration-3006.0-<release>.x86_64.rpm`
- `salt-transactional-update-3006.0-<release>.x86_64.rpm`
- `salt-zsh-completion-3006.0-<release>.noarch.rpm`

Note: both `python3-salt-master-3006.0-<release>.x86_64.rpm` and `python311-salt-master-3006.0-<release>.x86_64.rpm` provide the symbol `salt-master = 3006.0-<release>`.

### Per-flavor Dependencies and Conflicts
The idea is to offer choice to our users, in a predictable way. It's possible to co-install Salt-the-library (i.e. `python<flavor>-salt`), but not Salt-the-application (i.e. `python<flavor>-salt-*`). It's also not possible to mix-and-match different flavors of individual components of Salt-the-application (e.g. `python<flavor-A>salt-api` with `python<flavor-B>salt-master`).

On the implementation level, this means each `python<flavor>-salt-master` sub-package _provides_ and _conflicts_ the rpm symbol `salt-master`. Each component sub-package _requires_ Salt-the-library with the same flavor. Dependencies between component sub-packages are implemented with _requires_, using the Python flavor. 

For example, let's take a look at `python3-salt-master` and `python3-salt-api` on Leap 15.5 again.
```text
% rpm -q --requires python3-salt-api
[...]
/usr/bin/python3.6
python3-CherryPy >= 3.2.2
python3-salt = 3006.0-lp155.76.1
python3-salt-master = 3006.0-lp155.76.1
[...]
% rpm -q --provides python3-salt-master
config(python3-salt-master) = 3006.0-lp155.76.1
python3-salt-master = 3006.0-lp155.76.1
python3-salt-master(x86-64) = 3006.0-lp155.76.1
salt-master = 3006.0-lp155.76.1
% rpm -q --conflicts python3-salt-master
salt-master = 3006.0-lp155.76.1
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
