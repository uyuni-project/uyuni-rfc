- Feature Name: Live Patching EOL Date Information
- Start Date: 2021-02-08
- RFC PR:

# Summary
[summary]: #summary

Enhance live patching integration by providing EOL information on installed patches.

# Motivation
[motivation]: #motivation

SUSE only provides live patches for kernels up to 1 year after original release date of that kernel. It means that after one year, the user must reboot and use a new kernel so that they can keep getting live patches for another year.

This feature is about enhancing the live patching experience in Uyuni by implementing the following improvements:

1. Add information about the EOL of kernels in the UI
2. Warn user when a live kernel is approaching EOL, or past EOL

The existing live patching integration in Uyuni is described in the initial [Live Patching RFC](https://github.com/uyuni-project/uyuni-rfc/blob/master/accepted/00027-sle-live-patching.md).

# Detailed design
[design]: #detailed-design

## Live patching EOL information

SUSE provides lifecycle information on any product to users via 'zypper lifecycle' plugin. The actual data about a product is provided in a plain CSV file in a supplementary package per product. In case of live patching, this package is called `lifecycle-data-sle-live-patching` and is installed together with the product. Zypper lifecycle plugin reads this data to display human-friendly information to users.

Uyuni shall use this data to provide the following:
 - Display EOL dates for the current live patch in system details
 - Display an out-of-support systems list in the home page
 - Use the notifications system and/or send emails to report live patched systems approaching/past EOL
 - The notifications/emails will be sent in advance according to a time value configurable from the UI

## Data Retrieval

The lifecycle information for a product is provided with `*.lifecycle` files inside a separate package. Uyuni shall unpack this RPM and read the data from the extracted CSV file during reposync of this product. The data shall be stored in the database per package.

An example SQL query to retrieve the list of RPMs to unpack and the corresponding files to read from:

```sql
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

 The data stored in this table is available to be queried and consumed in the UI.

 *For other methods of data retrieval that are evaluated in the design, see [Alternatives](#alternatives).*

# Drawbacks
[drawbacks]: #drawbacks

 - Unpacking must be done during reposync, adding complication
 - Any future changes in the data format must be tracked and the implementation must be adapted accordingly
 - Renames on lifecycle data packages cannot be detected. A possible workaround to this is to unpack the data in order of build date, and overwrite the rows in case of any conflicts so that the latest info is current.

# Alternatives
[alternatives]: #alternatives

Alternative implementations for EOL data retrieval are described below.

## Call 'zypper lifecycle' on client

Uyuni calls `zypper lifecycle` on the client and collects the data via Salt during package profile update. The data is then stored in the database per client along with the kernel live version data.

**Pros:**
 - `zypper lifecycle` is publicly supported
 - Can be called directly for a package name (a specific live-patch package)
 - Can be attached to profile update data with an existing process

**Cons:**
 - Is a 2-step process that requires `zypper lifecycle` to output to a file
 - `zypper-lifecycle-plugin` needs to be installed on the client
 - Requires a round-trip to the client, per client

## Read the lifecycle data file on client

Uyuni runs a Salt state to read the lifecycle data file provided with the package `lifecycle-data-sle-module-live-patching` on the client and collects the data during package profile update. The data is then stored in the database per client along with the kernel live version data.

**Pros:**
 - Easy to implement
 - Can be attached to profile update data with an existing process

**Cons:**
 - File name or format can change in the future
 - Requires a round-trip to the client, per client

# Unresolved questions
[unresolved]: #unresolved-questions

 - Shall we prune the lifecycle data before each reposync?
