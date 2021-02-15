- Feature Name: new-package-predownloading
- Start Date: 29-04-2019
- RFC PR: https://github.com/uyuni-project/uyuni-rfc/pull/5

# Unimplemented note

This RFC was not ultimately implemented due to time limitations. It is still archived here for historical purposes.

# Summary
Change the current package predownloading ("staging") feature for minions. Allow users to customize the start download time on a per-Action basis.

# Motivation

Package pre-downloading is an essential feature to shorten the length of patch windows and is one of the features to enable bandwidth management for installations that might not have good connectivity between systems and Proxies, or Proxies and Server.

Currently package pre-downloading is a global setting - either all or none of the Actions get it. Moreover the time window is unique ([documentation reference](https://github.com/SUSE/doc-susemanager/blob/a5a5c8ec/modules/reference/pages/admin/organizations.adoc#organization-details--configuration)), and a restart of Tomcat and Taskomatic is required to change it.

This RFC is about adding "download only" package installation/patch application Actions that can be scheduled as needed.

Motivation summary:
 - users might want to change the download schedule depending on physical locations, often represented by System Groups
   - this is particularly true in SUSE Manager for Retail use cases
 - users might need to change the download schedule depending on workload, available calendar time, other factors
 - we want users to be able to change the download schedule without restarting Tomcat and Taskomatic (currently the case as parameters are in `rhn.conf`)

# Detailed design

## User interface

### GUI

Whenever a package installation or patch application is scheduled on a minion, users will have the option to choose an advance download time:

![Screenshot of the new option form](images/00052-earliest.png)

*Note: the new form controls are highlighted in yellow.*

Clicking on the selection element will bring up possible options:

![Screenshot of the new option, selected](images/00052-selected.png)


If an Action Chain is selected as the scheduling option, the new form elements will be disabled:

![Screenshot of the new option form, Action Chains case](images/00052-actionchain.png)


*Note: the checkbox will not appear for traditionally managed systems.*

#### Behavior

Once the schedule is accepted, two Actions will actually be scheduled:
 - the original package installation or patch application Action and
 - the pre-downloading Action (with the correct advance time, if selected)

Action management (listing, canceling, etc.) will be the same as for any other Action.

#### Affected pages

This will need changes in the following pages:

- Single systems:
  - patch application: https://server.tf.local/rhn/systems/details/ErrataList.do?sid=1000010000&
  - package installation: https://server.tf.local/rhn/systems/details/packages/InstallPackages.do?sid=1000010000&
  - package upgrade: https://server.tf.local/rhn/systems/details/packages/UpgradableList.do?sid=1000010000&

- SSM:
  - patch application: https://server.tf.local/rhn/systems/ssm/ListErrata.do
  - package installation: https://server.tf.local/rhn/ssm/PackageInstall.do
  - package upgrade: https://server.tf.local/rhn/ssm/PackageUpgrade.do

*Links above assume `server.tf.local` as the server location and `1000010000` as a minion ID.*

### API

The following calls will need a new optional `downloadOnly` boolean flag:
- `system.schedulePackageInstall`
- `system.schedulePackageInstallByNevra`
- `system.scheduleApplyErrata`
- `systemgroup.scheduleApplyErrataToActive`

If `false` or unspecified, behavior will be identical to the current one.

If `true`, a download-only Action will be scheduled. Note that this is different from the GUI, where one schedules two Actions together in one screen, while in the case of the API two scheduling calls will be needed (with and without `downloadOnly` set), to gain the flexibility of calling them at different points in time if that is needed.

Note that if `true` and at least one target system is not a minion this call should return an error.

## Implementation
- new selection box will be added to current JSPs/React components
  - selection box has to be shown only if applicable systems are all minions
- existing Java handling code will receive the advance time value, and if set schedule two Actions:
  - in the case of package installation/upgrade:
    - one that applies [pkgdownload.sls](https://github.com/uyuni-project/uyuni/blob/c8ffe6b9425392f5235864ad070646bb8ebc2ecb/susemanager-utils/susemanager-sls/salt/packages/pkgdownload.sls)
    - one that applies [pkginstall.sls](https://github.com/uyuni-project/uyuni/blob/c8ffe6b9425392f5235864ad070646bb8ebc2ecb/susemanager-utils/susemanager-sls/salt/packages/pkginstall.sls)
  - in the case of patch application:
    - one that applies [patchdownload.sls](https://github.com/uyuni-project/uyuni/blob/c8ffe6b9425392f5235864ad070646bb8ebc2ecb/susemanager-utils/susemanager-sls/salt/packages/patchdownload.sls)
    - one that applies [patchinstall.sls](https://github.com/uyuni-project/uyuni/blob/c8ffe6b9425392f5235864ad070646bb8ebc2ecb/susemanager-utils/susemanager-sls/salt/packages/patchinstall.sls)
  - alternatively, those files might be unified and use `pkg.downloaded` instead of `pkg.installed` conditionally (resp. `pkg.patch_downloaded` instead of `pkg.patch_installed`)
- existing configuration options are to be deprecated in SUSE Manager supported versions-
- existing code handling the configuration options is to be removed from Uyuni

# Drawbacks
 - this is limited to Salt minions. Traditional clients retain their existing mechanism and are not affected
 - as the `pkg.downloaded` state [is not yet supported in Salt for Debian systems](https://docs.saltstack.com/en/2018.3/ref/states/all/salt.states.pkg.html#salt.states.pkg.downloaded), this remains an exclusive for `yum` and `zypper` (this RFC does not change this aspect)
 - current users of the existing feature will have to adapt their workflows
 - proposed mechanism is conceptually different from the one in place for traditional clients

# Alternatives
- add UI pages and API calls to define "content staging windows". Allow users to Actions to "content staging windows" at scheduling time
  - pro: with the UI, users do not have to go through the package/patch selection twice
  - con: more difficult to implement
- also keep the old mechanism in place
  - pro: users can either use the old and the new mechanism
  - con: more maintenance work

# Unresolved questions

None known at time of writing.
