- Feature Name: disallow-downloading-when-patching
- Start Date: 29-03-2919
- RFC PR: https://github.com/uyuni-project/uyuni-rfc/pull/6

# Summary
Optionally fail package installations and patch applications if they require any downloading.

This is limited to minions: SUSE based distros initially, Red Hat based distros as a stretch goal, with design in place for Debian based distros.

# Motivation
Minions with limited connectivity options might have little bandwidth available or bandwidth usage could come with a high cost (eg. in remote areas). In those cases we want users to be fully in control of when downloading happens, eg., to schedule that during off-peak hours (see https://github.com/uyuni-project/uyuni-rfc/pull/5). This RFC is about giving users the possibility to prevent package managers' default behavior of downloading at installation time.

Package installation and patch application Actions should thus fail in case packages were not previously downloaded (if so configured).

# Detailed design
- [zypper's execution module installation function](https://github.com/openSUSE/salt/blob/5e0fe08c6afd75a7d65d6ccd6cf6b4b197fb1064/salt/modules/zypperpkg.py#L1207) gets a new commandline option, `cachedonly`, `False` by default
  - if `True`, before proceeding with any installation it should call `zypper` with the `--dry-run` option and check if any download is necesary. Commandline example below:
  ```
  minion:~ # zypper --non-interactive --xmlout install --dry-run zsh
  <?xml version='1.0'?>
  <stream>

  ...

  <install-summary download-size="0" space-usage-diff="7389792" packages-to-change="1">

  ...
  </stream>
  ```
  - if the `install-summary` element's `download-size` attribute is greater than 0, installation should fail with an adequate error
- zypper's execution module should be checked to make sure no "read" methods require network access (eg. `list_patches`)

- The Server's [package installation](https://github.com/uyuni-project/uyuni/blob/c8ffe6b9425392f5235864ad070646bb8ebc2ecb/susemanager-utils/susemanager-sls/salt/packages/pkginstall.sls) and [patch application](https://github.com/uyuni-project/uyuni/blob/c8ffe6b9425392f5235864ad070646bb8ebc2ecb/susemanager-utils/susemanager-sls/salt/packages/patchinstall.sls) modules should pass the new `cachedonly` parameter to the `pkg` state modules, which will in turn relay it to the execution modules above

- This should only happen if the minion's `mgr_fail_installation_if_download_is_required` Pillar is set

- Pillars controlling this feature can be set at a global, per-minion or per System Group basis ([similarly to what we do to set the package download endpoint override](https://github.com/SUSE/doc-susemanager/pull/366/files#diff-8bf787463eb899039a59878b8b2ce800R171)).

## Extensions
 - `yum` and `dnf` can be also easily supported by adding `cachedonly` to the respective `install` methods, and then invoking the commandline tools with the `-C` option. [This is already implemented for "read" functions such as list_repo_pkgs](https://github.com/openSUSE/salt/blob/5e0fe08c6afd75a7d65d6ccd6cf6b4b197fb1064/salt/modules/yumpkg.py#L829)
 - `apt` could be supported in a similar way via the `--no-download` commandline option

# Drawbacks
 - this is limited to Salt minions. Traditional clients have no such feature
 - this targets only `zypper` at least initially, see Extensions
 - no UI

# Alternatives
- use Action Chains
  - pro: more visible to users
  - con: could have scalability issues, more difficult to implement
- implement custom modules instead of adding new functions to Salt's core
  - pro: does not need a pull request against Salt
  - con: the functionality might be useful in other contexts

# Next steps

Instead of resorting to two `zypper` calls via `--dry-run`, an option such as `yum`'s '`--cacheonly` or `apt`'s `--no-download` could be added directly in `zypper`. Arguably, that would be cleaner design, although an updated `zypper` would be needed. A feature request against `zypper` will be opened in this sense.

# Unresolved questions

None known.
