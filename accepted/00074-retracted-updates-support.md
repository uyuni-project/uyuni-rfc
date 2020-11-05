- Feature Name: Retracted updates support
- Start Date: 2020-11-03
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

The topic of this RFC is implementing the "retracted patches" support in Uyuni.

A retracted patch is a patch with attribute `status=retracted`. The purpose of
the flag is to signalize the fact, that the patch had been released, but was
then back (retracted) by its publisher. This can be used, for instance, when the
publisher issues a patch that is invalid (e.g. can break a system).

# Motivation
[motivation]: #motivation

- Why are we doing this?

SUSE Customer Center (SCC) now exposes patches with the `retracted`
status. Making Uyuni aware of this feature improves the SCC integration.

- What use cases does it support?

The main goal of the feature is to minimize the possibility of breaking user
systems due to broken released patches.

- What is the expected outcome?

To make Uyuni aware of the `retracted` status of patches and to update
corresponding pieces of UI/XMLRPC.

# Detailed design
[design]: #detailed-design

We will implement the feature in an iterative way, starting from basic support
of the `retracted` status in the `spacewalk-repo-sync` and backend. After that,
it should be exposed in the user-facing parts of Uyuni. Finally, we will enhance
the Content Lifecycle feature by adding new filters operating with the
`retracted` status.

## Zypper implementation of retracted patches

Understanding how zypper handles retracted patches is vital for further design
of the feature integration.

In this section, we consider a system which:
- has an installed package `hello-2.10-lp151.2.6.x86_64`
- is registered in a repository containing a retracted patch associated with
  package `hello-2.10-lp151.4.1.x86_64` (newer than the installed one)

Operations and their outcomes:
- listing (`zypper patches`): lists retracted patches with status `retracted`
- searching for new versions (`zypper search -v hello`) gets us:
  `vR | hello | package | 2.10-lp151.4.1` <--- R means retracted
- upgrading a package (`zypper up hello`):
  does not upgrade to a version contained in a retracted patch
- installing specific version (`zypper in hello-2.10-lp151.4.1`):
  **allows** installing a package contained in a retracted patch (this must be
  taken into account, since this is the way we upgrade packages in SUMA)
- installing retracted patch (`zypper in patch:<retracted_patch_id>`):
  yields "patch not needed" and exit code `0`. Consequence: retracted patch
  can't be applied to a system! Q: somebody double-check this.
- if a system already has a patch installed, that becomes retracted, zypper has
  no intention to fix this situation

## Iteration 1 - Minimal Viable Product

### Database
The `rhnErrata` table must be updated with the `status` column of type
`VARCHAR(32)`.

Q: Alternatives: 1) `NUMERIC`, 2) normalize the `status` attribute and use
another table (see `rhnErrataSeverity` for an example).

### Reposync

The status `retracted` is part of `update` elements in the `updatedata.xml` file
of the repository. We need to adjust `spacewalk-repo-sync` (`errataImport.py`)
so that it parses this attribute during repository synchronization and stores it
in the database (`rhnErrata.status`).

Q: How does SCC retract the patch? Does it modify the patch with the same id by
   changing `status=stable` to `status=retracted` or does it somehow issue a new
   patch?

A: i think it's the former (modify), but verify that!
   https://jira.suse.com/browse/SLE-8770

Q: If the previous question==true: We need to think of consequences of modifying
   an existing patch. Normally reposync is not designed to modify data. We need
   to make sure reposync spots this change and maybe we also need to update some
   caches (system available updates are cached (`rhnServerNeededCache`?)).

### Java backend

We need to enhance the `Errata` class with the `status` attribute, for which we
will implement an `enum`.

### Repository generating
Enhance the `UpdateInfoWriter` class, so that it includes the `status` attribute
in the output XML. Currently the `status` output is hardcoded to `final`.


### UI

The following pages must be updated:

- Patch detail: information about the status. Given the fact we only have 2
  states now (`retracted`/`final`), this can be a boolean information telling
  whether the patch is retracted or not.

Q: should this be read-write? so that user can modify the `status` attribute
using a toggle (for non-vendor channels). If we allow this, we need to face the
consequences of modifying a patch (maybe regenerating some data
(`rhnServerNeededCache`, regenerating repodata of all channels, if this is not
already handled somewhere)).

