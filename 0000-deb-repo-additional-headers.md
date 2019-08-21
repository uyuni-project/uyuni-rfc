- Feature Name: deb_repo_additional_fields
- Start Date: 12-06-2019
- RFC PR: (leave this empty)

# Summary

Support additional packages fields in Debian repos.

# Motivation

- Why are we doing this?
- What use cases does it support?
- What is the expected outcome?

Uyuni doesn't expose all the metadata coming from the upstream repos. Additional package metadata like `Multi-Arch` is needed by `apt` in some cases to avoid installing a package over and over again.
Uyuni must be able to create Debian repositories with the correct metadata.

# Detailed design

## Repo syncing

When `spacewalk-repo-sync` parses the `Package.xz|gz` file it must take into account any additional fields.
Currently it takes into account only theses fields: `Package`, `Architecture`, `Version`, `Filename`, `SHA256`, `SHA1`, `MD5Sum`.
Any other fields should be saved in the database.

E.g. `Packages` entry:
```
Package: apache2-data
Architecture: all
Version: 2.4.29-1ubuntu4.6
Multi-Arch: foreign
Priority: optional
Section: httpd
Source: apache2
Origin: Ubuntu
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Original-Maintainer: Debian Apache Maintainers <debian-apache@lists.debian.org>
Bugs: https://bugs.launchpad.net/ubuntu/+filebug
Installed-Size: 870
Filename: pool/main/a/apache2/apache2-data_2.4.29-1ubuntu4.6_all.deb
Size: 159984
MD5sum: 7d4e4ad49eb6c5014d5453721573e637
SHA1: 1824d3d176e7db8010216abc2f0962ac2fe5531f
SHA256: 594070814770a028a9eb3924d02b22fcb818d83b311710aaac304a9064479292
Homepage: http://httpd.apache.org/
Description: Apache HTTP Server (common files)
Task: lamp-server
Description-md5: 9f2fab36019a61312dec627d1cd80365
Supported: 5y
```

The database schema needs to be extended with new tables to store the additional fields not covered by the existing `rhnPackage*` tables:
```
rhnPackageExtraTags
====================
id          number not null
name        string no null
value       string not null
created     timestamp
modified    timestamp

primary key (id)
```

Another new table is needed to store the association of a GPG key to a repository:
```
rhnContentSourceGpg
====================
content_source_id   number not null foreign key rhnContentSource(id)
gpg_key_id          number not null foreign key rhnCryptoKey(id)
created             timestamp
modified            timestamp

```

The class `com.redhat.rhn.taskomatic.task.repomd.DebPackageWriter` must be enhanced to write any additional fields stored in the database into the generated `Packages.gz` file.

_Note_: The same structure could be used to store additional RPM headers not yet stored. The corresponding class that needs to be changed is `com.redhat.rhn.taskomatic.task.repomd.PrimaryXmlWriter`.

## Repo signature checking

In order to import the metadata in a secure way Uyuni should be able to verify the GPG signature of that metadata.
The GPG verification should be optional but a warning should be shown to the the user in case he's not providing information about the GPG key used to verify the metadata.

### Repo metadata location and signatures

_Note: this section is only informative_

Debian/Ubuntu repos use GPG signing to ensure the integrity of the `Release` file. The signature can be either in a separate file `Release.gpg` or inline in a file called `InRelease`. If both files are present the `InRelease` file is preferred.

Typically the structure of a repo is like this:
```
http://mirror.example.com/ubuntu  <- $ARCHIVE_ROOT
|
+- dists/bionic                   <- Suite or Codename
   |
   +- main                        <- $COMPNENT directories
      |
      +- binary-amd64
         |
         +- Packages.gz           <- Packages indices
         +- Packages.xz
         . . .
      +- binary-i386
      . . .
   +- universe
   . . .
   +- Release                     <- Plain file
   +- InRelease                   <- Release file + inline signature
   +- Release.gpg                 <- Separate signature

```

E.g. for official Ubuntu repos the URL of these files:
```
http://mirror.example.com/ubuntu/dists/bionic-updates/InRelease
http://mirror.example.com/ubuntu/dists/bionic-updates/Release.gpg
```

There's also an alternative layout for Debian repos called "flat repos". In this case the repo directory containins both `Release*` and `Packages*` files. E.g.:
```
https://download.opensuse.org/repositories/systemsmanagement:/Uyuni:/Master:/Ubuntu1804-Uyuni-Client-Tools/xUbuntu_18.04/
```

_Note #1:_

