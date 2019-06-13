- Feature Name: deb_repo_additional_headers
- Start Date: 12-06-2019
- RFC PR: (leave this empty)

# Summary

Support additional packages headers in Debian repos.

# Motivation

- Why are we doing this?
- What use cases does it support?
- What is the expected outcome?

Uyuni doesn't expose all the metadata coming from the upstream repos. Additional package metadata like `Multi-Arch` is needed by `apt` in some cases to avoid installing a package over and over again.
Uyuni should copy the package metadata into its channels.

# Detailed design

## Repo syncing

When `spacewalk-repo-sync` parses the `Package.xz|gz` file it must take into account any additional headers.
Currently it takes into account only theses headers: `Package`, `Architecture`, `Version`, `Filename`, `SHA256`, `SHA1`, `MD5Sum`.

The database schema needs to be extended with a new table to store the additional headers:
```
rhnPackageDebHeadersValues
==========================
package_id  number foreign key rhnPackage(id)
header_id   number foreign key rhnPackageDebHeaders(id)
value       string not null
created     timestamp
modified    timestamp

primary key (package_id, header_id)

rhnPackageDebHeaders
====================
id          number
name        string
created     timestamp
modified    timestamp

primary key (id)
```

The class `com.redhat.rhn.taskomatic.task.repomd.DebPackageWriter` must be changed to write any additional headers stored in the database into the generated `Packages.gz` file.

## Repo signature checking

### Repo metadata location and signatures

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

In Uyuni the URL of a deb repository points to the directory containing the binary packages for a specific architecture. E.g. for Ubuntu 18.04 updates repo is something like:
```
http://mirror.example.com/ubuntu/dists/bionic-updates/main/binary-amd64/
```

In case of flat repos the URL points to a directory containing both `Release*` and `Packages*` files. E.g.:
```
https://download.opensuse.org/repositories/systemsmanagement:/Uyuni:/Master:/Ubuntu1804-Uyuni-Client-Tools/xUbuntu_18.04/
```

### GPG keys management

The keys used to verify the channel metadata will be stored in a separate keyring `$CHANNEL_KEYRING` TODO: path


### Key import via the UI

Prior to verifying the signature of a repo metadata the public key used to sign that repo must be imported.

When creating a channel the user will have to specify the `GPG key URL` and the `GPG key ID` in the channel configuration page under `Software -> Manage -> Channels`.

If only the `GPG key URL` field is populated the Uyuni server will use this URL to fetch the key file and import it into `$CHANNEL_KEYRING`.

If both `GPG key URL` and one of `GPG key ID` or `GPG key Fingerprint` are present then `GPG key URL` should hold just the FQDN of a key server (without `http://` etc).

To make it clear to the user the field name should be changed to `GPG key URL / Keyserver` in the UI. Some hints should be added to the UI about the usage of these fields.

When saving the channel configuration the user should be asked to confirm the import of a GPG key.

The key import should be done when saving the channel configuration. If a key with the given `GPG key ID` or `GPG key Fingerprint` is present in `$CHANNEL_KEYRING` then no confirmation or import are needed.

### Key import via the API

API already supports GPG URL, key ID and key Fingerprint. Backend changes are needed to import the the key on create or update.

### Metadata signature lookup

In order to verify integrity of the `Packages.gz` file, first the `Release` file must be looked up and verified. This file can be in one of these locations:
- `http://mirror.example.com/$ARCHIVE_ROOT/dists/$DIST` in case of repos with a `dists` directory when the Uyuni repo URL points to `http://mirror.example.com/$ARCHIVE_ROOT/dists/$DIST/$COMPONENT/binary-$ARCH/`.
- `http://mirror.example.com/$REPODIR/` in the case of flat repositories


### Signature verification

If the `InRelease` or `Release.pgg` exist in the repo then Uyuni must verify the `Release` file:
```
gpgv --keyring /path/to/keyring.gpg InRelease
```
or
```
gpgv --keyring /path/to/keyring.gpg Release.gpg Release
```

This should be done during repo syncing.


# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?

  * obscure corner cases
  * will it impact performance?
  * what other parts of the product will be affected?
  * will the solution be hard to maintain in the future?

# Alternatives
[alternatives]: #alternatives

- What other designs/options have been considered?
- What is the impact of not doing this?

# Unresolved questions
[unresolved]: #unresolved-questions

- What are the unknowns?
- What can happen if Murphy's law holds true?
