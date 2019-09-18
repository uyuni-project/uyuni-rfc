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

The database schema needs to be extended with a new table to store the additional fields not covered by the existing `rhnPackage*` tables:
```
rhnPackageExtraTagKey
=====================
id          NUMERIC NOT NULL
name        VARCHAR(256) NOT NULL

rhnPackageExtraTag
====================
package_id  NUMERIC NOT NULL
                   REFERENCES rhnPackage (id),
key_id      NUMERIC NOT NULL
                   REFERENCES rhnPackageExtraTagKey (id),
value       VARCHAR(2048) NOT NULL,
primary key (package_id, key_id)
```

The class `com.redhat.rhn.taskomatic.task.repomd.DebPackageWriter` must be enhanced to write any additional fields stored in the database into the generated `Packages.gz` file.

_Note_: The same structure could be used to store additional RPM headers not yet stored. The corresponding class that needs to be changed is `com.redhat.rhn.taskomatic.task.repomd.PrimaryXmlWriter`.


### Metadata location and signatures

In order to verify integrity of the `Packages.gz` file Uyuni must first lookup the `Release` file and verify the checksum it contains and its GPG signature. This file can be in one of these locations:
- `http://mirror.example.com/$ARCHIVE_ROOT/dists/$DIST` in case of repos with a `dists` directory when the Uyuni repo URL points to `http://mirror.example.com/$ARCHIVE_ROOT/dists/$DIST/$COMPONENT/binary-$ARCH/`.
- `http://mirror.example.com/$REPODIR/` in the case of flat repositories

Looking up the `Release` file should be done automatically when syncing of the repo. An error should be shown if it's not possible to locate the `Release` file.

_Note #1: debian repo structure_

Debian/Ubuntu repos use GPG signing to ensure the integrity of the `Release` file. The signature can be either in a separate file `Release.gpg` or inline in a file called `InRelease`. If both files are present the `InRelease` file is preferred.

Typically the structure of a repo is like this:
```
http://mirror.example.com/ubuntu  <- $ARCHIVE_ROOT
|
+- dists/bionic                   <- Suite or Codename
   |
   +- main                        <- $COMPNENT directories
      |
      +- binary-amd64             <- Architecture
         |
         +- Packages.gz           <- Packages indices
         +- Packages.xz
         +- Release               <- Legacy, not used by modern clients
         . . .
      +- binary-i386
         . . .
   +- universe
   . . .
   +- Release                     <- Plain file
   +- Release.gpg                 <- Detached signature
   +- InRelease                   <- Release file + inline signature
```

E.g. for official Ubuntu repos the URL of these files:
```
http://mirror.example.com/ubuntu/dists/bionic-updates/InRelease
http://mirror.example.com/ubuntu/dists/bionic-updates/Release.gpg
```

There's also an alternative layout for Debian repos called "flat repos". In this case the repo directory contains both `Release*` and `Packages*` files. E.g.:
```
https://download.opensuse.org/repositories/systemsmanagement:/Uyuni:/Master:/Ubuntu1804-Uyuni-Client-Tools/xUbuntu_18.04/
```

_Note #2:_

In Uyuni the URL of a deb repository must point to the directory containing the binary packages for a specific architecture. E.g. for Ubuntu 18.04 updates repo is something like:
```
http://mirror.example.com/ubuntu/dists/bionic-updates/main/binary-amd64/
```
or in case of a flat repository to the directory containing both `Release*` and `Packages*` files:
```
https://download.opensuse.org/repositories/systemsmanagement:/Uyuni:/Master:/Ubuntu1804-Uyuni-Client-Tools/xUbuntu_18.04/
```

### Metadata Checksum Verification

Uyuni should verify the integrity of the `Packages.gz|xz` files using the checksums present in the `Release` file.
The integrity of the `deb` binary packages must be verified using the checksums from the `Packages` file.

### GPG signature checking and checksum verification

This will be handled in a separate RFC.

## Failure Registry

Packages might have sync issues, such as wrong GPG signature or
checksum mismatch or downloading issues etc. However, broken packages
still can be assigned to the channels/repos and thus potentially
invaliadate them. In some circumstances this might have serious impact
on the infrastructure update performance. To avoid that, we need to
have a mechanism that will verify if a particular channel is "clean",
i.e. no any broken packages involved.

### Use Case Scenario Example

Following example can happen:

1. An admin runs reposync in a background.
2. Broken package appears, reposync is writing an error in the log, as
   usual.
3. The error is not noticed by another admin on a shift (UX is unused
   at the moment, other circumstances).
4. Synchronised channel is noticed and thus scheduled for an update.
5. An update cannot be completed due to broken package.

In this case an admin did not noticed that the channel contains broken
packages and thus should not be recommended for an update, but such repo
needs to be fixed first. Or such repo can be still used in case none
of dependencies are involved, but still admin needs to be aware of it.

### Solution

The solution is simply add the following table:

```
rhnPackageErrors
================
package_id  NUMERIC NOT NULL
error       VARCHAR NOT NULL
```

During the synchronisation, reposync will log all errors about broken
packages. Later on, UX can use this information for various purposes,
such as:
1. Mark with an icon for the channel(s) has issues (permanent reminder)
2. Display more detailed drill-down what packages are affected and why
3. Display a warning/confirmation dialog for admin, once affected
   channel is attempted to be scheduled for something.

In case package cannot be synchronised at all due to various reasons,
the information about it still needs to be appearing in the database
and marked as "broken". So then tools, like `spacewalk-data-fsck` can
verify that the record is there, but the file isn't etc. As well as an
error message can be placed to the log table "File was unable to be
downloaded".

This information can be reused across all the channels, UI and CLI
tools to display warning/status of a specified channel.

# Drawbacks
[drawbacks]: #drawbacks

No drawbacks.

# Alternatives
[alternatives]: #alternatives

- Support only a very limited set of additional fields like `Multi-Arch` while discarding all others.

# Unresolved questions
[unresolved]: #unresolved-questions



# References

1. [Debian Policy Manual: Control files and their fields](https://www.debian.org/doc/debian-policy/ch-controlfields.html)
2. [Debian Policy Manual: User defined fields](https://www.debian.org/doc/debian-policy/ch-controlfields.html#user-defined-fields)
3. [Debian repository format](https://wiki.debian.org/DebianRepository/Format)
