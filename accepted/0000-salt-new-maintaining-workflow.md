- Feature Name: An improved workflow for maintaining Salt
- Start Date: 2024-11-14

# Summary
[summary]: #summary

This RFC proposed an improved workflow for maintaining the Salt package for openSUSE/SUSE distributions, and therefore for Uyuni and SUSE Manager.

# Motivation
[motivation]: #motivation

Our current workflow for maintaining Salt requires manual user intervention after the changes are merged into our `openSUSE/salt` codebase, in order to make this changes available in OBS. Moreover, the Salt spec file and patches are tracked in a separated GitHub repository `openSUSE/salt-packaging`, that is also used to generate the changelog entries for the final RPM.

All these steps needs to be performed manually, with the help of some tooling, to eventually create a manual Submit Request to our Salt package in OBS.

With Salt Extensions appearing now in the upcoming Salt 3008 release, we want to introduce a new workflow that suits better and solves some the limitations we currently have. 

The purpose of this RFC is:
- Define an new workflow for Salt that reduces user intervention to zero after a given PR is merged in `openSUSE/salt` repository until getting the package ready to consume at OBS.
- Make the Salt maintaining workflow aligned with openSUSE practices.
- Provide a workflow that can also work the same way with packaged Salt Extensions.
- Deprecate the usage of `salt-packaging` repository.
 
# Detailed design
[design]: #detailed-design

In this new workflow the `openSUSE/salt` GitHub repository will become the unique source of thrust, and it will contain:

- Salt codebase
- Packaging artifacts: spec file, changelog and extra sources
- OBS workflow file

