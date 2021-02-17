- Feature Name: Live Patching with CLM
- Start Date: 2021-02-08
- RFC PR:

# Summary
[summary]: #summary

Improve live patching workflow using CLM by enhancing user experience.

# Motivation
[motivation]: #motivation

While it is possible to implement a live patching solution in Uyuni using Content Lifecycle Management features, it involves too much manual work and is not an easy thing to do for less experienced users.

This feature is about enhancing the live patching experience in Uyuni by implementing additional CLM functionality to make the process easier for users.

The existing live patching integration in Uyuni is described in the initial [Live Patching RFC](https://github.com/uyuni-project/uyuni-rfc/blob/master/accepted/00027-sle-live-patching.md).

# Detailed design
[design]: #detailed-design

## Live patching CLM workflow

SLES channels can be prepared for live patching applications using the Content Lifecycle Management feature in Uyuni. This is done by adding a set of filters that exclude the regular kernel package updates and include live patch versions of those. However, the UI doesn't provide any special workflow for live patching and this process must be done manually by the user.

Below are some examples of such sets of filters:

**Example A:** Live patching project with a single filter to exclude regular kernel packages newer than a specific version
 - `DENY erratum contains package with epoch/version/release greater than kernel-default <EVR> (package_nevr)`

**Example B:** Live patching project using `ALLOW` overrides
 - `DENY errata containing "update for the Linux Kernel" in synopsis`
 - `ALLOW errata containing "Live Patch" in synopsis` *- an override to the first rule*
 - `ALLOW a specific patch containing current kernel version (via advisory name)` *- an override to the first rule*

**Example C:** Live patching project using reboot flag
 - `DENY errata containing reboot_suggested (keyword)`
 - `ALLOW errata containing "Live Patch" in synopsis` *- an override to the first rule*
 - `ALLOW a specific patch containing current kernel version (via advisory name)` *- an override to the first rule*

## CLM filter wizards

The process of live patching can be made more user-friendly using "CLM filter wizards". The wizards are alternatives to the regular filter creation dialogs that provide a tailored interaction to create multiple filters that serve a single purpose. These dialogs can be accessed via the "Use wizard" button in the filter creation dialog. This concept can be extended to other use cases and workflows in the future.

When completed, the wizard will create the following filter to set up a project for live patching:
```
DENY erratum contains package with epoch/version/release greater than kernel-default <EVR> (package_nevr)
```
Since live patching channels can be composed using the existing filter types, no additional filter type needs to be implemented.

An advantage of this approach is that since the workflow is defined with a regular filter, advanced users can further modify the filters to achieve finer control over the project.

A wizard can be applied on a project at any time, adding the filter as described. Multiple wizards can be applied to a single project and it's the user's responsibility to make sure the created filters do not conflict with each other.

A wizard can be applied independently from a project. In that case, the filter will be created without being added to a specific project. These filters can be used in any project later on.

In scope of this RFC, two different wizards are proposed. The process of creating the filters using these wizards are described below.

### Live patching for a system

 1. Input a label prefix for the resulting filters. If the wizard is accessed from the project view, prefill this field with the project label
 2. Select a SLES client from a combobox
 3. Select a kernel version from a dropdown (current kernel version of the system is preselected)

The resulting filters will set up the project for live patching from the specified kernel version.
If the wizard is accessed from the project view, all the created filters will be automatically added to the project.

### Live patching for a product

 1. Input a label prefix for the resulting filters. If the wizard is accessed from the project view, prefill this field with the project label
 2. Select a synced SLES product from a dropdown
 3. Select a kernel version available in the selected product (latest is preselected)

The resulting filters will set up the project for live patching from the specified kernel version.
If the wizard is accessed from the project view, all the created filters will be automatically added to the project.

## Additional enhancements

### CLM filter list

CLM filter wizards are aimed to make the project creation easier by automatically adding multiple filters. As a consequence, the list of filters in Uyuni can grow very quickly. To handle this problem, the following improvements can be made in the CLM filter list page:

 - Add selection checkboxes to delete multiple filters at once
 - Add "Delete unused/Select unused" shortcuts to delete or select all the filters that are not currently attached to any project
 - Extend the search bar to search by project in use
 - Make the "Project in use" column sortable

### Filter wizards for other purposes

The concept of CLM filter wizards can be easily extended to other use cases as well. An example of such a use case is adding multiple AppStream module filters at once. A wizard called "AppStream modules with defaults" can be implemented with the following workflow:

 1. Input a label prefix for the resulting filters. If the wizard is accessed from the project view, prefill this field with the project label
 2. Select a modular channel from a dropdown
 3. In additional textboxes, add multiple module/stream pairs to override the default streams as required

When done, the wizard creates a module filter per module in the repository, specifying the default stream for that module, or the specified stream if overridden in the wizard.

# Drawbacks
[drawbacks]: #drawbacks

 - The set of filters to be automatically created may not be suitable for some corner cases. The actual filters to be created may be changed a later point in implementation, shaped by the additional feedback.
