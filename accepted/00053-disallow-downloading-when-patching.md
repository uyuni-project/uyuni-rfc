- Feature Name: disallow-downloading-when-patching
- Start Date: 29-03-2919
- RFC PR: https://github.com/uyuni-project/uyuni-rfc/pull/6

# Summary
Optionally fail package installations and patch applications if they require any downloading.

This is limited to minions on SUSE-based distros.

# Motivation
Minions with limited connectivity options might have little bandwidth available or bandwidth usage could come with a high cost (eg. in remote areas). In those cases we want users to be fully in control of when downloading happens, eg., to schedule that during off-peak hours (see https://github.com/uyuni-project/uyuni-rfc/pull/5). This RFC is about giving users the possibility to prevent package managers' default behavior of downloading at installation time.

Package installation and patch application Actions should thus fail in case packages were not previously downloaded (if so configured).

# Detailed design
- two new functions are implemented in [zypper's execution module](https://github.com/openSUSE/salt/blob/openSUSE-2018.3.0/salt/modules/zypper.py). Given a list of packages or patches, return `True` if any downloading is required

Those functions can leverage `zypper`'s estimation of downloaded bytes in dry-run mode to determine if any downloading is needed:

```
minion:~ # zypper --non-interactive --xmlout install --dry-run zsh
<?xml version='1.0'?>
<stream>

...

<install-summary download-size="0" space-usage-diff="7389792" packages-to-change="1">

...
</stream>
```

Those functions should accept a subset of parameters from the respective original state modules ([pkg.installed](https://docs.saltstack.com/en/2018.3/ref/states/all/salt.states.pkg.html#salt.states.pkg.installed) and [pkg.patch_installed](https://docs.saltstack.com/en/2018.3/ref/states/all/salt.states.pkg.html#salt.states.pkg.patch_installed)).


- The Server's [package installation](https://github.com/uyuni-project/uyuni/blob/c8ffe6b9425392f5235864ad070646bb8ebc2ecb/susemanager-utils/susemanager-sls/salt/packages/pkginstall.sls) and [patch application](https://github.com/uyuni-project/uyuni/blob/c8ffe6b9425392f5235864ad070646bb8ebc2ecb/susemanager-utils/susemanager-sls/salt/packages/patchinstall.sls) modules will call those functions and conditionally skip actual installation/application via `unless` clauses

- This should only happen if the minion's `mgr_fail_installation_if_download_is_required` Pillar is set

- Pillars controlling this feature can be set at a global, per-minion or per System Group basis ([similarly to what we do to set the package download endpoint override](https://github.com/SUSE/doc-susemanager/pull/366/files#diff-8bf787463eb899039a59878b8b2ce800R171)).


# Drawbacks
 - this is limited to Salt minions. Traditional clients have no such feature
 - only covers Zypper at this point. Yum/DNF can be implemented by leveraging the [--cacheonly](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/6/html/deployment_guide/sec-working_with_yum_cache#idm140707649391200) option
 - no UI

# Alternatives
- use Action Chains
  - pro: more visible to users
  - con: could have scalability issues, more difficult to implement
- implement custom modules instead of adding new functions to Salt's core
  - pro: does not need a pull request against Salt
  - con: the functionality might be useful in other contexts
- add this feature directly to Zypper via a commandline switch (analoguous to [--cacheonly](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/6/html/deployment_guide/sec-working_with_yum_cache#idm140707649391200) in `yum` and `dnf`)
  - pro: arguably cleaner design, does not need two calls to Zypper
  - con: updated Zypper would be needed, more difficult to implement

# Unresolved questions

None known.
