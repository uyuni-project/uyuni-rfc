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
To ensure system readiness, all necessary information for Uyuni channel repository data generation must be populated, followed by a data refresh. This metadata-first approach enables immediate functionality for Content Lifecycle Management (CLM) and allows channels to be assigned to minions without delay.

The specific logic for storing metadata is already established within the project, and existing Python code should facilitate much of this implementation.

Following the metadata sync, a secondary process will determine download priorities and schedule package retrieval based on a globally configurable download policy. Rather than immediate downloading, the primary objective is to flag packages in the database for future retrieval—identifying those that should be acquired proactively versus those with standard priority.

For instance, critical assets such as bootstrap process packages will be flagged for high-priority download. Additionally, we should store the relative download paths for each package during the initial metadata retrieval phase.

| Strategy Name | Description |
| --- | --- |
| all | The system will flag all packages in the channel for retrieval, replicating the current MLM behavior. To ensure efficiency, high priority will be assigned to the specific packages required for bootstrap repository generation. |
| bootstrap | Flags only the specific packages required to generate the bootstrap repository. |
| latest | Configure the system to flag only the most recent version of each package. Within this process, packages essential for the creation of the bootstrap repository will be assigned a higher priority. |


**Database changes will include new columns on `rhnpackage` table:**

- downloadStatus (Enun): (N)o Download, (P)ending download, (D)ownloading, (R)eady
- downloadPriority(int): between 0-9. The higher the number, the higher the priority.
- downloadRelativePath:(varchar): relative path from where to download the package.
- Retry download error count (int): Number of download failed attempts

## Package asynchronous downloader

A new Taskomatic task will be implemented to process packages awaiting download. This task will iterate through pending entries, prioritized by importance, download them, and store them within the local cache.

The operational workflow is defined as follows:

- Identify all packages with a (P)ending status, sorted by their assigned priority.
- Secure a lock on the primary package. If its status remains pending, transition it to (D)ownloading; if it is already being processed, proceed to the subsequent package. Note: This state may be redundant if cross-service downloads are managed via database locks.
- Execute the package download.
- Upon successful completion, transition the package status to (R)eady.
- In the event of a failure, revert the status to (P)ending. To prevent infinite loops during persistent download failures, a maximum attempt threshold must be implemented to eventually mark the package as failed.

As a preparatory measure during the Taskomatic job startup, any packages stuck in the (D)ownloading state will be reset to (P)ending. This ensures that packages left in limbo due to an unexpected service termination can be retried. This step is contingent on the utilization of the download status field.

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
WHERE cp.package_id = 1;
```

Because this query may return multiple source URLs—some of which may include token-based authentication—an ordering rule must be established (to be defined later).

The system will then calculate the full package URL by combining the repository URL with the previously stored relative path. Additionally, the download process must honor any proxy configurations defined on the Uyuni server.

The workflow for downloading is as follows:
Save the file to a temporary location during the download.
Verify the package checksum against the database record once the download is complete.
Move the verified package to its permanent location in the cache directory.
Update the database with the file path and the current download status.

## Pre-download Enhancements

For large-scale deployments, relying exclusively on on-demand downloads may be impractical. In these scenarios, it is essential to ensure that packages are pre-downloaded and cached before they are needed.
To provide users with greater control over package caching, the following enhancements are proposed:

**Manual Download Selection**

The package details interface will include a button to request an upstream download if the package is not currently in the cache. Clicking this button flags the package for retrieval, allowing the Taskomatic task to process the download. This functionality will also be accessible via the API.

**CLM Integration**

Each environment within a Content Lifecycle Management (CLM) project will feature an option to specify whether its associated packages should be pre-downloaded. When enabled, all packages in the environment's channels will be flagged for download during the build/promote phases. Taskomatic will then manage the subsequent retrieval of these flagged packages.


## On-Demand Download Endpoint

The system requires a mechanism to retrieve packages from upstream sources when they are absent from the local cache. The implementation of this workflow must adhere to the following functional requirements:

- **Single Retrieval Management:** To ensure efficiency, only a single upstream download session should be initiated even if multiple concurrent requests are received for the same missing package.
- **Concurrency and Resource Regulation:** The total number of simultaneous upstream downloads must be throttled to prevent server resource exhaustion or starvation.
- **Cache Integration:** All successfully retrieved packages must be committed to the local cache. Specific data retention policies for these cached items will be established in subsequent design phases.

### Proposed Operational Workflow

When a package download request is received, the system will execute the following steps:

1. **Cache Verification:** The system first checks the local cache. If the package is present, it is served immediately via the existing implementation.
2. **Upstream Retrieval:** If the package is missing, a download from the upstream source is triggered.
   1. Initialize multi-thread synchronization to block redundant download attempts for the same asset.
   2. Utilize the standard download module (consistent with Taskomatic tasks) to fetch the package.
3. **Distribution:** Once the package is persisted to the local cache, it is distributed to all waiting threads through the standard cache delivery mechanism.


### Performance and Scalability Considerations


Failure to utilize pre-downloading in large-scale environments introduces significant risks. If numerous systems attempt parallel updates via zypper and experience cache misses simultaneously, the server may reach its thread limit. In such cases, threads remain parked while waiting for package retrieval, potentially leading to total server overload.

[**PoC for the parallel download control**](https://github.com/rjmateus/lazydownsuma)


# Drawbacks
[drawbacks]: #drawbacks

While beneficial, these changes introduce specific impacts and problems:
- Risk of packages being unavailable when requested by a minion.
- Potential for server starvation caused by concurrent requests for non-cached packages.

# Alternatives
[alternatives]: #alternatives

- Keep the existing implementation
- Follow up with the another proposal of minion download
    - That proposal have several problems, that the fix is incorporated in this document

# Unresolved questions
[unresolved]: #unresolved-questions


