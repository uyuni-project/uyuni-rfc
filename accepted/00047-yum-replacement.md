- Feature Name: Migrate away from yum to zypper on spacewalk-repo-sync
- Start Date: 2019-01-02
- RFC PR: https://github.com/SUSE/susemanager-rfc/pull/84/

# Summary
[summary]: #summary

The SUSE Manager server contains a component called "spacewalk-repo-sync" to deal with the external repositories, collect packages, updates and products information from those repositories.

The actual implementation of "spacewalk-repo-sync" is inherited from old spacewalk and it makes use of the "yum" library to deal with the RPM based repositories: read repository and metadata, read packages, resolve dependencies, etc.

This RFC proposes a replacement for this component based on Zypper. This component must also support all different authentication methods (HTTP Proxy, Auth token, NTLM, and all methods covered by current `urlgrabber` library)

# Motivation
[motivation]: #motivation

During the work on making all spacewalk backend code Python 3 compatible, we figured out that `spacewalk-repo-sync` is based on the `yum` library and there is no Python 3 version of `yum`. The natural succesor for `yum` is `dnf` but there are changes in the API so the code needs to be readapted.

After [some talks & discussions](https://github.com/SUSE/salt-board/issues/112) we've decided to go implementing our own solution based on Zypper as repository & metadata downloader in combination with libsolv.

The `spacewalk-repo-sync` is very critical component of SUSE Manager since all repository, channel, package and update handling is depending of this little piece working. A more robust and long-term solution could be researched, even together with refactoring the core of `reposync` and the DownloaderThread.


# Detailed design
[design]: #detailed-design

### The `spacewalk-repo-sync` architecture

![spacewalk-repo-sync diagram](images/reposync-diagram.png)

### The purpose of a "ContentSource" plugin:

Since there are multiple types of content sources (i.a. repositories types), `spacewalk-repo-sync` delegates the handling of each type to plugins. These "ContentSource" plugins must:

- Get repository information and metadata from a repository (ContentSource).
- Provide a list of packages, products and errata coming from that ContentSource. (ContentPackage)
- Provide contact & download parameters to the Downloader Thread for downloading the packages.
- Resolve package dependencies. Since `spacewalk-repo-sync` allows filtering (include/exclude) packages when syncing, package dependencies need to be calculated when running on this mode.

With this information collected by the plugin, the `DownloaderThread` from `reposync` is able to perform the actual download of the necessary package files when `spacewalk-repo-sync` is called.

Currently, `spacewalk-repo-sync` comes with the following plugins:
- `yum_src`: RPM based repositories
- `deb_src`: DEB based repositories
- `uln_src`: Oracle ULN repositories (a wrapper of `yum_src` with custom authentication)

### The "ContentSource" plugin API

Mandatory methods:
- `get_md_checksum_type`: Return the checksum_type of primary.xml
- `get_products`: Return products metadata if any
- `get_susedata`: Return suse metadata if any
- `get_updates`: Return "updateinfo" / "patches" info
- `get_groups`: Return repo groups if any
- `get_file`:
- `get_modules`: Return module metadata if any
- `raw_list_packages`: Return the raw list of packages available after filtering.
- `list_packages`: Return a list of `ContentPackage` rhn class for the available packages after filtering.
- `clear_cache`: Clear cache files
- `set_download_parameters`: Prepare the downloader params dictionary

Yum specific methods we also need to cover:
- `repomd_up_to_date`: Check if repomd.xml checksum is up-to-date.
- `get_metadata_paths`: Simply load primary and updateinfo path from repomd.

#### The "ContentPackage" class
A "ContentSource" plugin needs to provide a list of "ContentPackage" objects to the reposync. This RHN class represents the package like by:

- NEVRA
- unique ID
- checksum
- checksum type

### Replacing "yum" plugin with custom "Zypper" + "libsolv" plugin.

The idea here would be the following:

- The repository metadata downloading is delegated to Zypper (with root parameter)
- The interface to Zypper could be imported from Salt zypper module.
- The downloaded XML metadata can be manually read (packages, updates, products, etc).
- When "zypper refresh" runs, a "solv" file is created containing all needed libsolv data for calculating package dependencies.
- Authentication with ULN repositories is made via Zypper plugin.


#### How to calculate the dependencies?
As mentioned, creates a "solv" file (libsolv) which contains all information needed for resolving the dependencies. To access this information we have two options:

- Pure libsolv approach. Hard since it's a very low level library: [Example of use](https://gist.github.com/mizdebsk/9a792604505634a2942182b761ed0a41)
- Use the [Python Hawkey library](https://github.com/rpm-software-management/hawkey), a simplified libsolv API integrated with ["libdnf"](https://github.com/rpm-software-management/libdnf) (OBS packages at [openSUSE:Factory](https://build.opensuse.org/package/show/openSUSE:Factory/libdnf) - [openSUSE:Backports:SLE-15-SP1](https://build.opensuse.org/package/show/openSUSE:Backports:SLE-15-SP1/libdnf))


#### Detailed proposed steps:

1. Use a new empty root environment for dealing with the particular repo: `/var/cache/rhn/reposync/ORG/MYREPO/`
2. Define the RPM reposity in `/var/cache/rhn/reposync/ORG/MYREPO/etc/zypp/repos.d/MYREPO.repo`
3. Run `zypper --root=/var/cache/rhn/reposync/ORG/MYREPO/ refresh` so Zypper download repository information, metadata and creates the "solv" file.
4. Since metadata XML files are downloaded by Zypper, metadata can be read.
5. To solve package dependencies the plugin would use the already create "solv" file, containing the data generated by libsolv for this repository.
6. To read the "solv" file,  `hawkey` [Github](https://github.com/rpm-software-management/hawkey) which is now integrated and shipped as part of `libdnf`: [GitHub](https://github.com/rpm-software-management/libdnf) - [OBS Package](https://build.opensuse.org/package/show/openSUSE:Backports:SLE-15-SP1/dnf). These libraries allows us to resolve package dependencies based on the solv file created by Zypper.


#### Requirements for this approach:
- We would need to use `python3-hawkey` library ([OBS link](https://build.opensuse.org/package/show/openSUSE:Backports:SLE-15-SP1/libdnf)) in order to read the "solv" file generated by Zypper when refreshing the repositories.
- Use `urlgrabber` to cover all different contact and authentication methods we already support. We've already ported `urlgrabber` to Python 3 as part of the cobbler migration to Python 3.


#### Authentication with ULN repositories
As mentioned, the current ULN plugin for "reposync" is essentially a wrapper on top of the "yum" plugin. It performs an initial XMLRPC call to ULN server to authenticate and get a token which is added into the HTTP headers when accessing the repository. This can be easily implemented via Zypper plugin.


### Alternative Proposal: Migrate to DNF without using Zypper.
Since we're already requiring "hawkey" / "libdnf" for the Zypper approach, we would need to partially depend on "dnf" anyway, so another similar approach here would be go by simple migrating to use the [Python DNF API](https://dnf.readthedocs.io/en/latest/api.html) - ([OBS Package](https://build.opensuse.org/package/show/openSUSE:Backports:SLE-15-SP1/dnf)) instead of the current Python YUM library.

This approach would be the natural step to do since it follows the same approach that we currently follow on the "yum" plugin we want to migrate.

## DNF / Hawkey / libsolv Python code examples
- Some DNF use cases from Python: https://dnf.readthedocs.io/en/latest/use_cases.html
- Working with DNF: http://abregman.com/2016/11/29/python-working-with-rpms/
- Using Python Hawkey to read solv file and resolve depencencies (high level): https://hawkey.readthedocs.io/en/latest/tutorial-py.html#resolving-things-with-goals
- Example of using pure libsolv in Python to solve dependencies (low level): https://gist.github.com/mizdebsk/9a792604505634a2942182b761ed0a41


# Implementation roadmap:
[roadmap]: #roadmap
Since implementation of this feature overlaps the alpha release calendar, the discussed idea would be:

- First iteration - before alpha2 (8th February):
  - Migrate from Yum to Zypper.
  - Allow syncing channels.
  - Do not support filtering. Vendor channels will work without limitation.

- Second iteration - after alpha2:
  - Add support for resolving dependencies using `libsolv`. This will enables filtering when syncing packages.

- Third iteration (not required):
  - Migrate away from `urlgrabber` in the `DownloaderThread` since `python3-urlgrabber` is not going to be maintained upstream.


# Drawbacks
[drawbacks]: #drawbacks

- ULN authentication plugin is needed for Zypper (authentication is really simple here though - not much code to maintain)


# Alternatives
[alternatives]: #alternatives
Since `yum` plugin needs to be replaced in `spacewalk-repo-sync`, there are few other alternatives that were also considered as we will see next.

- Migrate `yum` and `urlgrabber` to Python 3. This was initially discarded since `urlgrabber` is dead and we don't want to keep stuck to "yum". It's time to change.

- Create our own repodownloader component based on `libsolv` python bindings. We would have full control but that would require more effort to implement all the download cycle + collecting and reading metadata with pure `libsolv`.


# Unresolved questions
[unresolved]: #unresolved-questions

1. What to choose? Given SUSE Manager 4.0 alpha1 is scheduled for mid-January.
- "Zypper" + pure "libsolv" (Probably require more efforts)
- "Zypper" + "DNF/hawkey" (Simplified API with libsolv)
- "DNF only"

We've decided to go with "Zypper" + pure "libsolv" approach as described in [Implementation Roadmap](#roadmap). In case a pure "libsolv" approach turns too hard for resolving package dependencies in our context, we will fall-back to "Zypper" + "hawkey/dnf".

---

2. Is Zypper actually able to deal with RedHat CDN authentication (client certificate)? Yes, it does: https://github.com/openSUSE/zypper/blob/master/doc/zypper.8.txt#L992
