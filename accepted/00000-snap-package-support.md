- Feature Name: support snap packages in uyuni
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

## Data Analsis 

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

## Detailed Design

Proposed approach:

1. Load the full list of available packages.

2. Allow the client to select which packages they want to manage.

3. Download only the selected packages to the repository cache. 

4. Use Salt to copy the corresponding assertions and .snap files to the minions, thereby supporting partially air-gapped environments.

```

        [Scheduled Task: Cron Job]                      [User Workflow]
+----------------------------------------+       +-----------------------------+
| Every week (or on a schedule):         |       | User opens Uyuni Web UI    |
| - Call Snap search API (a to z)        |       +-----------------------------+
| - Fetch snap_id, publisher_id, etc.    |                   |
| - Store into preloaded metadata table  |                   v
+----------------------------------------+            +-----------------------------+
               |                                      | Create Snap Channel        |
               |                                      +-----------------------------+
               v                                                  |
     +--------------------------------+                           v
     |   Snap Metadata DB (preloaded) |              +-----------------------------+
     +--------------------------------+              | Create Snap Repo            |
               |                                     | - Select Snap package       |
               `----when click dropdown------------> |   from preloaded DB table   |
                                                     | - Bind repo to a channel    |
                                                     +-----------------------------+
                                                                 |
                                                                 v
                                                     +-----------------------------+
                                                     | Download Files (on demand): |
                                                     | - .snap binary              |
                                                     | - snap-revision.assert      |
                                                     | - account-key.assert        |
                                                     | - snap-declaration.assert   |
                                                     +-----------------------------+
                                                                 |
                                                                 v
                                                     +-----------------------------+
                                                     |     Repo Ready to Serve     |
                                                     +-----------------------------+
