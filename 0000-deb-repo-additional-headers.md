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
rhnPackageExtraTags
====================
id          number not null
name        string no null
value       string not null
created     timestamp
modified    timestamp

primary key (id)
```

The class `com.redhat.rhn.taskomatic.task.repomd.DebPackageWriter` must be enhanced to write any additional fields stored in the database into the generated `Packages.gz` file.

_Note_: The same structure could be used to store additional RPM headers not yet stored. The corresponding class that needs to be changed is `com.redhat.rhn.taskomatic.task.repomd.PrimaryXmlWriter`.


### Metadata and signature lookup

In order to verify integrity of the `Packages.gz` file Uyuni must first lookup the `Release` file and verify the checksum it contains and its GPGc signature. This file can be in one of these locations:
- `http://mirror.example.com/$ARCHIVE_ROOT/dists/$DIST` in case of repos with a `dists` directory when the Uyuni repo URL points to `http://mirror.example.com/$ARCHIVE_ROOT/dists/$DIST/$COMPONENT/binary-$ARCH/`.
- `http://mirror.example.com/$REPODIR/` in the case of flat repositories

Looking up the `Release` file should be done automatically when syncing of the repo. An error should be shown if it's not possible to locate the `Release` file and its corresponding signature.

### Metadata Checksum Verification

Uyuni should verify the integrity of the `Packages.gz|xz` files using the checksums present in the `Release` file.
The integrity of the `deb` binary packages must be verified using the checksums from the `Packages` file.

### GPG signature checking

This will be handled in a separate RFC.


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