Taking inspiration from the [OBS/SCM integration guide](https://openbuildservice.org/help/manuals/obs-user-guide/cha-obs-scm-ci-workflow-integration), the new workflow will use OBS workflows and GitHub Webhooks to automate pulling the changes from GitHub to OBS.

In addition to this, as new Jenkins job will take care of making the OBS package ready to be submitted to openSUSE or SLE.

This is how the proposed OBS structure would look like:

- `systemsmanagement:saltstack/salt`:
   * no services enabled - package ready to be submitted to openSUSE or SLE.
   * branched from `systemsmanagement:saltstack:github/salt`
- `systemsmanagement:saltstack:github/salt`:
   * services enabled
   * package building based on `openSUSE/release/xxxx` GitHub branch.
- `systemsmanagement:saltstack:github:CI:...:PR-XXXX/salt`:
   * services enabled
   * package building according to PR branch.
   * branched and removed automatically from `systemsmanagement:saltstack:github/salt` by OBS workflow.

### Packaging artifacts

All current extra "Sources" files in our RPM package, together with spec file and changelog file will go now to a `pkg/suse/` directory in `openSUSE/salt`:

```
pkg/suse/README.SUSE
pkg/suse/html.tar.bz2
pkg/suse/salt-tmpfiles.d
pkg/suse/transactional_update.conf
pkg/suse/update-documentation.sh
pkg/suse/salt.spec
pkg/suse/salt.changes
```

This is the place now where all those files will be maintained.

#### Salt RPM changelog

As mentioned this is now at `pkg/suse/salt.changes` in `openSUSE/salt` GitHub repo.

When creating a PR to `openSUSE/salt` the user must also include the corresponding changes to the spec file, that can be generated as usual with `osc vc`.

Similarly to the main Uyuni repository, we should add a GitHub action to warn the user in case no changelog entry is added in the PR.

### OBS project structure

#### `systemsmanagement:saltstack:github/salt`

This OBS package will only contain `_multibuild` file and a `_service` file that should look like: 

```
<services>
  <service name="obs_scm">
    <param name="url">https://github.com/openSUSE/salt.git</param>
    <param name="scm">git</param>
    <param name="versionformat">@PARENT_TAG@</param>
    <param name="versionrewrite-pattern">v(.*)</param>
    <param name="revision">openSUSE/release/xxxx</param>
    <param name="extract">pkg/suse/salt.*</param>
  </service>
  <service name="set_version" />
  <service name="tar" mode="buildtime"/>
  <service name="recompress" mode="buildtime">
    <param name="file">*.tar</param>
    <param name="compression">gz</param>
  </service>
</services>
```

The rest of the files will be automatically pulled by the service, as they are enabled here. This package will be automatically refreshed by OBS at any new commit at `openSUSE/release/xxxx` branch.

#### `systemsmanagement:saltstack/salt`

This OBS package is a branch from `systemsmanagement:saltstack:github/salt`, where we disable the services and manually run them to get the spec file, changelog and obsinfo/obscpio files, so the package can be submitted to openSUSE or SLE.

The `_service` file should look like:

```
<services>
  <service name="obs_scm" mode="manual">
    <param name="url">https://github.com/openSUSE/salt.git</param>
    <param name="scm">git</param>
    <param name="versionformat">@PARENT_TAG@</param>
    <param name="versionrewrite-pattern">v(.*)</param>
    <param name="revision">openSUSE/devel/master</param>
    <param name="extract">pkg/suse/salt.*</param>
  </service>
  <service name="set_version" mode="manual" />
  <service name="tar" mode="buildtime"/>
  <service name="recompress" mode="buildtime">
    <param name="file">*.tar</param>
    <param name="compression">gz</param>
  </service>
</services>
``` 
And it should only contain the following files:

```
_multibuild
_service
salt-xxxx.obscpio
salt.changes
salt.obsinfo
salt.spec
```

Since services are disabled here, to allow submissions to openSUSE and SLE, this OBS package will be automatically synced with `openSUSE/devel/master` by a Jenkins job.

### OBS and GitHub Webhook integration

As described in the [SCM/CI Workflow integration guide](https://openbuildservice.org/help/manuals/obs-user-guide/cha-obs-scm-ci-workflow-integration#sec-obs-obs-scm-ci-workflow-integration-setup-token-authentication-how-to-authenticate-obs-with-scm), a "GitHub Personal Access Token" must be created and a "GitHub Webhook" configure at `openSUSE/salt` repository.


#### OBS workflow file

A `.obs/workflows.yml` will be also added to `openSUSE/salt` to define the OBS workflow as the following:

```
main_workflow:
  steps:
    - branch_package:
        source_project: systemsmanagement:saltstack:github
        source_package: salt
        target_project: systemsmanagement:saltstack:github:CI
  filters:
    event: pull_request

rebuild_master:
  steps:
    - trigger_services:
        project: systemsmanagement:saltstack:github
        package: salt
  filters:
    event: push
    branches:
      only:
        - openSUSE/release/xxxx
```

This workflow will take care of:

- Setting up a new subproject at `systemsmanagement:saltstack:github:CI:...:PR-XXXX/salt` for every incoming PR to build the Salt package according to the changes in the PR.
- Triggering the services at `systemsmanagement:saltstack:github/salt` on any new push to `openSUSE/release/xxxx` to build the package accordingly.

### Making OBS packages ready to submit

Since the package at `systemsmanagement:saltstack:github/salt` has "services" enabled, and we cannot enable/disable services using OBS workflows, this means this package is not yet ready to be submitted to openSUSE or SLE, as they don't accept enabled services on their submissions. We must disable the services.

In order to do this we will use an Jenkins job that monitors when a new build is done at `systemsmanagement:saltstack:github/salt` to trigger the following actions at the main `systemsmanagement:saltstack/salt` package:

```
# osc checkout systemsmanagement:saltstack/salt
# cd systemsmanagement:saltstack/salt
# osc service manualrun
# osc commit -m "Push new changes from GitHub"
```

This way, we ensure `salt.spec` and `salt.changes` and obscpio/obsinfo files gets upgraded according to latest changes.

### Proof-of-Concept

I've implemented this structure and automation here:

- GitHub repository: https://github.com/meaksh/salt/ (`openSUSE/devel/master` branch)
- OBS:
  * https://build.opensuse.org/package/show/home:PSuarezHernandez:tests/salt
  * https://build.opensuse.org/package/show/home:PSuarezHernandez:tests:github/salt
  * https://build.opensuse.org/package/show/home:PSuarezHernandez:tests:github:CI:....:PR-XX/salt

- Example PR:
  * https://github.com/meaksh/salt/pull/10
  * https://build.opensuse.org/package/show/home:PSuarezHernandez:tests:github:CI:meaksh:salt:PR-10/salt

Feel free to open new PRs against `openSUSE/devel/master` to see this in action.

# Drawbacks
[drawbacks]: #drawbacks

TBD

# Alternatives
[alternatives]: #alternatives

TDB

# Unresolved questions
[unresolved]: #unresolved-questions

TBD