```
```
+-------------------+                                     +-------------------+
|    Salt Master    |                                     |      Minion       |
+-------------------+                                     +-------------------+
        |                                                       |
        | 1. salt cp (send *.assert, *.snap) ------------------>|
        |                                                       |
        | 2. salt cmd.run on minion:                            |
        |       snap ack /tmp/asserts/*.assert                  |
        |                                                       |
        |                                                       | 3. snap install /tmp/snaps/pkg.snap \
        |                                                       |        --offline
        |                                                       |    (or --dangerous if no assertions)
        |                                                       |
        |                                                       | 4. snap list | grep pkg   # verify
        |                                                       |
        |                                                       |

```

### Web UI and CLI Desgin 

From my observation, there are two ways to create a channel in Uyuni: via CLI and Web UI.

CLI-Based Channel Creation (e.g., for deb):
In the current workflow, using a command such as:

spacewalk-repo-sync --channel=ubuntu_22.04 --type=deb

requires a pre-existing channel and a repository bound to that channel. The repository configuration typically includes a URL from which the binary packages are downloaded onto the Uyuni server.

Web UI-Based Channel Creation:
Similarly, in the Web UI, users must:

Create a channel (with a name, label, summary, etc.)

Create and associate a repository to that channel

Click the Sync button to initiate repository synchronization.

For Snap support, i want to  follow a similar logic. However, installing a Snap package requires not just a binary file (.snap), but also three associated assertion files:

snap-revision.assert

snap-declaration.assert

account.assert + account-key.assert

In Stage 1, we focus on supporting the Stable channel from Snapcraft.

#### UI Proposal for Snap:

When creating a channel for Snap, the form structure remains similar to existing deb/yum workflows (channel name, label, summary, etc.).

For the repository creation step:

If the user selects "Repository Type = Snap", the URL input field can be hidden.

Instead, a dropdown list of available Snap packages should be provided.

The user can select one or more packages to download from Snapcraft.

#### CLI Proposal for Snap:
We propose extending spacewalk-repo-sync with support for Snap packages:

spacewalk-repo-sync --channel=snap_stable_ubuntu2204 --type=snap --add-snaps="hello-world,vlc"
In addition, we could provide a helper function to list all Snap packages Uyuni can support or has access to:

spacewalk-repo-sync --list-snaps
This will return a list of available Snap packages that can be selected during channel creation.

### Database Design (Snap Package Repository Design)
To support package discovery, we propose maintaining a pre-defined Snap repository list in the Uyuni database.

snap_repo Table Structure:

| Column Name         | Description                         |
| ------------------- | ----------------------------------- |
| `snap_id`           | Unique Snap ID                      |
| `snap_name`         | Package name (e.g., `vlc`)          |
| `publisher_id`      | Snap publisher account ID           |
| `sha3_384`          | Hex-encoded SHA3-384 of snap binary |
| `sha3_384_b64`      | Base64-URL-encoded SHA3-384         |
| `sign_key_sha3_384` | Signer's key fingerprint            |

Metadata Extraction Process
To populate the table, we use the Snap Store API via a refresh call to retrieve key metadata:

```
curl -X POST https://api.snapcraft.io/v2/snaps/refresh \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Snap-Device-Series: 16" \
  -H "Snap-Device-Architecture: amd64" \
  --data-binary @refresh.json \
  -o refresh-response.json

cat > refresh.json <<EOF
{
  "context": [],
  "actions": [
    {
      "action": "install",
      "instance-key": "install-htop",
      "name": "htop",
      "channel": "stable"
    }
  ],
  "fields": [
    "architectures",
    "base",
    "confinement",
    "links",
    "contact",
    "created-at",
    "description",
    "download",
    "epoch",
    "license",
    "name",
    "prices",
    "private",
    "publisher",
    "revision",
    "snap-id",
    "snap-yaml",
    "summary",
    "title",
    "type",
    "version",
    "website",
    "store-url",
    "media",
    "common-ids",
    "categories"
  ]
}
EOF

```
Key Fields Returned
From the refresh-response.json, the following fields are extracted:

snap-id: Used for assertion requests (e.g., snap-declaration, snap-revision)

revision: Used to fetch the Snap binary and match its hash

sha3-384: Used to verify the integrity of the .snap binary

publisher->account-id: Used to fetch the account and account-key assertions

These values form the foundation for verifying Snap packages and organizing metadata in Uyuni.


### List Packages and Synchronization (Cron Job)
A scheduled cron job should:

Call the Snapcraft API to fetch updated package metadata:

GET https://api.snapcraft.io/api/v1/snaps/search?q=a  # Repeated for a–z

```
all_packages = {}
limit = 100
keywords = list(string.ascii_lowercase)  # a-z

for keyword in keywords:
    page = 1
    same_count = 0
    while True:
        url = f"https://api.snapcraft.io/api/v1/snaps/search?q={keyword}&limit={limit}&page={page}"
        response = requests.get(url, headers=headers)
        data = response.json()
        packages = data.get("_embedded", {}).get("clickindex:package", [])

        if not packages:
            break

        prev_count = len(all_packages)

        for pkg in packages:
            name = pkg.get("package_name")
            if name not in all_packages:
                all_packages[name] = {
                    "name": name,
                    "version": pkg.get("version"),
                    "channel": pkg.get("channel"),
                    "arch": pkg.get("architecture"),
                }

        curr_count = len(all_packages)

        if curr_count == prev_count:
            same_count += 1
        else:
            same_count = 0

        if same_count >= 5:
            break

        page += 1
        time.sleep(0.3)

```
Update the snap_repo table with the latest Snap metadata.

Ensure new packages and updated revisions are stored and ready for selection in the UI/CLI.


### Download Snap Binary and Assertion Files 

In Snap, installing a package requires not only the .snap binary itself, but also a set of assertion files. These assertions are cryptographically signed metadata used by snapd to verify the authenticity, origin, and permissions of the package.

The following components must be prepared in advance. 

On the Uyuni server, the local repository should be structured as follows:
```
/srv/salt/
├── snap/                       
│   ├── init.sls
│   └── ensure_snapd.sls
│   └── ensure_snapd_core.sls
└── snaps/                      
    ├── htop/
    │   ├── htop.snap
    │   └── htop_snap-revision.assert
    │   └── htop_snap-declaration.assert
    │   └── htop_account-key.assert
    │   └── htop_account.assert
    └── kubectl/
        ├── kubectl.snap
        └── kubect_snap-revision.assert
        └── kubect_snap-declaration.assert
        └── kubect_account-key.assert
        └── kubect_account.assert

```
This repository can be populated from the Snapcraft API, with all relevant metadata also stored in the database (as prepared in the previous synchronization step).

#### Endpoints Desgin

POST https://api.snapcraft.io/v2/snaps/refresh
(Initiates the refresh or installation of the Snap package.)

GET https://api.snapcraft.io/v2/assertions/snap-revision/<revision-id>?max-format=0
(Retrieves the snap-revision assertion for the specified package revision.)

GET https://api.snapcraft.io/v2/assertions/snap-declaration/<snap-id>?max-format=6
(Retrieves the snap-declaration assertion for the snap.)

GET https://api.snapcraft.io/v2/assertions/account/<account-id>?max-format=0
(Retrieves the account assertion for the publisher.)

GET https://api.snapcraft.io/v2/assertions/account-key/<key-id>?max-format=1
(Retrieves the public key assertion for the account.)

### Salt Part
```
/srv/pillar/
├── top.sls                    
└── snaps.sls   

/srv/salt/
└── snap/
    ├── ensure_snapd.sls
    ├── ensure_bases_store.sls
    └── init.sls
```
#### Design pillar for the package list
The package list to be managed is defined in a dedicated Salt pillar. 
This pillar is automatically generated when the user selects packages through the UI/CLI.

```
/srv/pillar/top.sls

  base:
  '*':
    - snaps

/srv/pillar/snaps.sls 

snap_pkgs:
  - name: htop
    mode: local
    src_dir: salt://snaps/htop
    dst_dir: /tmp/snap-airgap/htop
    sequence:
      - {name: htop,    file: htop_*.snap}

  - name: kubectl
    mode: local
    src_dir: salt://snaps/kubectl
    dst_dir: /tmp/snap-airgap/kubectl
    sequence:
      - {name: kubectl, file: kubectl_*.snap}

```

#### Step 3: Salt State Design 
```
/srv/salt/snap/ensure_snapd.sls

  {% if grains['os_family'] in ['Ubuntu'] %}
  snapd:
    pkg.installed: []
    service.running:
      - enable: True
      - require:
        - pkg: snapd
  {% endif %}

/srv/salt/snap/ensure_bases_store.sls

{% set bases = pillar.get('snap_bases', ['core22']) %}

include:
  - snap.ensure_snapd

{% for b in bases %}
snap-base-{{ b }}-store:
  cmd.run:
    - name: "snap install {{ b }}"
    - unless: "snap list | awk '{print $1}' | grep -qx {{ b }}"
    - require:
      - service: snapd-service
{% endfor %}

/srv/salt/snap/init.sls

  {% set pkgs = pillar.get('snap_pkgs', []) %}

include:
  - snap.ensure_snapd
  - snap.ensure_bases_store     ）

{% macro SNAP_LOCAL(block) %}
{% set pkg = block.name %}
{% set src = block.get('src_dir', 'salt://snaps/' + pkg) %}
{% set dst = block.get('dst_dir', '/tmp/snap-airgap/' + pkg) %}
{% set seq = block.get('sequence', [{"name":pkg,"file": pkg + "_*.snap"}]) %}

{{ pkg }}-dir:
  file.directory:
    - name: {{ dst }}
    - mode: '0755'

{{ pkg }}-stage:
  file.recurse:
    - name: {{ dst }}
    - source: {{ src }}
    - include_empty: False
    - clean: False
    - require:
      - file: {{ pkg }}-dir

{{ pkg }}-ack:
  cmd.run:
    - name: >
        bash -lc 'shopt -s nullglob; cd {{ dst }};
                  for a in *.assert; do snap ack "$a" || true; done'
    - require:
      - file: {{ pkg }}-stage
      - service: snapd-service
{% if not pkgs %}
No-Packages-Defined:
  test.show_notification:
    - text: "pillar:snap_pkgs Not provided, currently offline pkg will not be processed"
{% else %}
{%   for b in pkgs %}
{{ SNAP_LOCAL(b) }}
{%   endfor %}
{% endif %}

              
```
#### Sync Pillars and Apply Snap States

salt-run fileserver.update
salt 'minion2.tf.local' saltutil.refresh_pillar
salt 'minion2.tf.local' pillar.items snap_bases
salt 'minion2.tf.local' pillar.items snap_pkgs
salt 'minion2.tf.local' state.apply snap

### Test Install Snap Locally (Minion or Client Machine)
On the minion, run:

cd /tmp/snap-htop/

snap install ./htop.snap --dangerous