- Patch list (*Patches -> All/Relevant*): an icon in the list, if the
  patch is retracted.

- *System detail -> Software -> Packages -> List/Upgrade/Install*: a **fat**
  warning icon in the list, if a package is contained in a retracted patch. The
  warning should contain a popup text, telling that selecting that package
  **installs** the package.

- Package install/upgrade confirmation screens: if there are any packages
  contained retracted patches, we should explicitly inform the user on these
  screens too.

- *System detail -> Software -> Patches*: an icon in the list, if the
  patch is retracted. The warning should contain a popup text, telling that
  selecting the patch for installation doesn't have any effect (see the details
  about zypper above).

- *Channel detail -> Patches*: an icon

- *Channel detail -> Packages*: an icon

Q: consider this alternative: toggle button `show retracted patches`/`show
  packages from retracted` in the lists above.


### XMLRPC
The following endpoints must be updated:

- `ErrataHandler.getDetails` the endpoint will expose the `status` field of an
  Erratum

- `ErrataHandler.setDetails` (if we allow modifying the flag) for non-vendor
  channels the endpoint allows setting `status` to either `retracted` or `final`

- Q: `ErrataHandler.create` shall we support creating retracted patches via API?
  Likely not.

- `PackageHandler.getDetails` add a boolean flag to the return value, that tells
  if the package is part of a retracted patch

- `SystemHandler.schedulePackageInstall` no changes needed. The endpoint takes
  package ids, so the user most likely knows the details of the package (and
  a possible presence of a retracted patch too)

Q: todo verify that user can't get list of package ids without knowing the
  retracted status somewhere

- `SystemHandler.scheduleApplyErrata` no changes needed for the same
  reason. Moreover, even if user schedules a retracted patch application, the
  patch won't be installed (see the details about zypper above). We might inform
  the user about it somehow.

- Information about the presence of a retracted patch on a system/in a channel
  can be retrieved via existing XMLRPC methods and `ErrataHandler.getDetails`.


## Iteration 2 - Content Lifecycle management

Enhance Content Lifecycle Manager and notifications.

### Filters

- add a filter that strips retracted patches from the sources

- add a filter for turning `retracted` patches into `stable` ones
Q: This is questionable. Do we need that? And are filters a good fit for that?
Mabye we need some to generalize the filters a bit.

### Projects

- distinguish a project with retracted patch in it

- Warn about out-of-date CLM clones with new retracted patches

### Notifications
- notification after reposync, when some patches -> retracted &&


## Iteration 3 - deeper UI integration, allow uninstalling a retracted patch
- Channel detail: a warning icon and a message, that the channel contains a
  retracted patch

- Channel list: a warning icon in the list, if the channel contains a retracted
  patch

- System detail: a warning icon and a message, that the system has a retracted
  patch installed

- System list: a warning icon in the list, if the system has a retracted patch
  installed

- Allow uninstalling a retracted patch (downgrade)

# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?
It adds complexity to the product for relatively sparse use case (SCC is not
retracting patches _that_ often).

# Alternatives
[alternatives]: #alternatives

- What other designs/options have been considered?
Not doing anything at all.

- What is the impact of not doing this?
The retracted patches would be exposed to the clients and installing its
packages them could lead to unwanted results (e.g. breaking systems).


# Unresolved questions
[unresolved]: #unresolved-questions

- See the inline "Q:" parts.
- How to "uninstall" a patch that used to be stable, but is retracted now? Is
  there some other way than `zypper in --oldpackage pkg-oldver`?
- any screens/consequences for image building? (ask @cbbayburt)
- What happens if patch=stable -> retracted -> stable? this path should be also
  supported

# Resolved questions
- Q: how does SUMA upgrade packages/install patches via salt? does it specify
  the version of the upgraded package?
  - A: Yes.
  - patching: we create an action bearing all errata, salt then
    applies state `packages.patchinstall` with all of the patches
  - upgrading: we call `packages.pkginstall` with package name, arch and version  

# Appendix
Examples of XML data for a retracted patch.

