- Feature Name: Lazy repository synchronization
- Start Date: (2026-07-14)

# Summary
[summary]: #summary

The objective of this proposal is to enable synchronization of repository metadata alone while maintaining the same database integrity we have today. This requires the system to process and store package details and errata information directly from the metadata.

To achieve our goals, we will implement several components designed to provide flexibility regarding when and how packages are retrieved.
Our primary strategy involves transitioning to metadata-only downloads and upgrading the download endpoint to support on-demand package retrieval for items not yet in the cache. To mitigate potential performance risks associated with this approach, we will also incorporate pre-download mechanisms to ensure critical packages are available upfront.

# Motivation
[motivation]: #motivation

The existing repository synchronization mechanism simultaneously downloads metadata and all associated packages. These processes are currently coupled, meaning that we need to downlaod all packages to be able to have a funcional uyuni channel.

This concurrent download approach forces the retrieval of an entire repository, which presents several significant challenges:

- Excessive disk space consumption due to downloading packages that may never be utilized.
- Substantial delays in usability, as channels (including those in CLM) remain unavailable until the initial synchronization completes.
- Lack of a priority system, which prevents the early download of essential bootstrap packages and slows down the minion onboarding process.


# Detailed design
[design]: #detailed-design


This section provides a simplified summary of the proposed architecture, with further technical details provided in the subsequent sections.

The core functionality of the new repo-sync process is to download repository metadata exclusively, assigning download flags to individual packages based on the active strategy. A dedicated Taskomatic downloader task then manages the retrieval of any packages flagged for pre-download. Additionally, the system will feature enhanced mechanisms to mandate pre-downloads and an upgraded download endpoint capable of performing on-demand package retrieval if a requested item is missing from the cache.

The implementation of this solution relies on four primary components:
- Metadata repo-sync
- Asynchronous package downloader
- Pre-download enhancements
- On-demand download endpoint

## Meta-data repo-sync

The redesigned repo-sync process will focus exclusively on retrieving channel metadata and persisting it within the database, bypassing package downloads entirely at this stage.
To ensure system readiness, all necessary information for Uyuni channel repository data generation must be populated, followed by a uyuni repo metadata refresh. This metadata-first approach enables immediate functionality for Content Lifecycle Management (CLM) and allows channels to be assigned to minions without delay.

The specific logic for storing metadata is already established within the project, and existing Python code should facilitate much of this implementation.

Following the metadata sync, a secondary step in this process will determine download priorities and schedule package retrieval based on a globally configurable download policy. Rather than immediate downloading, the primary objective is to flag packages in the database for future retrieval: identifying those that should be acquired proactively versus those with standard priority versus those that should not be pre-download.

For instance, critical assets such as bootstrap process packages will be flagged for high-priority download. Additionally, we should store the relative download paths for each package during the initial metadata retrieval phase.

| Strategy Name | Description |
| --- | --- |
| all | The system will flag all packages in the channel for pre-downloaded, replicating the current MLM behavior. To ensure efficiency, higher priority must be assigned to the specific packages required for bootstrap repository generation. |
| bootstrap | Flags only the specific packages required to generate the bootstrap repository. |
| latest | Configure the system to flag only the most recent version of each package. Within this process, packages essential for the creation of the bootstrap repository will be assigned a higher priority. |


**Database changes will include new columns on `rhnpackage` table:**

- downloadStatus (Enun): (N)o Download, (P)ending download, (E)rror, (R)eady
- downloadPriority(int): between 0-9. The higher the number, the higher the priority.
- downloadRelativePath:(varchar): relative path from where to download the package in the repository download location (remote server will be determined at download time, base on the rhncontentsource table).
- Retry download error count (int): Number of download failed attempts


### Implementation Approach

The code in the `repo-syn` is complex and filled with bug fixes that occasionally conflict with one another.However, it remains a crucial component of Uyuni and is relatively stable, given that it is likely our most used tool.

To implement the changes proposed in this RFC, we have two options:

1. Modify the current repo-sync implementation
2. Develop a new repo-sync-ng, designed according to the specifications in this RFC


Both approaches carry distinct trade-offs:

- Option 1 (Modify existing code): This would be significantly faster to implement, but we would retain all existing technical debt and maintenance challenges.
- Option 2 (Develop repo-sync-ng): This allows us to refactor the codebase for better long-term maintainability. However, rewriting the tool risks introducing new bugs or missing subtle edge cases addressed in the legacy code.

Given that repo-sync is a critical tool, a balanced approach would be to build the new implementation alongside the existing one. Initially, only new customers who want to leverage the lazy-repo-sync feature would use repo-sync-ng.

Once the new tool proves stable in production, we can migrate all remaining users to it and safely deprecate the legacy version.


## Package asynchronous downloader

A new Taskomatic task will be implemented to process packages awaiting download. This task will iterate through pending entries, prioritized by importance, download them, and store them within the existing local cache.

