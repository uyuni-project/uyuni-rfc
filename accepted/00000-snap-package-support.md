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

Proposed approach:

1. Load the full list of available packages.

2. Allow the client to select which packages they want to manage.

3. Download only the selected packages to the repository cache. (by this way support part of airgap environment)

## Stage 1 Download the file from Snapcraft

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

For Snap support, we follow a similar logic. However, installing a Snap package requires not just a binary file (.snap), but also three associated assertion files:

snap-revision.assert

snap-declaration.assert

account.assert + account-key.assert

In Stage 1, we focus on supporting the Stable channel from Snapcraft.

### UI Proposal for Snap:

When creating a channel for Snap, the form structure remains similar to existing deb/yum workflows (channel name, label, summary, etc.).

For the repository creation step:

If the user selects "Repository Type = Snap", the URL input field can be hidden.

Instead, a dropdown list of available Snap packages should be provided.

The user can select one or more packages to download from Snapcraft.

### CLI Proposal for Snap:
We propose extending spacewalk-repo-sync with support for Snap packages:

spacewalk-repo-sync --channel=snap_stable_ubuntu2204 --type=snap --add-snaps="hello-world,vlc"
In addition, we could provide a helper function to list all Snap packages Uyuni can support or has access to:

spacewalk-repo-sync --list-snaps
This will return a list of available Snap packages that can be selected during channel creation.

### Snap Package Repository Design
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


### Synchronization (Cron Job)
A scheduled cron job should:

Call the Snapcraft API to fetch updated package metadata:

GET https://api.snapcraft.io/api/v1/snaps/search?q=a  # Repeated for a–z
Update the snap_repo table with the latest Snap metadata.

Ensure new packages and updated revisions are stored and ready for selection in the UI/CLI.

## Stage 2 Offline Snap Package Management in Uyuni

### Method 1: Simulating the Snap Store with a Mock API for Offline Snap Package Deployment

#### Mock Api : 
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


##### Step 1: Download Snap Binary and Assertion Files 

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

##### Step 2: DNS Configuration

To redirect Snap client traffic to the Uyuni server instead of the official Snap Store, DNS interception must be configured on the client (minion) machine.

One simple method is to modify the /etc/hosts file on the minion:

echo "<UYUNI_SERVER_IP> api.snapcraft.io" | sudo tee -a /etc/hosts
This maps api.snapcraft.io to the Uyuni server's IP address, effectively redirecting all Snap API requests to the mock server.

##### Step 3: Generate TLS Certificates:

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


##### Step 4 Construct API server

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

##### Step 5 : Test Install Snap Locally (Minion or Client Machine)
On the minion, run:

snap install hello_42.snap

This manually acknowledges the signatures and installs the snap fully offline.

## Method 2 Emulating a Local Snap Store in Uyuni Using a Custom CA and Snap Store Proxy

#### Step 1: Design the Signing System(to be investigated)

#### Step 2: Configure Client Trust Chain

##### 2.1 Distribute Uyuni Root CA

Send the Uyuni root CA to all managed clients via Uyuni or Salt, and run:

sudo mkdir -p /etc/snapd/assertions

sudo cp uyuni-root-ca.assert /etc/snapd/assertions/

sudo snap ack /etc/snapd/assertions/uyuni-root-ca.assert

##### 2.2 Acknowledge Uyuni Assertions

Send these assertion files to the client and run:

sudo snap ack uyuni-store.assert

sudo snap set core proxy.store=<STORE_ID>

#### Step 3: Deploy Snap Store Proxy

##### 3.1 Install Snap Store Proxy

Due to the requirement that Snap Store Proxy must be deployed on Ubuntu LTS, while most Uyuni users operate on openSUSE systems, we propose to provide a dedicated image—similar to a container—that includes both the Snap client and the Snap Store Proxy. This would allow Uyuni to support Snap functionality in a cross-distro environment.

```
eg 

docker run -d --name=snap-store-proxy \
  -v /path/to/config:/config \
  -p 80:80 -p 443:443 \
  snapcore/snap-store-proxy
```

##### 3.2 Mock snap-proxy register (Bypass Canonical)

Normally should run:

sudo snap-proxy register

But this contacts Canonical. To bypass it:

Skip this step entirely.
Manually load Uyuni-signed assertions and CA certificate created by step1:

cat uyuni-root-ca.crt | sudo snap-proxy use-ca-certs

sudo snap restart snap-store-proxy

This simulates a “registration” using uyuni own root CA.


#### Step 4: Validate & Automate
##### 4.1 Validation
On a Uyuni-managed client, try:

sudo snap install hello

If the client was configured correctly, the Snap should be pulled from your local Snap Store Proxy, which in turn forwards API requests to your Uyuni-hosted Mock API.

##### 4.2 Automation
Integrate this flow into Uyuni’s Salt modules or installer scripts:

Generate & sign assertions

Distribute root CA to clients

Configure Snapd and Store Proxy

Install & configure Snap Store Proxy with Uyuni upstream

##### Notes
Key aspects of this architecture:

The client (snapd) must trust Uyuni’s custom CA.

The Snap Store Proxy must trust the same CA for upstream HTTPS requests to Uyuni.

Emulate the assertion format and signature validation logic.


### Approach Comparison
Two technical approaches are considered for enabling offline Snap package support in Uyuni:

Approach 1: Mock API Simulation
Simulates key Snap Store API endpoints (e.g., /v2/snaps/refresh, /v2/assertions/*) and serves locally cached assertion files and .snap binaries. This avoids Canonical registration and custom CA setup, allowing Uyuni to act as a fake Snap Store. While simpler to implement, this method is fundamentally hacky and may break if snapd behavior changes.

Approach 2: Snap Store Proxy with Custom CA
Deploys a local Snap Store Proxy instance and replaces Canonical’s signing chain with a custom Uyuni-owned CA. This requires setting up a certificate infrastructure, generating assertions signed by the custom CA, and distributing trust anchors to clients. Although closer to official enterprise usage, building and maintaining the entire CA trust chain is complex and time-consuming.

