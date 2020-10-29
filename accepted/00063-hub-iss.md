- Feature Name: hub_iss
- Start Date: 2019-10-17
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

Uyuni Server has a functionality called Inter-Server Synchronization (abbreviated to ISS from now on) that allows users to transfer channel data (packages and repo/product metadata) from one Server (called an ISS Master) to another Server (called an ISS Slave).

Current implementation [is documented in Uyuni manuals](https://www.uyuni-project.org/uyuni-docs/uyuni/administration/iss.html).

With the Hub architecture, there will be multiple Servers that receive content managed in the Hub, hence ISS will be a required mechanism.

This RFC describes an overhaul of the ISS implementation in order to cover more use cases (in particular, synchronization of content different than channel data) and with better performance to attain higher scalability.

See the [Hub general RFC](00060-hub-general.md) for an introduction to the Hub project.

# Motivation
[motivation]: #motivation

ISS is currently limited to software channels, and it is not sure whether it can scale up above tens of Servers.

From the requirements:

> * Managed content can be selectively synced from Hub to Servers
>   * In order of importance:
>    - Packaged software
>    - Configuration Management data (states, pillars...)
>    - OS Images
>    - Container Images
>   * Synchronization has to be atomic
>   * Synchronization has to be doable via a storage media instead of a network for certain network-constrained environments (defense, China)
>   * Nice-to-have: avoid the download of content from the Hub if it is faster to retrieve it from SCC
>   * Nice-to-have: on-demand downloading from the Hub should be considered (Proxy/Squid model)
> [...]
> * Performance: support high number of clients and Servers
> [...]
>  * maximum expected number of Servers: 9k

# Detailed design
[design]: #detailed-design

## Overall problem statement

Any kind of managed content on a Uyuni Server can be thought as:
  1- a set of database records describing that content and, optionally,
  2- a set of files on a filesystem referred to by those records

One way to look to look at this problem is to provide a way of:
  - exporting (from a Server),
  - transferring, and
  - importing (into another Server)

The two pieces of information above.

**Core idea**: the whole mechanism will be reimplemented from scratch via an "exporter" program which dumps relevant data from the originating Server and an "importer" program that consumes that dump on the receiving Server. Dump will be saved to the filesystem.

### File export/import

A "file exporter" component runs on a Server and given a specified piece of content to sync (eg. a software channel label), will access the database to identify the set of relevant files and save them in an appropriate directory structure.

A "file importer" component runs on the target Server and, given an exported directory structure, copies files in appropriate locations.

Transfer of the directory structure is described separately in the "Transport" section below.

### Database data import/export

**First core idea**: a "database exporter" component runs on a Server and dumps data in form of a special SQL script. On the target Server, data is then imported by executing the SQL script against the local database.

Dumped data will have to be limited to a specified piece of content to sync (eg. a software channel label, or a set of such labels).

**Second core idea**: the generated SQL script will be generated without substantial hardcoding of database schema information int the program. Rather, the exporter will inspecting the schema programmatically and, for example, determine most or all of the involved tables, key relationships, ordering, etc.

Notes:
  - the current implementation serializes ISS Master database data to XML and deserializes it on the ISS Slave. Relatively complicated logic is in place on both communication ends to convert to and from this format
    - intention of the approach in this RFC is to avoid most of this complication
  - the current implementation also needs an up-to-date mapping of tables and columns in Python code (ORM), and that has to be kept updated
    - intention of the approach in this RFC is to avoid most of the manual specification of the mapping, reducing maintenance

A proof-of-concept Python script that implements partially those ideas is available at: https://github.com/moio/mgr-dump

#### First core idea: export as SQL script

The exported SQL script will have to be idempotent. For example:

```sql
INSERT INTO "rhnchecksumtype" (
    "id",
    "label",
    "description"
)
VALUES
    (1, 'md5', 'MD5sum'),
    (2, 'sha1', 'SHA1sum'),
    (3, 'sha256', 'SHA256sum'),
    (4, 'sha384', 'SHA384sum'),
    (5, 'sha512', 'SHA512sum')
ON CONFLICT ("label") DO UPDATE
    SET "description" = excluded."description";
```

The `ON CONFLICT DO UPDATE` clause is called an "upsert" effectively turning the `INSERT` into an `UPDATE` if a row with a conflict on the specified column (`label` in this case) is found.

Note that additional mechanisms are needed to add correct values in the `id` column, if they come from a sequence. For example:

```sql
INSERT INTO "web_customer" (
    "id",
    "name",
    "modified"
)
VALUES
    (nextval('web_customer_id_seq'), 'SUS', '2019-10-17T10:09:11.750508+02:00'::timestamptz)
ON CONFLICT ("name") DO UPDATE
    SET "modified" = excluded."modified";
```

For tables with foreign keys, `SELECT` statements on parent tables will have to be used to link rows correctly, for example:

```sql
INSERT INTO "rhnchannelarch" (
    "id",
    "label",
    "arch_type_id",
    "name"
)
VALUES
    (500, 'channel-ia32', (SELECT id FROM rhnarchtype WHERE label =  'rpm'), 'IA-32' - ),
    (501, 'channel-ia32-deb', (SELECT id FROM rhnarchtype WHERE label =  'deb'), 'IA-32 Debian' - )
ON CONFLICT ...
```

At this point it is believed/assumed that:
  - ISS is by and large an additive process, so cleanups should not be needed for most tables. For those where it is necessary (eg. linking tables in an m:n relationship), `DELETE` statements either before or after `INSERT`s suffice
  - most tables can be treated in substantially the same way, not much table-specific logic has to be implemented (in case it is, it is believed a solution can be found via pl/SQL)

#### Second core idea: SQL script is generated via introspection

The SQL script would be produced by a program that looks at the database schema and, given a small set of starting tables (eg. `rhnchannel`) and starting rows given by a criterion (eg. `channel_id = 103` or `modified_date > '2019-01-01'`), figures out:

- the graph of dependent/dependency tables (from the starting set)
- for each table:
  - all columns
  - the primary key (if any), and columns involved
  - the sequences feeding the primary key if numeric (heuristics with exceptions, or database schema naming rules, might be needed)
  - the foreign keys (if any), and the columns involved
  - the rows directly or indirectly connected to the starting row id

With the above information, it should be possible to write the SQL script in a completely or almost-completely automated way, in particular:
  - determining the right order of `INSERT` and `DELETE` statements given table dependencies
  - determining which column values have to be `SELECT`ed, because they are foreign keys, and which are constant
  - determining the conflict column set for `ON CONFLICT` clauses
  - the actual row data to insert

Expected benefits:
  - the ISS programs need (potentially) no updating when the database structure changes
  - supporting a new managed content type is as easy as specifying a new set of starting tables

### Transport

Both file and database data need to be transferred somehow to the receiving Server.

Current ISS implementation offers:
  - storage-based transfer (a directory with well-defined structure is created to host files and data in XML form) and
  - API-based transfer: an XMLRPC request is made from ISS Slave to Server, and the same data set is sent over XMLRPC (http), streamed

The initial, most basic version of the new ISS will not implement a transport at all, relying on the user to deliver data to the receiving Server.

Later versions might wrap the import process in a Salt module, delegating the transport to Salt itself (possibly via `https`, `rsync` or other protocols subject to performance needs). It is in principle possible to copy files directly to desired destinations, avoiding a temporary directory to be transfered at all.

There is no plan for API-based transfer, although that could be implemented later.

### Triggering

Current ISS implementation is ISS-Slave-triggered - the `mgr-inter-sync` command will trigger syncing (by default via the API-based transport).

The new ISS implementation will be triggered from the exporting side, possibly via Salt states. The exact mechanism is left as an implementation detail.

For software channel synchronization, either the SQL script or the "importer" will have to trigger errata cache refresh and repository metadata regeneration.

### Limitations

The first implementation of this RFC will:
  - be limited to software channels, including product metadata
  - be limited to storage-based transfers

## Implementation details

- two commandline tools will be added, "exporter" and "importer"
  - output of the "exportter" will be a directory with files and a SQL script
  - the "importer" program will mainly copy files to correct locations and execute the SQL script
  - triggering of the "importer" tool might happen via Salt, this is left as an implementation detail
- all new code will be in Go
- inspection of the schema can be implemented via `SELECT` queries on Postgres's internal schema tables
  - current and new implementations would thus be completely independent, so could coexist for an initial period of time, as the new implementation matures

## Impact on existing components and users
All code would be new in a new component, so no change to existing components is expected. No impact on existing users is expected at all until the old implementation is dropped.

When that happens, there is a chance of regressions for ISS users, which represent a small minority of total users.

# Drawbacks
[drawbacks]: #drawbacks

Syncing content between different versions of Uyuni may not work, if the database schema changes in non-compatible ways.

This risk is fundamentally unavoidable at a conceptual level, although different mitigations can be put in place and the current implementation actually allows for a broader set of mitigations than the proposal in this RFC can allow.

In particular:

1. Some changes in the database structure could be "internal only", not really changing the nature of the information that's being exchanged. In those cases, the current implementation could make use of the fact the the XML representation does not change, thus the ISS Slave continues to operate normally
2. Other changes would be reflected in the XML structure, but still not create problems because, for example, the current implementation ignores unknown tags. This is the case for completely new elements that the ISS Slave would just not import (which is most likely conceptually correct, as tables would also be missing)
3. Finally, yet other changes could really introduce a backwards compatibility problem and, since the protocol is versioned, [the import program will send an alert and abort](https://github.com/SUSE/spacewalk/blob/Manager-3.2/backend/satellite_tools/xmlSource.py#L271-L298).

With the proposal in this RFC, it is possible to implement protection from case 3. via a similar versioning mechanism, partially against 2. ignoring missing tables but only offer limited resilience against case 1., as we would not have a real database-agnostic representation of data.

pl/SQL could still be used, as a last resort, to apply different commands to different ISS Slave versions, but that would be hardly maintainable, so it would only be suggested to handle critical situations temporarily.

General recommendation would be to upgrade an ISS Master, then upgrade ISS Slaves before attempting any new Inter-Server Synchronization. Another RFC will detail how Hub could make such upgrades easier.


# Alternatives
[alternatives]: #alternatives

- re-use of the current ISS implementation, extending it to cover other content types
  - con: current implementation proved difficult to maintain. Complicating factors are:
    - data is exchanged in XML form which needs explicit marshaling and unmarshaling from the database (types and structure)
    - marshaling implementation [requires extensive mapping onto the schema](https://github.com/uyuni-project/uyuni/blob/1638692858c3d0a9c8342524c34307842d57136d/backend/server/importlib/backendOracle.py#L32-L651) to be manually kept in sync
    - supports two backends (Postgres and Oracle), but the second has been dropped
    - format is versioned and code is meant to cope with version differences
    - format contains some data summaries for performance reasons (eg. packages and packages_short)
    - XML files are compressed, as they tend to get large
    - access to the database uses the traditional Python stack, which comprises a Python NIH ORM
  - con: storage-based transfer was shipped broken for a long time (SUSE Manager 3.2). Probably nobody used it, test would be required to determine if it works at all
  - pro: does not require reimplementation from scratch

- use a neutral format (JSON, XML...) instead of SQL
  - pro: potentially more robust when ISS Master and ISS Slave are not on the same version
  - con: more complex to implement and maintain

- use an existing content management project: Pulp or Artifactory
  - pro: lots of extra functionality
  - con: much more complex
    - the current ISS implementation is roughly 10K LOC (excluding dependencies)
    - the proposed ISS implementation is expected to be much simpler, could be 2K-5K LOC
    - Pulp is around 152K LOC (~30x bigger best case)
    - Artifactory is around 523K LOC (~100x bigger best case)

# Next steps
[Next steps]: #next-steps

- support more types of content: configuration management data, OS images, container images
- support an API-based transport, if needed
- drop the current ISS implementation
  - full backwards compatibility of all commandline flags is left as an implementation detail, it's probably achievable
  - dropping the old ISS implementation could save about ~9k LOC, as measured by `cloc backend/server/importlib/*Import* backend/satellite_exporter/ backend/satellite_tools/exporter/ backend/satellite_tools/*sat*ync*`
- support syncing repo metadata, in order for them not to necessarily be regenerated on the ISS Slave
- allow downloading of files from locations other than the ISS Master - SCC, a closer Proxy, third-party repos...
- offer a UI for ISS in general. Current implementation does not have one
- integrate with the Content Lifecycle Management functionality: automatically sync after content is finalized

# Unresolved questions
[unresolved]: #unresolved-questions

- is it really possible to cover all cases with a SQL script? What cases would be missing?
- is it acceptable to lose compatibility between ISS Master and ISS Slaves if they are on different Uyuni versions?