This task can be configure to run each few minutes, or run once per day. If the decision goes on run once per day, then some action would need to trigger extra execution, like a CLM promotion with auto-download enable (more on this later in this RFC).

The operational workflow is defined as follows:

- Identify all packages with a (P)ending status, sorted by their assigned priority.
- Secure a lock on the primary package. If its status remains pending after aquiring the download the process will continue; if it is already being processed, proceed to the subsequent package
- Execute the package download.
- Upon successful completion, transition the package status to (R)eady.
- In the event of a failure, if the number of retrieslower then the configure max retries on the system keep the package at the state (P)ending download. If the max number of retries was reached, move the package status to (E)rror.

### Download package workflow

Packages may be associated with multiple channels/repositories; however, duplicates are handled during the repository synchronization phase.

To identify the correct download source URL, the system must locate all channels/repositories associated with an rhncontensource definition (table were channel download data is stored).

The following SQL query can be used to retrieve these sources:

```sql
SELECT s.*
FROM rhnchannelpackage cp
INNER JOIN rhnchannel c ON cp.channel_id = c.id
INNER JOIN rhnchannelcontentsource cs ON c.id = cs.channel_id
INNER JOIN rhncontentsource s ON cs.source_id = s.id
WHERE cp.package_id = <PACKAGE_ID>;
```

Because this query may return multiple source URLs, some of which may include token-based authentication, an ordering rule must be established (to be defined later).

The system will then calculate the full package URL by combining the repository URL with the previously stored package relative path. Additionally, the download process must honor any proxy configurations defined on the Uyuni server.

The workflow for downloading will be:

1. Save the file to a temporary location during the download.
2. Verify the package checksum against the database record once the download is complete.
3. Move the verified package to its permanent location in the cache directory.
4. Update the database with the file path and the current download status.

## Pre-download Enhancements

For large-scale deployments, relying exclusively on on-demand downloads may be impractical. In these scenarios, it is essential to ensure that packages are pre-downloaded and cached before they are needed.
To provide users with greater control over package caching, the following enhancements are proposed:

**Manual Download Selection**

The package details interface will include a button to request an upstream download if the package is not currently in the cache. Clicking this button flags the package for retrieval, allowing the Taskomatic task to process the download. This functionality will also be accessible via the API.

**CLM Integration**

Each Content Lifecycle Management (CLM) project will feature an option to specify whether packages on each it's environments must be pre-downloaded. When enabled, all packages in the project environment's channels will be flagged for download during the build/promote phases. Taskomatic will then manage the subsequent retrieval of these flagged packages.


## On-Demand Download Endpoint

The system requires a mechanism to retrieve packages from upstream sources when they are absent from the local cache. The implementation of this workflow must adhere to the following functional requirements:

- **Single Retrieval Management:** To ensure efficiency, only a single upstream download session for the same package should be initiated even if multiple concurrent requests are received for the same missing package.
- **Concurrency and Resource Regulation:** The total number of simultaneous upstream downloads must be throttled to prevent server resource exhaustion or starvation.
- **Cache Integration:** All successfully retrieved packages must be committed to the local cache. Specific data retention policies for these cached items will be established in subsequent design phases.

All waiting location should be controlled with some limites, to control server starvations. For example:

- Max concurrent downloads
- Max number of waiting clients
- Max clients waiting on the same package
- Max waiting connections per client

### Proposed Operational Workflow

When a package download request is received, the system will execute the following steps:

1. **Cache Verification:** The system first checks the local cache. If the package is present, it is served immediately via the existing implementation.
2. **Upstream Retrieval:** If the package is missing, a download from the upstream source is triggered.
   1. Initialize multi-thread synchronization to block redundant download attempts for the same package.
   2. Utilize the standard download module (consistent with Taskomatic tasks) to fetch the package.
3. **Distribution:** Once the package is persisted to the local cache, it is distributed to all waiting threads through the standard cache delivery mechanism.


[**PoC for the parallel download control**](https://github.com/rjmateus/lazydownsuma)


### Performance and Scalability Considerations


Failure to utilize pre-downloading in large-scale environments introduces significant risks. If numerous systems attempt parallel updates via zypper and experience cache misses simultaneously, the server may reach its thread limit. In such cases, threads remain parked while waiting for package retrieval, potentially leading to total server overload.


# Drawbacks
[drawbacks]: #drawbacks

While beneficial, these changes introduce specific impacts and problems:
- Risk of packages being unavailable when requested by a minion.
- Potential for server starvation caused by concurrent requests for non-cached packages.

# Alternatives
[alternatives]: #alternatives

- Keep the existing implementation
- Follow up with the another proposal of [minion download](https://github.com/uyuni-project/uyuni/pull/12181)
    - That proposal have several problems, that the fix is incorporated in this document

# Unresolved questions
[unresolved]: #unresolved-questions


