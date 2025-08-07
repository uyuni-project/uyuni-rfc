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

At this stage, we may be able to store the beta and candidate Snap packages in the cache.
However, since .snap binary packages are typically two to three times larger than .deb packages, it may be more efficient to use a pre-selection strategy for the stable channel.


## Method 1: Simulating the Snap Store with a Mock API for Offline Snap Package Deployment

Proposed approach:

1. Load the full list of available packages.

2. Allow the client to select which packages they want to manage.

3. Download only the selected packages to the repository cache. (by this way support part of airgap environment)

### Stage 1 Download the file from Snapcraft

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

#### Snap Package Repository Design
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


#### Synchronization (Cron Job)
A scheduled cron job should:

Call the Snapcraft API to fetch updated package metadata:

GET https://api.snapcraft.io/api/v1/snaps/search?q=a  # Repeated for a–z
Update the snap_repo table with the latest Snap metadata.

Ensure new packages and updated revisions are stored and ready for selection in the UI/CLI.

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

### Stage 2 Implement API on uyuni backend

This describes how to simulate the Snap Store API locally, allowing Snap packages to be installed in air-gapped environments by intercepting and serving Snap metadata and binaries from a Uyuni server. 

To understand how Snap package installation works, I used mitmproxy to intercept and analyze network traffic during a snap install operation. When executing a command such as snap install <package>, the Snap client sends several HTTPS requests to the Snapcraft API endpoint at https://api.snapcraft.io. The key requests observed include:

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

To simulate the Snap Store (api.snapcraft.io) within Uyuni, the Uyuni server must be able to mock at least these four types of API routes, providing valid responses for the assertions and refresh logic expected by snapd. All my mock api designs proposed are based on these observed interactions.


#### Step 1: Download Snap Binary and Assertion Files 

In Snap, installing a package requires not only the .snap binary itself, but also a set of assertion files. These assertions are cryptographically signed metadata used by snapd to verify the authenticity, origin, and permissions of the package.

The following components must be prepared in advance. This preparation should be completed during Stage 1, when the client creates a channel for Snap packages:

The actual Snap package binary (compressed squashfs, e.g., hello_42.snap)

snap-revision.assert

snap-declaration.assert

account-key.assert

On the Uyuni server, the local repository should be structured as follows:
```
/snap_repo/
├── hello_42.snap
├── hello_42.assert
├── hello_42.snap-declaration.assert
└── hellp_42.account-key.assert
```

#### Step 2: DNS Configuration

To redirect Snap client traffic to the Uyuni server instead of the official Snap Store, DNS interception must be configured on the client (minion) machine.

One simple method is to modify the /etc/hosts file on the minion:

echo "<UYUNI_SERVER_IP> api.snapcraft.io" | sudo tee -a /etc/hosts
This maps api.snapcraft.io to the Uyuni server's IP address, effectively redirecting all Snap API requests to the mock server.

#### Step 3: Generate TLS Certificates:

Because Snap uses HTTPS for secure communication, simulating the Snap Store requires a valid TLS setup on the Uyuni server.

Follow these steps:

Use a tool such as mkcert to generate a TLS certificate for uyuni server.

Install the Root CA on the Client

The root CA generated by mkcert must be installed into the system trust store of the client (minion), so that it trusts the Uyuni server's TLS certificate.

Establish Secure Communication

Once the Uyuni server is set up with the certificate, and the minion trusts the CA, the Snap client will be able to communicate securely with the Uyuni server over HTTPS as if it were api.snapcraft.io.

```
uyuni-server:mkcert -install
uyuni-server: mkcert api.snapcraft.io
uyuni-server:/ # scp api.snapcraft.io.pem root@192.168.122.56:/usr/local/share/ca-certificates/
(venv-salt-minion) root@minion: sudo update-ca-certificates
(venv-salt-minion) root@minion: curl -vk https://api.snapcraft.io:443/

```

#### Step 4 Construct API server

In the proof-of-concept (PoC) stage, I used Flask, a lightweight Python web framework, to construct the mock API server. Flask allows for rapid prototyping and testing of API behavior. If this approach proves viable, I plan to design a production-ready version using Java, aligned with Uyuni's existing backend stack.

To redirect Snap client traffic to the mock API server, configure DNS resolution by either:

Adding an entry in /etc/hosts, or

Setting up internal DNS to resolve api.snapcraft.io to the Uyuni server's IP address (e.g., 127.0.0.1 for local development).

Implementing API Endpoints

The mock server should simulate the key Snap Store API routes required for package installation and verification. In Flask, the following routes are implemented:
```

@app.route('/v2/snaps/refresh', methods=['POST'])

@app.route('/api/v1/snaps/download/<snap_id>.snap', methods=['GET'])

@app.route('/v2/assertions/snap-revision/<assertion_id>', methods=['GET'])

@app.route('/v2/assertions/account/<account_id>', methods=['GET'])

@app.route('/v2/assertions/account-key/<key_id>', methods=['GET'])

Each route should serve the corresponding file from the local repository (e.g., /snap_repo/) with the appropriate headers. 

For example:

Assertion files must be served with:

Content-Type: application/x.ubuntu.assertion

Snap packages must be served with:

Content-Type: application/octet-stream
```

