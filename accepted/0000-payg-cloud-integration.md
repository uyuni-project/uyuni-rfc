- Feature Name: payg_cloud
- Start Date: 2021-08-11

# Summary
[summary]: #summary

In the three major Public Clouds (AWS, GCP and Azure), SUSE:
 - provides customized pay-as-you-go-specific product images (eg. SLES, SLES for SAP...)
 - operates per-region RMT Servers mirroring repositories for products available as PAYG

PAYG instances all come with Cloud-specific "tokens" that authorizes the specific instance to download specific products from SUSE-operated RMT Servers. PAYG instances are registered to the closest RMT Server at launch time (region/Server name is auto-determined).

At update time, a zypper plugin forwards such "token" to the RMT Server via custom headers.
To check repository accessibility RMT Servers have plugins which use Cloud-specific internal APIs to check whether the "token" is valid and which products it is entitled to.


# Motivation
[motivation]: #motivation

Uyuni needs to load repository data from external sources to provide it to the registered machines.
At the moment Uyuni can syncronize repositores from:
  - the SCC CDN
  - a plain RMT Server ("from-mirror setup", still requires connection to SCC)
  - a plain directory exported from an RMT Server ("disconnected setup")
  - a custom repository

Presently, it is not possible to sync content from a SUSE-operated Cloud RMT Server, because:
  - a Uyuni Server does not come with "tokens" (unlike PAYG instances, see above)
  - Uyuni does not know how to pass them to RMT Servers
  - we do not know which repositories are served via such RMT Servers

Since Uyuni cannot contact the cloud RMT servers the only option for users is to contact SUSE and get one SCC account which allows to synchronize content from the SCC CDN.
The process for this is not straightforward and adds extract complexity to users and SUSE teams.

The goal for this RFC is to propose a solution to simplify this process and allowed Uyuni to synchronize content directly from RMT cloud servers in a user friendly way.


# Detailed design
[design]: #detailed-design

Our solution will be based on the following steps:
  - Connect to PAYG instance, extract authentication data to uyuni server
  - Teach Uyuni how to use PAYG authentication data to reposync product repositories

With this solution the expected user flow would be:
  - Provide to Uyuni ssh information to connect to the PAYG instance
    - uyuni will extract data from the PAYG instance
    - product of the PAYG instance will then be displayed on the Products Setup Wizard
  - Import product from the products setup wizard
    - all channels will be added
    - reposync will be able to download all needed data fro cloud RMT server
  - Bootstrap PAYG instances using one of the existing methods

## Retrieving authentication data from PAYG instance

A script will be created which could be run on a PAYG instance to extract all needed data to access RMT repos the instance has access to.
Data needs from the extraction tool:
  - repository URL
  - authentication headers
  - HTTP authentication credential
  - RMT hosts name and IP address
  - RMT https certificate

This script can be remotely executed from uyuni and retrieved data in a json format.

### Data extraction script

This will be a python script which can be executed locally on the PAYG instance and extract all the needed data (mentioned above) returning it in json format.
Next we will explain how this data can be obtain in the PAYG instance.

#### URL and authenticatio header
PAYG instances come with the `cloud-regionsrv-client` package, which provides a zypper plugin (`/usr/lib/zypp/plugins/urlresolver/susecloud`) that takes Cloud-specific crypto and configuration files from the instance and computes:
  - each repository full URL, including the hostname of the nearest RMT server
  - the special authentication header

Since zypper plugins are standalone executable and communicate via a simple text protocol on stdin/stdout:
https://github.com/openSUSE/zypp-plugin/blob/master/python/zypp_plugin.py

we can call such a zypper plugin ("impersonating zypper") to compute URLs and headers in a trivial and cross-Cloud way.
https://gist.github.com/moio/b064c1d8cb91a00fd4545f3625ee3911

#### HTTP auth credentials
Plain HTTP authentication credentials are required to access the repositories.
Those credentials are stored in plain text `/etc/zypp/credentials.d/<repo_name>` and can simply be read by root.

#### RMT Server IP
RMT server domain name are not registered in DNS server, and the IP is specified on the `/etc/hosts` file of the PAYG instance.
We can call the command `getent hosts <RMT_HOST_NAME>` to retrieve the IP address, which will cope with future changes to this mechanism.

#### RMT Certificate
RMT server https certificate is signed by suse, is added to the PAYG instance.
We can load the certificate from `/usr/share/pki/trust/anchors/registration_server_<RMT_IP_REPLACE_DOT_WITH_UNDERSCORE>.pem`.

### Remotely run data extraction script

Uyuni sever should open an ssh connection to the PAYG machine, execute the data extraction script, and retrieve the result in a json format.
Should have support to receive the needed ssh parameters in the web UI (similar to what we have on system bootstrap) or from XML-RPC API.
SSH authentication with basic auth and client certificate should be possible.

