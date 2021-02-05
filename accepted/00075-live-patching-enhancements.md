- Feature Name: Live Patching Enhancements
- Start Date: (fill with today's date, YYYY-MM-DD)
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

Enhance live patching integration by providing EOL information on installed patches.

Improve live patching workflow using CLM.

# Motivation
[motivation]: #motivation

SUSE only provides live patches for kernels up to 1 year after original release date of that kernel. It means that after one year, the user must reboot and use a new kernel so that they can keep getting live patches for another year.

This feature is about enhancing the live patching experience in SUSE Manager by implementing the following improvements:

1. Add information about the EOL of kernels in the UI
2. Warn user when a live kernel is approaching EOL, or past EOL
3. Add CLM filters to make package selection easier

The existing live patching integration in Uyuni is described in the initial [Live Patching RFC](https://github.com/uyuni-project/uyuni-rfc/blob/master/accepted/00027-sle-live-patching.md).

# Detailed design
[design]: #detailed-design

This design provides solutions for two separate problems regarding to kernel live patching:

1. [Live patching EOL information](#live-patching-eol-information)
2. [Live patching CLM workflow](#live-patching-clm-workflow)

## 1. Live patching EOL information

SUSE provides lifecycle information on any product to users via 'zypper lifecycle' plugin. The actual data about a product is provided in a plain CSV file in a supplementary package per product. In case of live patching, this package is called `lifecycle-data-sle-module-live-patching` and is installed together with the product. Zypper lifecycle plugin reads this data to display human-friendly information to users.

Uyuni shall use this information to provide the following:
 - Display EOL dates for the current live patch in system details
 - Display an out-of-support systems list in the home page
 - Use the notifications system and/or send emails to report live patched systems approaching/past EOL
 - The notifications/emails will be sent in advance according to a time value configurable from the UI

### Data Retrieval

This section evaluates three alternative implementations for this feature.

#### Call 'zypper lifecycle' on client

Uyuni calls `zypper lifecycle` on the client and collects the data via Salt during package profile update. The data is then stored in the database per client along with the kernel live version data.

**Pros:**
 - `zypper lifecycle` is publicly supported
 - Can be called directly for a package name (a specific live-patch package)
 - Can be attached to profile update data with an existing process

**Cons:**
 - Is a 2-step process that requires `zypper lifecycle` to output to a file
 - `zypper-lifecycle-plugin` needs to be installed on the client
 - Requires a round-trip to the client, per client

#### Read the lifecycle data file on client

Uyuni runs a Salt state to read the lifecycle data file provided with the package `lifecycle-data-sle-module-live-patching` on the client and collects the data during package profile update. The data is then stored in the database per client along with the kernel live version data.

**Pros:**
 - Easy to implement
 - Can be attached to profile update data with an existing process

**Cons:**
 - File name or format can change in the future
 - Requires a round-trip to the client, per client

#### Unpack and read the lifecycle data RPM on Uyuni server

The lifecycle information for a product is provided with `*.lifecycle` files inside a separate package. Uyuni unpacks this RPM and reads the data from the extracted CSV file during reposync of this product. The data is stored in the database per package.

An example SQL query to retrieve the list of RPMs to unpack and the corresponding files to read from:
```
SELECT
    c.name filename,
    p.path rpm_path
FROM
    rhnPackage p
    JOIN rhnPackageFile f ON p.id = f.package_id
    JOIN rhnPackageCapability c ON c.id = f.capability_id
    JOIN rhnPackageEvr e ON p.evr_id = e.id
WHERE
    --Select packages that have '*.lifecycle' files in them
    c.name LIKE '%.lifecycle' AND
    e.evr = (
        --Select latest EVR for a package name
        SELECT MAX(evr)
        FROM rhnPackageEvr se
            JOIN rhnPackage sp ON se.id = sp.evr_id
        WHERE sp.name_id = p.name_id
    );
```

The output is a list of RPM paths in the local filesystem and the packed filenames to extract the data from:
```
                      filename                       |                         rpm_path
-----------------------------------------------------+----------------------------------------------------------
 /var/lib/lifecycle/data/sle-live-patching.lifecycle | .../lifecycle-data-sle-live-patching-1-10.79.1.noarch.rpm

```

The list of RPMs are unpacked into a temp directory and the corresponding files are read into a table called `susePackageLifecycle` with the following structure:
 - `package_id` as a foreign key to `rhnPackage` table
 - `eol_date` of `DATE` type

**Pros:**
 - Independent, no impositions on clients
 - Gathered data is always available and can be used for UI enhancements such as displaying EOL info for all live patch packages displayed in the UI

**Cons:**
 - RPM format can change in the future
 - Uyuni doesn't have any existing functionality that can be utilized
 - Unpacking must be done during reposync, adding complication

## 2. Live patching CLM workflow

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

### CLM filter wizards

The process of live patching can be made more user-friendly using "CLM filter wizards". The wizards are alternatives to the regular filter creation dialogs that provide a tailored interaction to create multiple filters that serve a single purpose. These dialogs can be accessed via the "Use wizard" button in the filter creation dialog. This concept can be extended to other use cases and workflows in the future.

When completed, the wizards will create multiple filters that look like the examples mentioned in the section above to set up a project with a specific purpose. Since live patching channels can be composed using the existing filter types, no additional filter type needs to be implemented.

An advantage of this approach is that since the workflow is defined with a set of regular filters, advanced users can modify these filters to achieve finer control over the project.

A wizard can be applied on a project at any time, adding filters as described. Multiple wizards can be applied to a single project and it's the user's responsibility to make sure the created filters do not conflict with each other.

A wizard can be applied independently from a project. In that case, the filters will be created without being added to a specific project. These filters can be used in any project later on.

In scope of this RFC, two different wizards are proposed. The process of creating the filters using these wizards are described below.

#### Live patching for a system

 1. Input a label prefix for the resulting filters. If the wizard is accessed from the project view, prefill this field with the project label
 2. Select a SLES client from a combobox
 3. Select a kernel version from a dropdown (current kernel version of the system is preselected)

The resulting filters will set up the project for live patching from the specified kernel version.
If the wizard is accessed from the project view, all the created filters will be automatically added to the project.

#### Live patching for a product

 1. Input a label prefix for the resulting filters. If the wizard is accessed from the project view, prefill this field with the project label
 2. Select a synced SLES product from a dropdown
 3. Select a kernel version available in the selected product (latest is preselected)

The resulting filters will set up the project for live patching from the specified kernel version.
If the wizard is accessed from the project view, all the created filters will be automatically added to the project.

#### Additional enhancements

##### CLM filter list

CLM filter wizards are aimed to make the project creation easier by automatically adding multiple filters. As a consequence, the list of filters in Uyuni can grow very quickly. To handle this problem, the following improvements can be made in the CLM filter list page:

 - Add selection checkboxes to delete multiple filters at once
 - Add "Delete unused/Select unused" shortcuts to delete or select all the filters that are not currently attached to any project
 - Extend the search bar to search by project in use
 - Make the "Project in use" column sortable

##### Filter wizards for other purposes

The concept of CLM filter wizards can be easily extended to other use cases as well. An example of such a use case is adding multiple AppStream module filters at once. A wizard called "AppStream modules with defaults" can be implemented with the following workflow:

 1. Input a label prefix for the resulting filters. If the wizard is accessed from the project view, prefill this field with the project label
 2. Select a modular channel from a dropdown
 3. In additional textboxes, add multiple module/stream pairs to override the default streams as required

When done, the wizard creates a module filter per module in the repository, specifying the default stream for that module, or the specified stream if overridden in the wizard.

# Drawbacks
[drawbacks]: #drawbacks

 - Gathering lifecycle data from the client is initially the easier option, but depending on clients is unnecessary and execution is duplicated per-client.

# Alternatives
[alternatives]: #alternatives

Alternative implementations for EOL data retrieval are mentioned in the [data retrieval](#data-retrieval) section.

# Unresolved questions
[unresolved]: #unresolved-questions

 - Which approach shall be used for [EOL data retrieval](#data-retrieval)?
 - What is the roadmap for `zypper lifecycle` and the lifecycle data format?
 - What is the best way to define a live patching project with the existing filters (see [Live patching CLM workflow](#live-patching-clm-workflow))?
 - Do we plan to extend the EOL reporting to other products in the future?

# TODO

 - Split EOL data and CLM improvements into separate RFCs
