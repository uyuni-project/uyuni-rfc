- Feature Name: Automatic migration from Salt 3000 to Salt Bundle
- Start Date: 2023-03-22

# Summary
[summary]: #summary

Force an automatic migration for Salt clients from Salt 3000 to Salt Bundle.


# Motivation
[motivation]: #motivation


Salt 3000 is EOL as of Aug 31, 2022. It is advisable for Salt clients using Salt 3000 to migrate to Salt Bundle. Right now this migration can be done by applying the already existent `util.mgr_switch_to_venv_minion` state from the CLI. The purpose of this RFC is to automatically perform this migration for Salt 3000 clients to Salt Bundle so they can keep receiving updates for the Salt package, including security updates.

NOTE: This RFC excludes SSH minions.


# Detailed design
[design]: #detailed-design

An state to perform the migration from Salt 3000 to Salt Bundle is added to the highstate. This state checks the 'saltversion' grain and others in order to determine if the targeted minion needs to be migrated to Salt Bundle.

The migration will be triggered by the state if the following conditions are met:
- The running minion is not Salt Bundle.
- The running minion is not an SSH minion.
- The running minion is Salt 3000.
- The `mgr_avoid_venv_salt_minion` pillar is not `True` for this minion.

If so, the migration is performed in the following steps:

- Install the `venv-salt-minion` package.
- Copy the minion id file, minion configuration files, PKI files and static grains from the existing `salt-minion` in `/etc/salt` to the `venv-salt-minion` corresponding directories in `/etc/venv-salt-minion`.
- Enable the `venv-salt-minion` service.
- Disable the `salt-minion` service.
- Remove `/etc/salt/minion.d/susemanager.conf` file, to prevent possible accidental reconnection of classic "salt-minion" after migration.

The whole process is transparent to the user.


# Drawbacks
[drawbacks]: #drawbacks

- The `salt-minion` package remains installed and the configuration files in the `/etc/salt` are not deleted.

- After migration this check is done in every highstate.

- If a client was bootstrapped avoiding the Salt Bundle following the steps in the documentation, the migration would force this client to use Salt Bundle. The options to avoid installing Salt Bundle and keep using `salt-minion` that currently appear in the documentation are:

  * Execute mgr-bootstrap with --no-bundle option.

  * Set AVOID_VENV_SALT_MINION to 1 in the generated bootstrap script.

  * For bootstrap state set the `mgr_avoid_venv_salt_minion` pillar to `True`.

# Alternatives
[alternatives]: #alternatives

- Force the removal of the `salt-minion` package and related files. This could be done by means of a custom grain module that informs if the minion is running  `venv-salt-minion`. With that in place, the application of the highstate a second time could handle that second stage for purging.
- The impact of not doing this is that Salt 3000 clients will stop receiving updates for the Salt package.


# Resolved questions
[resolved]: #resolved-questions

1. What is a better solution?
  - The sls contains the logic for triggering the migration or not.
  - There is logic for triggering the migration that decides if adding or not the sls to the highstate.
  
The option chosen is adding the logic to the state as this stays in line with our usage of SLS files.

2. Could this automatic migration behaviour be opted out? It seems it would be reasonable in case bootstrapping with the Salt Bundle was explicitly avoided.

The automatic migration can be opted out by setting the pillar `mgr_avoid_venv_salt_minion` to `True` for the specific minion.

3. Is it best to take a cleaner approach and remove the `salt-minion` package and related files or to take a more conservative approach and do not do it in case there are unexpected scenarios?

Neither the `salt-minion` package nor the configuration files in `/etc/salt` are going to be removed in case the user had configured another `salt-minion` between stages.

However, the `/etc/salt/minion.d/susemanager.conf` file is going to be removed to prevent an accidental reconnection.