## Retracted patch served by SCC
```xml
<!-- what we get from SCC -->
<updates>
  <update from="maint-coord@suse.de" status="retracted" type="optional" version="1">
    <id>11749</id>
    <title>Optional update for hello</title>
    <severity>moderate</severity>
    <release>openSUSE Leap 15.1 Update</release>
    <issued date="1593505741"/>
    <references/>
    <description>
This update for hello is a test for retracted updates.
</description>
    <pkglist>
      <collection>
        <package name="hello" epoch="0" version="2.10" release="lp151.4.1" arch="src" src="src/hello-2.10-lp151.4.1.src.rpm">
          <filename>hello-2.10-lp151.4.1.src.rpm</filename>
        </package>
        <package name="hello" epoch="0" version="2.10" release="lp151.4.1" arch="x86_64" src="x86_64/hello-2.10-lp151.4.1.x86_64.rpm">
          <filename>hello-2.10-lp151.4.1.x86_64.rpm</filename>
        </package>
        <package name="hello-debuginfo" epoch="0" version="2.10" release="lp151.4.1" arch="x86_64" src="x86_64/hello-debuginfo-2.10-lp151.4.1.x86_64.rpm">
          <filename>hello-debuginfo-2.10-lp151.4.1.x86_64.rpm</filename>
        </package>
        <package name="hello-debugsource" epoch="0" version="2.10" release="lp151.4.1" arch="x86_64" src="x86_64/hello-debugsource-2.10-lp151.4.1.x86_64.rpm">
          <filename>hello-debugsource-2.10-lp151.4.1.x86_64.rpm</filename>
        </package>
        <package name="hello-lang" epoch="0" version="2.10" release="lp151.4.1" arch="noarch" src="noarch/hello-lang-2.10-lp151.4.1.noarch.rpm">
          <filename>hello-lang-2.10-lp151.4.1.noarch.rpm</filename>
        </package>
      </collection>
    </pkglist>
  </update>
</updates>
```

## Retracted patch in the repodata generated by Uyuni

Here it's obvious, that the `status` attribute is not propagated correctly in
the current version.
```xml
<!-- what reposync creates -->
<?xml version="1.0" encoding="UTF-8"?>
<updates>
  <update from="maint-coord@suse.de" status="final" type="enhancement" version="1">
    <id>11749</id>
    <title>Optional update for hello</title>
    <severity>moderate</severity>
    <issued date="2020-06-30 13:29:01"/>
    <updated date="2020-06-30 13:29:01"/>
    <description>
This update for hello is a test for retracted updates.
</description>
    <references/>
    <pkglist>
      <collection short="retracted-example">
        <name>retracted-example</name>
        <package name="hello" version="2.10" release="lp151.4.1" epoch="0" arch="x86_64" src="hello-2.10-lp151.4.1.src.rpm">
          <filename>hello-2.10-lp151.4.1.x86_64.rpm</filename>
          <sum type="sha256">d3078e456b443b5963d389c6e8be0bcf2d828fc690fac8a898717404986f71f5</sum>
        </package>
        <package name="hello-debuginfo" version="2.10" release="lp151.4.1" epoch="0" arch="x86_64" src="hello-2.10-lp151.4.1.src.rpm">
          <filename>hello-debuginfo-2.10-lp151.4.1.x86_64.rpm</filename>
          <sum type="sha256">f4075a9816576eb043381aaf9533f39ebc2bd485a2d0d9c05a87c7a4872e4e99</sum>
        </package>
        <package name="hello-debugsource" version="2.10" release="lp151.4.1" epoch="0" arch="x86_64" src="hello-2.10-lp151.4.1.src.rpm">
          <filename>hello-debugsource-2.10-lp151.4.1.x86_64.rpm</filename>
          <sum type="sha256">b5425b7a68e90e1628a12a424c2687fbb4cca5d4b2e3acacb4acfa091549cabc</sum>
        </package>
        <package name="hello-lang" version="2.10" release="lp151.4.1" epoch="0" arch="noarch" src="hello-2.10-lp151.4.1.src.rpm">
          <filename>hello-lang-2.10-lp151.4.1.noarch.rpm</filename>
          <sum type="sha256">22175f470d19d3bb65be50071f5873bfe1222cbe81b6b3efc62b16bd356af83e</sum>
        </package>
      </collection>
    </pkglist>
  </update>
</updates>
```
