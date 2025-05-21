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

In this new workflow the `openSUSE/salt` GitHub repository will become the unique source of trust, and it will contain:

- Salt codebase
- Packaging artifacts: spec file, changelogs, \_multibuild file and extra sources
- OBS workflow file

Taking inspiration from the [OBS/SCM integration guide](https://openbuildservice.org/help/manuals/obs-user-guide/cha-obs-scm-ci-workflow-integration), the new workflow will use OBS workflows and GitHub Webhooks to automate pulling the changes from GitHub to OBS.

In addition to this, as new Jenkins job will take care of making the OBS package ready to be submitted to openSUSE or SLE.

This is how the proposed OBS structure would look like:

- `systemsmanagement:saltstack/salt`:
   * no services enabled - package ready to be submitted to openSUSE or SLE.
   * linked to `systemsmanagement:saltstack:github/salt`
- `systemsmanagement:saltstack:github/salt`:
   * services enabled
   * package building based on `openSUSE/release/xxxx` GitHub branch.
- `systemsmanagement:saltstack:github:CI:...:PR-XXXX/salt`:
   * services enabled
   * package building according to PR branch.
   * branched and removed automatically from `systemsmanagement:saltstack:github/salt` by OBS workflow.

The same OBS structure will apply these other OBS targets, allowing us to deal with different Salt versions if necessary ensuring the packages are also ready to be consumed, without enabled services that could run unexpectely on targets that are linked to them (like i.a. `systemsmanagement:Uyuni:Master`):
- `systemsmanagement:saltstack:products:testing`
- `systemsmanagement:saltstack:products:next`

For `systemsmanagement:saltstack:products` OBS target, it is not really necessary to follow the above structure, as this target gets updated once we run our "Salt Promote pipeline" (which does copypac whatever is in `products:testing` to `products`).

### Packaging artifacts

All current extra "Sources" files in our RPM package will go now to a `pkg/suse/` directory in `openSUSE/salt`, together with the spec file, the different maintained changelogs files:

```
pkg/suse/README.SUSE
pkg/suse/html.tar.bz2
pkg/suse/salt-tmpfiles.d
pkg/suse/transactional_update.conf
pkg/suse/update-documentation.sh
pkg/suse/rpmchangelogs
pkg/suse/_multibuild
pkg/suse/salt.spec
pkg/suse/changelogs/factory/salt.changes
pkg/suse/changelogs/sles15sp2/salt.changes
pkg/suse/changelogs/sles15sp3/salt.changes
pkg/suse/changelogs/sles15sp4/salt.changes
pkg/suse/changelogs/sles15sp5/salt.changes
```

This is the place now where all those files will be maintained.

#### Tracking upstream and downstream patches

This RFC proposes the usage of "obs_scm" service as the mechanism to pull the sources for the Salt package to build. This service generates a sources tarball based on the content of a configured GitHub repository.

Except for bugs under embargo, we won't use patches in the spec file. The generated tarball includes the latest changes we merged into our `openSUSE/release/<current release>` branch.
Bugs under embargo use a different workflow with manually created patches since we cannot push fixes for such bugs to our public Github repository.

We will therefore not track bug fixes in the spec file anymore. The origin of a bug fix, i.e. whether it is backport from upstream or not, will be stored in a Git note attached to the commit of each bug fix. Git notes can be added after bug fixes are merged  without modifying the Git history.

#### Salt RPM changelogs

As mentioned, the changelog files are now maintained in the `openSUSE/salt` GitHub repo, under `pkg/suse/changelogs/` directory. New changelog are part of pull requests to `openSUSE/salt`.
Our packaging artifacts will contain a `rpmchangelogs` Python script to easily `add`, `modify` and `remove` changelog entries for all changelogs at once.

We will use a Github status check to prevent us from merging pull requests without changelogs, like we already do in `uyuni-project/uyuni`

### OBS project structure

#### `systemsmanagement:saltstack:github/salt`

This OBS package will only contain only a `_service` file that should look like:

```
<services>
  <service name="obs_scm">
    <param name="url">https://github.com/openSUSE/salt.git</param>
    <param name="scm">git</param>
    <param name="versionformat">@PARENT_TAG@</param>
    <param name="versionrewrite-pattern">v(.*)</param>
    <param name="revision">openSUSE/release/xxxx</param>
    <param name="extract">pkg/suse/_multibuild</param>
    <param name="extract">pkg/suse/salt.spec</param>
    <param name="extract">pkg/suse/changelogs/factory/salt.changes</param>
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

NOTE: This package will be automatically refreshed by OBS at any new commit at `openSUSE/release/xxxx` branch.

#### `systemsmanagement:saltstack/salt`

This is our ready-to-consume OBS package. We set the devel package (osc setdevelpackage) for this OBS package to `systemsmanagement:saltstack:github/salt`, but here we disable the services and manually run them to get the spec file, changelog and obsinfo/obscpio files, so the package can be submitted to openSUSE or SLE.

The `_service` file here should look like:

```
<services>
  <service name="obs_scm" mode="manual">
    <param name="url">https://github.com/openSUSE/salt.git</param>
    <param name="scm">git</param>
    <param name="versionformat">@PARENT_TAG@</param>
    <param name="versionrewrite-pattern">v(.*)</param>
    <param name="revision">openSUSE/release/xxxx</param>
    <param name="extract">pkg/suse/_multibuild</param>
    <param name="extract">pkg/suse/salt.spec</param>
    <param name="extract">pkg/suse/changelogs/factory/salt.changes</param>
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

Since services are disabled here, to allow submissions to openSUSE and SLE, this OBS package will be automatically synced with `openSUSE/release/xxxx` by a Jenkins job.

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

### Making OBS packages ready to be submitted to Maintenance

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

### Salt Extensions

Salt extensions are collections of Salt modules that are maintained outside of the Salt repository.
They can be maintained by the upstream Salt Core team, by our openSUSE Salt maintainers or anyone
else. By convention, most Salt extensions are maintained in repositories in the
[salt-extensions](https://github.com/salt-extensions) Github organization.

#### Extensions Maintained by openSUSE

- transactional\_update
- zypperpkg
- rebootmgr
- btrfs
- openscap
- libvirt_events
- virt
- snapper
- suse\_ip?


Each of these extensions are maintained in a separate Git repository, created with
[`salt-extension-migrate`](https://github.com/salt-extensions/salt-extension-migrate). This tool
keeps the Git log from the main Salt repository and is the standard tool to move Salt modules to new extensions.

A) We maintain these extensions in the [salt-extensions](https://github.com/salt-extensions) Github
organization. That makes it easy to discover our Salt extensions and makes it easier for anyone to
contribute to our Salt extensions, just like any other existing Salt extension. The standard tooling
helps us with the configuration for publishing the documentation and the PyPI upload.

B) We maintain these extensions in the [openSUSE](https://github.com/openSUSE) Github organization,
to make the ownership and responsibility clear. We manually configure PyPI upload and docs publishing.

#### RPM Packages for Extensions

Salt Extensions are like any other Python package. `py2pack` can be used to generate 80% of the spec
file for a Salt Extension. That makes it easy to add new Salt Extensions or drop old ones, e.g. when
they are moved back to the Salt core repository.

#### Packaged Salt Extensions

For the Salt Extensions that are packaged separately from the main Salt package, we will create a separated GitHub repository for each of these extensions.

- a common salt-extension spec file that will generate all RPM packages
- The sources for each Salt Extension we package
- The changelog files for each maintained codestream
- OBS workflow file

When it comes to OBS, we will use the same SCM integration and OBS subprojects schema than the proposed for the main Salt codebase. Unique workflow for Salt and Salt Extensions.

- PoC:
  * https://github.com/meaksh/test-repo-1
  * https://build.opensuse.org/package/show/home:PSuarezHernandez:tests/salt-extensions

- Example PR:
  * https://github.com/meaksh/test-repo-1/pull/6
  * https://build.opensuse.org/project/show/home:PSuarezHernandez:tests:github:CI:meaksh:test-repo-1:PR-6

NOTE: We are using a single GitHub repo and single OBS package which provides all different salt-extensions RPM packages. This is preferred against having a separated GitHub repositories and OBS package for each Salt Extension, as it will reduce the number of submissions, maintenance incidents and resources needed.

# Drawbacks
[drawbacks]: #drawbacks

- A bit more complex OBS structure than the current one. Including `obs_scm` service.
- Having to still rely on Jenkins to get the packages ready to be released.

# Alternatives
[alternatives]: #alternatives

1. Stick to our current workflow based on "salt-packaging" -> The workflow doesn't currently fit with Salt Extensions and we don't want to have different workflows between Salt and Salt Extensions.
2. One dedicated GitHub repository and OBS package per each Salt Extension -> It won't save resources and will cause more submissions.
3. The usage of "git submodules" as an alternative to adding the Salt Extensions sources manually would make it tricky to generate patches manually and also to integrate with "obs_scm".
4. Use OBS `scmsync` integration -> while this allows to integrate even the `_service` file into the GitHub repo, it does not work well with SCM/CI workflow, therefore we cannot test the build of the package for an open PR because the branched package is not reflecting the actual changes on the PR.

# Unresolved questions
[unresolved]: #unresolved-questions

TBD