In Uyuni the URL of a deb repository must point to the directory containing the binary packages for a specific architecture. E.g. for Ubuntu 18.04 updates repo is something like:
```
http://mirror.example.com/ubuntu/dists/bionic-updates/main/binary-amd64/
```
or in case of a flat repository to the directory containing both `Release*` and `Packages*` files:
```
https://download.opensuse.org/repositories/systemsmanagement:/Uyuni:/Master:/Ubuntu1804-Uyuni-Client-Tools/xUbuntu_18.04/
```

_Note #2:_

Debian repos don't have a standard location for the public GPG keys used to verify the metadata. Sometimes the key is located in the root of a flat repo but the location is not standardized.

### GPG keys management

Uyuni ships the SUSE and OpenSUSE keys in the package `uyuni-build-keys`. The keys for Ubuntu and Debian should be shipped in this package too.

Any additional keys that need to be used (e.g. for Ubuntu derivatives distros or for custom repos) must be created manually using the existing UI (`Systems -> Autoinstallation -> GPG and SSL keys`)


### GPG Key usage in the UI

The UI for creating/updating a repository (`Software -> Manage -> Repositories`) must be extended with one additional field:
- GPG key

This field must be visible only if the selected repository type is `deb` and the checkbox `Has Signed Metadata` is checked. For `deb` repositories the `Has Signed Metadata` checkbox must be enabled by default.

The field must be shown as a selector. The values used to populate the selector come from the existing table `rhnCryptoKey`. Only keys for current organization must be shown.

An additional option `Default keys` must shown in the selector as default. If this option is selected, the validation will be done using the GPG keys from package `uyuni-build-keys`.

When saving the repository data, in case there was a GPG key selected other then `Default keys` the assignment will be saved into the new table `rhnContentSourceGpg`.

### Key usage in the API

The API method `channel.software.create_repo()` must be extended with one optional arguments to allow specifying the `GPG key ID`.

An error should be thrown if the the GPG key does not exist.

### Metadata and signature lookup

In order to verify integrity of the `Packages.gz` file Uyuni must first lookup the `Release` file and verify its signature. This file can be in one of these locations:
- `http://mirror.example.com/$ARCHIVE_ROOT/dists/$DIST` in case of repos with a `dists` directory when the Uyuni repo URL points to `http://mirror.example.com/$ARCHIVE_ROOT/dists/$DIST/$COMPONENT/binary-$ARCH/`.
- `http://mirror.example.com/$REPODIR/` in the case of flat repositories

Looking up the `Release` file should be done automatically when syncing of the repo. An error should be shown if it's not possible to locate the `Release` file and its corresponding signature.

### Metadata Verification

Uyuni should verify the integrity of the `Packages.gz|xz` files using the checksums present in the `Release` file.

### GPG signature verification

If the `InRelease` or `Release.pgg` exist in the repo to be synced then Uyuni must verify the `Release` file. If the repo has signed metadata enabled but no GPG key selected, the default keyring must be used:
```
gpgv --keyring /var/lib/spacewalk/gpgdir/pubring.gpg InRelease
```
or
```
gpgv --keyring /var/lib/spacewalk/gpgdir/pubring.gpg Release.gpg Release
```

Otherwise the custom GPG key associated with the repo must be used:
```
gpgv --keyring </path/to/temp/keyring/file.gpg> InRelease
```
or
```
gpgv --keyring </path/to/temp/keyring/file.gpg> Release.gpg Release
```

The signature verification should be done during repo syncing when the metadata is parsed.
Verification must be done only if the user has configured the GPG signing of the repos to be synced. Otherwise a warning must be printed in the logs about the lack of GPG configuration.


# Drawbacks
[drawbacks]: #drawbacks

No drawbacks.

# Alternatives
[alternatives]: #alternatives

- Support only a very limited set of additional fields like `Multi-Arch` while discarding all others.

# Unresolved questions
[unresolved]: #unresolved-questions

- Should all the fields be stored ? Should only the fields defined in [1] be stored ? If yes what happens with user defined fields [2]
- In case no GPG keys are configured for a repo (i.e. no GPG verification needed) should the `Release` file still be looked up and the checksums verified ?

# References

1. [Debian Policy Manual: Control files and their fields](https://www.debian.org/doc/debian-policy/ch-controlfields.html)
2. [Debian Policy Manual: User defined fields](https://www.debian.org/doc/debian-policy/ch-controlfields.html#user-defined-fields)
3. [Debian repository format](https://wiki.debian.org/DebianRepository/Format)
