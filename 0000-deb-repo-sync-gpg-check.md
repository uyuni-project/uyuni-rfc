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

## Current implementation

Currently Uyuni uses its own keyring from `/var/lib/spacewalk/gpgdir/pubring.gpg` to verify RPM repo metadata.

By default it contains various keys for verifying SLES and OpenSUSE repos. The content of this keyring is shipped in the `uyuni-build-keys` package.

In case of third-party RPM repos there is a standard location for the GPG keys used to verify the metadata. Because of this `spacewalk-repo-sync` can import those keys when syncing the repo (the user is prompted to accept the keys).

## Use cases

1. Verify metadata from "official" distro repos.
2. Verify third-party repos.

## GPG verification implementation

In case of Debian repos there is no standard location for the GPG keys. The user has to import it manually using `apt-key`.

Uyuni will provide keys for "official" repos using packages and will allow the user to upload keys for thid-party repos.

### Official repos

In case of official repos, Uyuni should ship the GPG keys for Ubuntu and Debian in packages similar to `uyuni-build-keys`:
- `debian-build-keys`
- `ubuntu-build-keys`

When installing the packages the keys will be added to the Uyuni keyring automatically.

These packages will expose the short ID of the keys they contain using RPM `Provides`. This is needed to allow querying by Uyuni (see later).

### Third party repos

For third-party repos the user will have the option to upload GPG keys via the current UI `Software -> Manage -> Repositories`.

The uploaded key will be added to the Uyuni keyring `/var/lib/spacewalk/gpgdir/pubring.gpg` by the Taskomatic job.

### Keys management

The GPG keys will be stored in the database in the existing table `rhnCryptoKey`.

The keyring `/var/lib/spacewalk/gpgdir/pubring.gpg` and the DB will be kept in sync automatically by a Taskomatic job (`gpg-key-sync`).

The Taskomatic job  will be triggered periodically.

Sync algorithm:
```
for each $key in db:
   if ($key not exists in keyring):
      import $key into keyring

   if ($key exists in keyring) and ($key.use_for_signing == false) and not (pkg installed with Provides == short_id($key):
       delete from keyring

for each $key in keyring:
    if ($key not exists in db):
      if pkg installed with Provides == short_id($key):
        import $key into db
      else:
        delete from keyring

```

### UI changes

In the current UI `Software -> Manage -> Repositories` a new checkbox will be added `Use to verify repo metadata`.

Updating or deleting GPG keys shipped by packages (`uyuni-build-keys`, etc) will not be allowed. Only GPG keys uploaded by the user can be updated or deleted.

### API

TODO

### Metadata and signature lookup

In order to verify integrity of the `Packages.gz` file Uyuni must first lookup the `Release` file and verify its signature (see the `Support for additional fields in the metadata of Deb repos ` RFC for the location of the `Release` file).

The signature must be looked up together with the `Release` file. If the `Has signed metadata` flag is not disabled then an error must be thrown in case the `InRelease` or `Release.gpg` file can't be found in the repo.


### Signature verification

The GPG verification must be done always. The user should have the option to disable it by unchecking the `Has signed metadata` checkbox in the repository UI.

If the `InRelease` or `Release.pgg` exist in the repo to be synced then Uyuni must verify the `Release` file:
```
gpgv --keyring /var/lib/spacewalk/gpgdir/pubring.gpg InRelease
```
or
```
gpgv --keyring /var/lib/spacewalk/gpgdir/pubring.gpg Release.gpg Release
```

<<<<<<< HEAD
The signature verification must be done in `spacewalk-repo-sync` during repo syncing when the metadata is parsed.
=======
Otherwise the custom GPG key associated with the repo must be used:
```
gpgv --keyring </path/to/temp/keyring/file.gpg> InRelease
```
or
```
gpgv --keyring </path/to/temp/keyring/file.gpg> Release.gpg Release
```

The signature verification should be done during repo syncing when the metadata is parsed.
If the user has turned off GPG signature verification, a warning should be printed into the logs.
>>>>>>> 9d45ec18bf150a85cd046624a10d15f02c90926d


# Drawbacks
[drawbacks]: #drawbacks

No drawbacks.

# Alternatives
[alternatives]: #alternatives


# Unresolved questions
[unresolved]: #unresolved-questions

# References

1. [Debian repository format](https://wiki.debian.org/DebianRepository/Format)