For this implementation we will use JSCH library, similar to what is being used in `SSHPushWorker` class.

## Teaching Uyuni how to use cloud RMT

### Context

Uyuni will create vendor channels for the PAYG integration. The advantage would be that if such vendor channels had the correct channel label, then mgr-sync would link them to the appropriate products at next `mgr-sync` time, allowing CVE Audit, Product Migration and other features requiring correct product data to work correctly.

Uyuni always gets all products meta information from SCC: which products exists and all repositories assigned.
These products are only showed in the products setup wizard page if an authentication mechanism for the repositories is available, meaning user have access to it.

The proposed solution will implement a new authentication mechanism on uyuni (named `cloudrmt`, for example) to deal with cloud RMT server authentication. With this approach we will be able to reuse the existing product/channel management features.

### Implementation steps - Cloud RMT server access

To access the cloud RMT server uyuni server needs to know is IP address (which is not registered in DNS) and trust the server certificate.

Cloud RMT IP needs to be added to `/ets/hosts` on uyuni server. IP and hostname are returned by the data extraction script.

Cloud RMT https certificate is also returned by the data extraction tool and on uyuni server we need to:
  - add the certificate to folder `/etc/pki/trust/anchors/<label>`
  - run command `update-ca-certificates`

### Implementation steps - Register new PAYG repositories

After we get all repositories information from the PAYG instance, for each repository we will need to:

#### Find internal suse Scc repository ID

Repositories are identified by its URL. We can extract repository endpoint from PAYG machine and find the corresponding repository in Uyuni database. Note that the cloud RMT server have a url prefix `/repo/` which we need to remove before compare.

Example:
- URL on PAYG instance: `https://host/repo/SUSE/Products/SLE-Module-Basesystem/15-SP2/x86_64/product/`
- URL uyuni database (suseSccRepository table): `https://updates.suse.com/SUSE/Products/SLE-Module-Basesystem/15-SP2/x86_64/product/`

Query to be executed: `select id from susesccrepository where url like '%SUSE/Products/SLE-Module-Basesystem/15-SP2/x86_64/product/';`

The query above will return the internal suse scc repository ID, to be used in next step.

#### Insert repository authentication data

- If not exists, add a new entry to table `susecredentials`, with the new authentication type `cloudrmt`, containing the repository basic authentication credentials.
- Add a new entry to table `susesccrepositoryauth` for each repository, where:
  - repo_id: the one obtained in previous step
  - credentials_id: the one obtain from `susecredentials`
  - source_id: null
  - auth_type: `cloudrmt`
  - auth: authentication header obtained from the PAYG instance for the repository

We also need to save the repository URL, since we will not be able to use the existing SCC repository url.
If this information will be saved in a new table field of `susesccrepositoryauth` table or in a new table is a implementation detail.


### Implementation steps - Add product with setup wizard

When a product is added in the setup wizard table `rhncontentsource` is populated according to the authentication mechanism defined in table `susesccrepositoryauth` using the repository url defined in table `susesccrepository`.

We need to adapt this feature to consider the new `cloudrmt` authentication mechanism and copy the basic authentication and headers:
  - basic authentication can be defined on repo URL (`https://user:pass@host/repo/url/`)
  - authentication header location is an implementation detail
    - One idea is concatenate in URL as query string parameter and adapt reposync extract and use it
    - another possibility is using the existing mechanism, which reads from a configuration file: https://github.com/uyuni-project/uyuni/pull/2136

Url to be used should be the one pointing to the cloud RMT server, saved in previous step, instead the one defined in table `susesccrepository`.

### Implementation steps - reposync

Reposync is already able to deal with the basic authentication mechanism (defined in repository URL).
Http authentication headers can be read from a configuration file, specified per repository.
Has mentioned before we need to decide how to deal with this header, if reuse the existing mechanism of implement a new one based on the database. How the header is passed from table `susesccrepositoryauth` to `rhncontentsource` and how is consume by reposync is an implementation detail.

We need to maintain this table separation because reposync already have several different mechanisms relaying on this separation.


# Drawbacks
[drawbacks]: #drawbacks

# Alternatives
[alternatives]: #alternatives

## Uyuni/SUSE manager PAYG

We could define a uyuni/suse manager PAYG image with access to all cloud RMT repositories.
It would be possible to syncronize any product directly from cloud in a more simple and straightforward way.
Drawbacks: User will have access to repository and product he is not paying for.

## Reposync only metadata

Change reposync and SCC to allow metadata access without SCC account to load repositories metadata.
PAYG client could download data from cloud RMT server directly.
This will be a huge change, not sure if it is even possible to all providers.
Possible security impact of having repository metadata publicly accessible.

# Unresolved questions
[unresolved]: #unresolved-questions

- What happens and how to deal if the PAYG instance we loaded the data from get terminated or stopped?

- Should we have a UI showing all the PAYG authentications registered and allow user to remove existing ones?