This setup allows the snapd client to behave as if it is interacting with the official Snap Store, enabling offline or internal deployments of Snap packages within Uyuni.

#### Step 5 : Test Install Snap Locally (Minion or Client Machine)
On the minion, run:

snap install hello_42.snap

This manually acknowledges the signatures and installs the snap fully offline.

## Method 2: Integrate Snap Store Proxy into Uyuni

Canonical provides a solution called the **Snap Store Proxy**. This proxy allows devices (called minions in Uyuni) to:

- Cache and mirror Snap packages locally
- Enforce network policies
- Provide limited offline support
- Retain some visibility into package usage

### Basic Steps to Use Snap Store Proxy

To set up and use a Snap Store Proxy (either in online or offline mode), follow these core steps:

- Install a Snap Store Proxy
- Register a Snap Store Proxy
- Configure HTTPS
- Configure devices

However, using Snap Store Proxy comes with several caveats:
- It only runs on **Ubuntu LTS** systems
- Requires **manual registration** with an Ubuntu One account
- Becomes a **paid feature** if used to manage more than 25 devices
- Configuration of proxy, TLS, and client trust relationships must be done manually

## 1.  Platform-Level Automation (Snap Proxy Setup)

### 1.1 Provide a Pre-Built Container Image
- Build and offer a container image based on **Ubuntu LTS** with:
  - Snap Store Proxy pre-installed
  - PostgreSQL pre-installed
- Customer can run it easily:
  ```bash
  podman run -d -p 80:80 -p 443:443 uyuni/snap-proxy
  ```

### 1.2 Automate `snap-proxy config` via Uyuni UI/CLI
- Provide UI form or Salt module to set `proxy.domain`:
  ```bash
  sudo snap-proxy config proxy.domain="snaps.myorg.internal"
  ```

### 1.3 Assist with Proxy Registration
- Snap Proxy **registration must be done manually** due to Canonical requirements.
- Uyuni can:
  - Open a guided registration web link
  - Pre-fill known values
  - Let users upload the resulting **Store ID** to Uyuni UI

---

## 2.  Client-Side Automation (Minion Setup)

### 2.1 Use Salt to Configure Proxy Trust
- Provide a Uyuni Salt module like:
  ```bash
  snapproxy.set_store <proxy-domain> <store-id>
  ```
- This encapsulates:
  ```bash
  curl -sL http://<proxy-domain>/v2/auth/store/assertions | sudo snap ack /dev/stdin
  sudo snap set core proxy.store=<STORE_ID>
  ```

### 2.2 Bind Snap Proxy Settings to Channels
- Allow Snap channels in Uyuni to be associated with a proxy config.
- When a minion subscribes to the channel, proxy setup is triggered automatically.

### 2.3 Auto-Deploy TLS Certificates
- If using HTTPS, Uyuni can distribute Snap Proxy CA certs to all minions via Salt:
  ```bash
  /var/lib/snapd/certs/mitmproxy-ca-cert.pem
  ```

---

## 3.  Visibility and Control

### 3.1 Log Collection from Minions
- Use Salt to fetch and parse `/var/log/snapd.log`
- Display installed Snap packages per minion on the Uyuni dashboard

### 3.2 Parse Snap Proxy Logs
- Snap Proxy has an API to access download logs.
- Uyuni can collect and visualize Snap installs via the proxy.

---
## Method 3: Import Brand Store and Perform Controlled Updates

Building on Method 2, we understand that the key requirement for using Snap Store Proxy is the **registration step** with Canonical. This process involves:

- A registration interaction between the **proxy host and Canonical**.
- Providing an **email address** and answering **personal verification questions**.
- Once validated, Canonical assigns a **Store ID** and issues a **store assertion**, which binds the proxy to that Store ID.

### Challenge: Skipping Canonical Registration

If we want to **bypass this registration process**, one extreme approach would be to have **Uyuni act like Canonical**, generating its own store assertion and serving as the trust root. 

However, this would require **re-implementing Snap's core trust model**, introducing significant complexity and security risks.

---

### An Alternative Approach: Use a Brand Store

Instead of emulating Canonical, we propose using Canonical’s **official enterprise solution** — the **Brand Store**.

#### Proposal:

1. **Register a Brand Store for Uyuni**  
   Canonical offers a private, managed Snap Store (called a Brand Store) for a fee. This gives Uyuni its own dedicated Snap publishing and validation environment.

2. **Make the Uyuni Brand Store the Upstream for Snap Store Proxy**  
   Rather than communicating with the public `api.snapcraft.io`, the Snap Store Proxy would talk to Uyuni’s Brand Store instance.

3. **Manage and Curate Snaps via the Brand Store**  
   Uyuni could publish, test, approve, and distribute specific Snap packages. This gives us full control over:
   - Which Snap revisions are allowed
   - Software lifecycle and patching
   - Security and compliance

---

###  Benefits

- **Full control** over Snap content and device access.
- **Leverages Canonical’s supported infrastructure** without rebuilding the trust system.
- **Supports offline/air-gapped deployment** with strong assurance.
- **Brand-specific authentication** via serial assertions (if needed).

---

### Trade-offs

- This is a **paid service**.
- Uyuni needs to evaluate its **cost-effectiveness** based on:
  - Customer scale
  - Frequency of Snap changes
  - Value of controlled software supply chain

---



