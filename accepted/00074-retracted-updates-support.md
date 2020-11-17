- Feature Name: Retracted updates support
- Start Date: 2020-11-03
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

The topic of this RFC is implementing the "retracted patches" support in Uyuni.

A retracted patch is a patch with attribute `status=retracted`. The purpose of
the flag is to signal the fact that the patch had been released, but was then
taken back (retracted) by its publisher. This can be used, for instance, when
the publisher issues a patch that is invalid (e.g. can break a system).


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
  can't be applied to a system.
- if a system already has a patch installed, that becomes retracted, zypper has
  no intention to fix this situation (this can be problematic, since downgrading
  RPM is potentially dangerous operation because of rpm scripts)


## Iteration 1 - Minimal Viable Product

### Database
The `rhnErrata` table must be updated with the `status` column of type
`VARCHAR(32)`.

### Reposync

The status `retracted` is part of `update` elements in the `updatedata.xml` file
of the repository. We need to adjust `spacewalk-repo-sync` (`errataImport.py`)
so that it parses this attribute during repository synchronization and stores it
in the database (`rhnErrata.status`).

We need to think of consequences of modifying an existing patch (that has been
synced in the past with `status=final`). We need to make sure reposync spots
this change and maybe we also need to update some caches (system available
updates are cached (`rhnServerNeededCache`?)).

Analyze the case, when a stable patchh gets retracted and then stable again in SCC.

### Java backend

We need to enhance the `Errata` class with the `status` attribute, for which we
will implement an `enum`.

### Repository generating
Enhance the `UpdateInfoWriter` class, so that it includes the `status` attribute
in the output XML. Currently the `status` output is hardcoded to `final`.

## Inter Server Sync
Make sure that the patch status gets propagated correctly in the ISS slaves.


## Iteration 2 - Enhance UI and XMLRPC

In this iteration, we add the support to user-facing parts of SUMA.

### UI

The following pages must be updated:

- *Patches -> All -> detail*:
  information about the status. Given the fact we only have 2 states now
  (`retracted`/`final`), this can be a boolean information telling whether the
  patch is retracted or not.

- *Patches -> Manage Patches*: 
  We should implement a checkbox, allowing the user to change the status
  attribute (although the change should be disabled for vendor patches). We need
  to take into account the possible consequences of modifying a patch (maybe
  regenerating some data (`rhnServerNeededCache`, regenerating repodata of all
  involved channels)).

- *Patches -> All*: an icon in the list, if the patch is retracted.

- *Patches -> Relevant*: a retracted patch should not be displayed
  in this list at all.

- *System detail -> Software -> Packages -> List*:
  Installed packages contained in retracted patches should be highlighted (icon,
  possibly accompanied by red text).

- *System detail -> Software -> Packages -> Upgrade*:
  Package upgrades that are part of the retracted patch should not be
  displayed. The highest ("non-retracted") update of the package should be
  displayed.

- *System detail -> Software -> Packages -> Install*:
  Don't display package versions that are part of a retracted patch.

- New tab *System detail -> Software -> Packages -> Retracted*:
  This screen should allow user to install or upgrade packages
  contained in retracted patches and should contain huge warning about
  possible consequences. The table should contain packages for both
  installation and upgrade in the following manner:

  - Installation: display the newest version of the "retracted"
    package, if it's the newest version in the channel (i.e. there is
    no non-retracted package that superseedes this one) and the
    package is not installed on the system.

  - Upgrade: for each package installed on the system, display its
    retracted upgrade, if there is no superseeding non-retracted
    upgrade in the channel.

  - We should distinguish the install/upgrade rows graphically

- *System detail -> Software -> Patches*:
  Don't display retracted patches.

- *Channel detail -> Patches*: an icon for a retracted patch

- *Channel detail -> Packages*: an icon for a package contained in a retracted
  patch

### XMLRPC
The following endpoints must be updated:

- `ErrataHandler.getDetails` the endpoint will expose the `status` field of an
  Erratum

- `ErrataHandler.setDetails` for non-vendor channels the endpoint allows setting
  `status` to either `retracted` or `final`

- `ErrataHandler.create` shall we support creating retracted patches via API?
   No.

- `PackageHandler.getDetails`, `PackageHandler.findByNvrea` add a boolean flag
  to the return value, that tells if the package is part of a retracted patch

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


## Iteration 3 - Content Lifecycle management

Enhance Content Lifecycle Manager and notifications.

### Filters

- add a filter that strips retracted patches from the sources

### Projects

- distinguish a project with retracted patch in it
- Warn about out-of-date CLM clones with new retracted patches

### Notifications

Early idea:
- notification after reposync: when some patches got retracted, create a
  notification containing this information:
  - retracted patch details
  - affected channels channels containing the patch
  - channels containing clone of the retracted patch

This must be grouped in a sane way.


## Iteration 4 - deeper UI integration, allow uninstalling a retracted patch
- Channel detail: a warning icon and a message, that the channel contains a
  retracted patch

- Channel list: a warning icon in the list, if the channel contains a retracted
  patch

- System detail: a warning icon and a message, that the system has a retracted
  patch (or its clone) installed

- System list: a warning icon in the list, if the system has a retracted patch
  (or its clone)  installed

As a part of this iteration, evaluate query complexity of underlying queries.


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


# Resolved questions
- Q: how does SUMA upgrade packages/install patches via salt? does it specify
  the version of the upgraded package?
  - A: Yes.
  - patching: we create an action bearing all errata, salt then
    applies state `packages.patchinstall` with all of the patches
  - upgrading: we call `packages.pkginstall` with package name, arch and version  

- Q: Does the feature have any consequences for image building?
  - A: no.

- Q: How does SCC retract the patch? Does it modify the patch with the same id by
   changing `status=stable` to `status=retracted` or does it somehow issue a new
   patch?
   - A: They modify the same patch. The `status` flag will change in the
     repodata for that patch.
     
- Q: Is a system with installed retracted patch supported?
  - A: Yes.
  
- Q: What's the best way to uninstall a retracted patch?
  - A: There is no good way to do this. Downgrading an RPM can always break
    something if it contains pre/post scripts.


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
