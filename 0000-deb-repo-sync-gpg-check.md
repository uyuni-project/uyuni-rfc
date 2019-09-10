- Feature Name: deb_repo_sync_gpg_check
- Start Date: 12-06-2019
- RFC PR: (leave this empty)

# Summary

Verify GPG signature of Debian repositories when synchronizing.

# Motivation

- Why are we doing this?
- What use cases does it support?
- What is the expected outcome?

Uyuni can synchronize Debian repositories but currently it doesn't verify the GPG signature of the repo metadata.
In order to import the metadata in a secure way Uyuni must be able to verify the GPG signature of that metadata.

# Detailed design

## Database changes

A new table is needed to store the association of a GPG key to a repository:
```
rhnContentSourceGpg
====================
content_source_id   number not null foreign key rhnContentSource(id)
gpg_key_id          number not null foreign key rhnCryptoKey(id)
created             timestamp
modified            timestamp

```

## Repo signature checking

The GPG verification must be done always. The user should have the option to disable it.

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

### GPG keys management for official repositories

Uyuni ships the SUSE and OpenSUSE keys in the package `uyuni-build-keys`. The Ubuntu and Debian will be shipped in separate packages, i.e. `debian-build-keys` and `ubu-build-keys`.

### GPG keys management for third-party repositories

Any additional keys that need to be used (e.g. for Ubuntu derivatives distros or for custom repos) must be created manually using the existing UI (`Systems -> Autoinstallation -> GPG and SSL keys`)

### GPG Key usage in the UI

The UI for creating/updating a repository (`Software -> Manage -> Repositories`) must be extended with one additional field:
- GPG key

This field must be visible only if the selected repository type is `deb` and the checkbox `Has Signed Metadata` is checked. For `deb` repositories the `Has Signed Metadata` checkbox must be checked by default.

The field must be shown as a selector. The values used to populate the selector come from the existing table `rhnCryptoKey`. Only keys for current organization must be shown.

An additional option `Default keys` must shown in the selector as default. If this option is selected, the validation will be done using the GPG keys from package `uyuni-build-keys`.

When saving the repository data, in case there was a GPG key selected other then `Default keys` the assignment will be saved into the new table `rhnContentSourceGpg`.

### Key usage in the API

The API method `channel.software.create_repo()` must be extended with one optional arguments to allow specifying the `GPG key ID`.

An error should be thrown if the the GPG key does not exist.

### Key import via `spacewalk-repo-sync`

`spacewalk-repo-sync` must be extended to be able to import the GPG keys configured in `rhnContentSourceGpg`. Similarly to Yum repos, the user should be asked for confirmation when importing the keys.

### Metadata and signature lookup

In order to verify integrity of the `Packages.gz` file Uyuni must first lookup the `Release` file and verify its signature. This file can be in one of these locations:
- `http://mirror.example.com/$ARCHIVE_ROOT/dists/$DIST` in case of repos with a `dists` directory when the Uyuni repo URL points to `http://mirror.example.com/$ARCHIVE_ROOT/dists/$DIST/$COMPONENT/binary-$ARCH/`.
- `http://mirror.example.com/$REPODIR/` in the case of flat repositories

Looking up the `Release` file should be done automatically when syncing of the repo. An error should be shown if it's not possible to locate the `Release` file and its corresponding signature.

### Metadata Verification

Uyuni should verify the integrity of the `Packages.gz|xz` files using the checksums present in the `Release` file.

### Signature verification

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


# Unresolved questions
[unresolved]: #unresolved-questions

- In case no GPG keys are configured for a repo (i.e. no GPG verification needed) should the `Release` file still be looked up and the checksums verified ?

# References

1. [Debian repository format](https://wiki.debian.org/DebianRepository/Format)
