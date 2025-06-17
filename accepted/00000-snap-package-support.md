- Feature Name: support snap in ubuntu 22.04
- Start Date: 6/01/2025

# Summary
[summary]: #summary

Introduce Snap support in Uyuni, allowing users to:

Install, update, and remove Snap packages.

Manage Snap channels (stable, candidate, beta, edge).

Handle Snap package management in airgapped environments.

# Motivation
[motivation]: #motivation

Since Ubuntu 22.04 LTS, the Snap package technology has gained significant traction, and with the Ubuntu 24.04 LTS release, many deb packages are being migrated to Snap.

With this increasing adoption of Snap packages in Ubuntu, Uyuni lacks native support for managing Snap-based applications. This creates a gap in package management, especially as more software is distributed via Snap.


# Detailed design
[design]: #detailed-design

1 Data Analsis 

Total unique packages: 6564 (6/11/2025)
Total stable packages: 6564
Architecture count in stable packages:
  - amd64: 6463
  - armhf: 45
  - arm64: 58
  - all: 101
  - i386: 67
  - ppc64el: 10
  - s390x: 10

Total unique packages checked: 13746
- Total in 'beta': 1677
- Total in 'candidate': 1782
- Total in 'edge': 3740

Total size: 493 GB  around 500GB
Average package size: 76.82 MB

At this stage, we may be able to store the beta and candidate Snap packages in the cache.
However, since .snap binary packages are typically two to three times larger than .deb packages, it may be more efficient to use a pre-selection strategy for the stable channel.

Proposed approach:

1. Load the full list of available packages.

2. Allow the client to select which packages they want to manage.

3. Download only the selected packages to the repository cache. (by this way support part of airgap environment)

2 Snap Repository Synchronization Workflow

```text
┌────────────────────────────────────────────┐
│          spacewalk-repo-sync CLI           │
│  $ spacewalk-repo-sync --channel=          │
│    ubuntu_22.04_snap_stable --type=snap    │
└────────────┬───────────────────────────────┘
             │
             │ Note: Snap packages do not have a public URL,
             │       so no URL is required in CLI.
             ▼
┌────────────────────────────────────────────┐
│            reposync.py (main logic)        │
│ - Selects plugin by repo_type              │
└────────────┬───────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────┐
│          snap_src.py (Snap plugin)         │
│ - Creates ContentSource                    │
│ - Wraps SnapRepo                           │
└────────────┬───────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│        SnapRepo.get_all_package_list()                     │
│  - Calls: https://api.snapcraft.io/api/v1/snaps/search?q={query}&limit={limit}    │
│  - Creates SnapPackage objects (name, path, etc.)          │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│        SnapRepo.get_select_package_list()                  │
│  - Filters selected packages                               │
│  - Creates SnapPackage objects (name, path, etc.)          │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│            SnapRepo._download(url)                         │
│  - Performs HTTP download of selected .snap file           │
│  - GET https://api.snapcraft.io/v2/snaps/info/<snap_name> │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│      reposync.py → import_packages()                       │
│  - Imports metadata into the database                      │
│  - Saves .snap files under /var/spacewalk/packages/        │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│   Minions can now use Uyuni as a Snap repository           │
│   (served through Uyuni-hosted channels)                   │
│   e.g. `sudo snap install <pkg>` from Uyuni server         │
└────────────────────────────────────────────────────────────┘
```

Fake URL Design for Snap Repositories

Snap packages are distributed via the Snap Store using dynamic APIs rather than static URLs. To maintain consistency with other repository types (e.g., YUM, DEB),  introduce a Fake URL format to represent Snap sources uniformly in the database.

Fake URL Format:
```
snap://<repo label>/<stable/edge/candidate/beta>
```


These URLs are not used for actual downloads. Instead, they serve as unique identifiers stored in the rhnContentSource.source_url field. The real package fetching will be handled through the Snap API.

This approach keeps the database structure consistent, simplifies repository logic, and supports multiple Snap channels (managed through the rhnSnapChannel table).

When a client creates a Snap repository through the UI, they do not need to enter a URL—only the channel (stable, edge, candidate, or beta) and a repository label are required. The API will automatically generate a fake URL internally.

However, when creating a Snap repository using spacemd, the user may manually specify a fake URL, for example:
```
repo_create --name="Snap Store Repo" --url="https://fake.url" --type=snap
```


3 DB DESIGN

rhnChannel stores basic channel information, such as label, org_id
rhnContentSource stores the actual repo URL
rhnChannelContentSource channel and content source mapping table (channel ↔ repo)

Uyuni’s current database schema (rhnContentSource, rhnContentSourceType, rhnChannel) is designed for repositories like YUM or DEB, which use a static URL and do not have multi-channel semantics.

However, Snap packages are distributed via multiple dynamic channels (e.g., stable, beta, candidate, edge) under a track (e.g., latest). The existing schema does not provide a way to associate a Snap repository with multiple channels, nor a place to store their metadata.
``` text
CREATE TABLE rhnSnapChannel (
    id SERIAL PRIMARY KEY,
    content_source_id INTEGER REFERENCES rhnContentSource(id) ON DELETE CASCADE,
    channel VARCHAR(64) NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT now(),
    modified TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Insert 'snap' repo type
insert into rhnContentSourceType (id, label) values
(sequence_nextval('rhn_content_source_type_id_seq'), 'snap');

-- Register supported channels for the repo
INSERT INTO rhnSnapChannel (content_source_id, channel) VALUES
(600, 'stable'),
(600,  'beta'),
(600, 'candidate'),
(600,  'edge');
```



4 UI design 

To be continue

