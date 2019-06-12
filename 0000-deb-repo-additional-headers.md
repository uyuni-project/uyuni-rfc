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
