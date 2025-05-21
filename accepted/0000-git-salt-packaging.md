- Feature Name: Git-based Salt Packaging
- Start Date: 2025-05-21

# Summary
[summary]: #summary

Package Salt on src.opensuse.org, with one branch per code stream.

# Motivation
[motivation]: #motivation

We want to change our packaging process for Salt, starting with Salt 3008. This is the
first release we package after moving a lot of Salt modules to Salt Extensions. This
approach should meet the following goals:

1. After merging a pull request at [openSUSE/salt](https://github.com/openSUSE/salt), a new package (RPM) is built automatically
2. Building Salt and Salt Extensions can be controlled from a single location (sources may be located elsewhere)
3. We're aligned with the new openSUSE Tumbleweed / SLE 16 workflow packaging
4. We're aligned with upstream's Salt Extension workflows for maintaining, documenting and publish

Package sources for Tumbleweed and SLE 16 will be tracked in git repositories.
[OBS](https://openbuilservice.org) uses the sources from central git forges located at
https://src.opensuse.org and https://src.suse.de respectively. 


## Requirements

We maintain Salt RPMs in different code streams from the same sources. The code streams'
changelogs differ and release timings can be

- Why are we doing this?
- What use cases does it support?
- What is the expected outcome?

Describe the problem you are trying to solve, and its constraints, without coupling them too closely to the solution you have in mind. If this RFC is not accepted, the motivation can be used to develop alternative solutions.

# Detailed design
[design]: #detailed-design

## `openSUSE/Salt` on Github

 Build metadata (salt.spec, salt.changes, \_multibuild, …) is moved to a subdirectory in
`openSUSE/salt` on GitHub. This allow us to include packaging updates at the time we
create pull requests, e.g. we can include an appropriate changelog together with the
changes.

Files moved to Salt repository:
- pkg/suse/README.SUSE
- pkg/suse/html.tar.bz2 ???
- pkg/suse/salt-tmpfiles.d
- pkg/suse/transactional_update.conf
- pkg/suse/update-documentation.sh
- pkg/suse/rpmchangelogs
- pkg/suse/_multibuild
- pkg/suse/salt.spec
- pkg/suse/changelogs/factory.changes
- pkg/suse/changelogs/sles15sp2.changes
- pkg/suse/changelogs/sles15sp3.changes
- pkg/suse/changelogs/sles15sp4.changes
- pkg/suse/changelogs/sles15sp5.changes
- pkg/suse/changelogs/sles15sp6.changes
- pkg/suse/changelogs/sles15sp7.changes

### RPM Changelogs

New changelog entries should be part of pull requests. It easy for the code author to
write the user-facing changelog entry while she has all the required context available.

Our changelogs differ between code streams. Most differences are due to different grouping
and entry dates, since we generally keep the package contents in sync.

To help adding new changelog entries in pull requests and update them during rebases, we
add a new Python script `rpmchangelogs`. This script wraps `osc vc` to modify all
`*.changes` files at once. It can `add`, `modify`, and `remove` the latest changelog entry
in all changelogs when the entries are the same.

We use a Github status check to prevent accidental pull requests merges without changelog entries.

## "Package-Git" repository on src.{suse.de,opensuse.org}

Package git: One repository with different branches (see below). The repository contains
openSUSE/salt as a Git submodule.

Branches:
-  `factory` (devel for Tumbleweed)
-  `products` (why?)
-  `testing` (devel for Manager / Uyuni)
-  `sles15sp5` (code stream, src.suse.de)
-  `sles15sp6` (code stream, src.suse.de)
-  `sles15sp7` (code stream, src.suse.de)
-  `next` (why?)

###  Packaging sources in salt repo

``` text
.gitattributes            # created with obs-git-init
.gitignore                # created with obs-git-init
.gitmodules               # contains Git submodule status
salt                      # Git submodule
README.SUSE               # extracted from `salt` Git submodule
_multibuild               # extracted from `salt` Git submodule
html.tar.bz2              # extracted from `salt` Git submodule
salt-tmpfiles.d           # extracted from `salt` Git submodule
salt.spec                 # extracted from `salt` Git submodule
salt.changes              # extracted from `salt` Git submodule,for the given branch
transactional_update.conf # extracted from `salt` Git submodule
update-documentation.sh   # extracted from `salt` Git submodule
```

## "Project-Git" repository on src.{suse.de,opensuse.org}

We use a single "Project-Git" repository, again with one branch per code stream. Packages
in this project are included as Git submodules, checked out at the corresponding branch. 

Per convention, the project git repository is located in the "salt" organisation and
called `_ObsPrj`. An example organisation with the same layout (except that it uses a
singular `master` branch in `_ObsPrj`) is [lua](https://src.opensuse.org/lua)

### Packages

``` text
salt
salt-ext-zypper
salt-ext-transactional_update
salt-ext-rebootmgr
...
```

## Build Service project on build.{suse.de,opensuse.org}

Build Service projects configure build repositories via it's `meta`. The rest (including
`prjconf`) is maintained in the "Project-Git".

##  Update End-to-end Workflow

When we merge a PR to a release/ branch in openSUSE/salt, a jenkins job updates the Package-Git repository.

``` text
1. update git submodule
2. extract files (salt.spec, \_multibuild, …)
3. rename <codestream.changes> to salt.changes
4. commit
5. push 
```

This is implemented with a Makefile, the Jenkins job just calls `make` with
required variables set. The same Makefile also defines targets to similarly update Salt
Extensions. 

[`workflow-direct`](https://src.opensuse.org/adamm/autogits) keeps the Project-Git
up-to-date with changes to the Package-Git repositories.

## Salt Extensions

Salt Extensions are packaged individually. Each salt extension is a typical
Python RPM, built with the standard `python-rpm-macros`, tracked in
"Package-Git" repositories. These package git repositories are included next to
Salt in the "Project-Git".

Packaging sources are different from Salt since we do not control the upstream
repositories. Specfile and changelog are not stored in the extension source repos, instead
we keep them directly in the Package-Git. Since these are new packages, we don't have
diverging changelogs and can use a single branch.

# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?

  * obscure corner cases
  * will it impact performance?
  * what other parts of the product will be affected?
  * will the solution be hard to maintain in the future?

# Alternatives
[alternatives]: #alternatives

- What other designs/options have been considered?
- What is the impact of not doing this?

# Unresolved questions
[unresolved]: #unresolved-questions

- What are the unknowns?
- What can happen if Murphy's law holds true?
