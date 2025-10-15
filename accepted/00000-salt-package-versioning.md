- Feature Name: Salt packages versioning
- Start Date: 2025-10-15

# Summary
[summary]: #summary

We are releasing our branch of Salt with its original version (currently `3006.0`) with no any changes in version number with each next release.
This approach is causing some confusions on detecting the exact salt code used with the package as the `release` of the packages, delivered
for different clients can't be aligned and is not reliable. The only reliable for now is the data from the package changelog.

The aim of this RFC is to improve the visibility of the state of the salt code released with each maintenance update.

# Motivation
[motivation]: #motivation

- We need to have clear way to identify the exact salt code used with the salt packages as the release number is not reliable.
- There were some issues detected for the cases when the outdated salt is used either on `salt-master` or `salt-minion` side, but such cases are hard to identify as the only reliable data is the changelog of the package.
- Make it easier to ensure that newer version of Salt is used on the `salt-master` side by enforce preventing adding higher `salt-minion` version to bootstrap repos.
- Unify the same approach for classic salt package used on the `salt-master` side and for the salt bundle to make the check, if the versions aligned, clear for the supporters and the users.

# Detailed design
[design]: #detailed-design

With each salt version bump we are using certain version from upstream Salt, like `3006.0` now (before we had `3004`, `3002.2`, `3000` etc.).
While backporting the fixes and adding the features we are releasing Salt packages with each maintenance update without chaning the version of the packages.
The only changing part is the `release` of the package, but it depends on the project where it was building and there is no any alignment possible.

To avoid the confusions and better tracking the alignment of the package version across different targets for classic salt package and the salt bundle,
we could extend the version of the package with the patch level like `MAJOR.MINIOR.PATCH` instead of `MAJOR.MINOR` which is used now.

The patch level could be either increased manually on each maintenance update submission or adjusted automatically on the build time with the current number of patches included.

With such approach we would have constantly increasing version number and the content of each package release will be easier to identify.

The examples of new versions to be released:
`3006.0.1`, `3006.0.2`, `3006.0.3` ... `3008.0.0` - in case of manual version increase
`3006.0.179`, `3006.0.180`, `3006.0.183` ... `3008.0.25` - in case of alignment with the numbers of patches included

The suggestion with the number of patches could be not relevant in case of switching to git workflow with the packaging,
in this case as an alternative we can check if we can use the amount of commits between the latest one and the original for the certain version.

This way of package versioning could improve the process of creating the bootstrap repositories for different types of the clients as
the salt packages in the bootstrap repos could be checked to prevent populating the bootstrap repositories with the salt package versions higher
than used on the salt-master side.

The suggested way of versioning by adding patch level to the version number does not require ECOs for each next version bump, except the case,
when major or minor part of the version is changing. In this case, only single request to add salt package to the list of the packages that may
receive version updates without ECO is required.

# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?

  * slightly increase the complexity of submitting new maintenance update, but can be mitigated by automation with either RPM macro or OBS service
  * in case of manual version increase could affect the speed of preparing the submission
  * with manual version increase could cause issues due to the typos or not expected values of the version

# Alternatives
[alternatives]: #alternatives

- Leave the package versioning as it is now
- Add extra pre-defined prefix for the `release` of the package, but prefixes are already used there, so it could cause way too long `release` section.
- Use metadata fields instead of adding patch level to the version number, for example with `Provides` field, but it doesn't provide enough visibility and bit more complex to implement as requires parsing package metadata each time when we need to compare packages.

# Unresolved questions
[unresolved]: #unresolved-questions

- It's not clear how to align it with git workflow integration for OBS.
- What should we do with the old product versions which are not using any conditions for adding the new versions of the bundle to the bootstrap repositories?
