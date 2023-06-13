- Feature Name: payg_cloud
- Start Date: 2021-08-11

# Summary
[summary]: #summary

In the three major public cloud providers (AWS, GCP and Azure), SUSE:
 - provides customized pay-as-you-go-specific product images (eg. SLES, SLES for SAP...)
 - operates per-region RMT Servers mirroring repositories for products available as pay-as-you-go

Pay-as-you-go instances all come with public cloud-specific "tokens" that authorizes the specific instance to download specific products from SUSE-operated RMT Servers. Pay-as-you-go instances are registered to the closest RMT Server at launch time (region/Server name is auto-determined).

At update time, a zypper plugin forwards such "token" to the RMT Server via custom headers.
To check repository accessibility RMT Servers have plugins which use public cloud-specific internal APIs to check whether the "token" is valid and which products it is entitled to.


# Motivation
[motivation]: #motivation

The Uyuni server needs to load repository data from external sources to provide it to the registered clients.
At the moment Uyuni server can synchronize repositories from:
  - the SCC CDN
  - a plain RMT Server ("from-mirror setup", still requires connection to SCC)
  - a plain directory exported from an RMT Server ("disconnected setup")
  - a custom repository

Presently, it is not possible to sync content from a SUSE-operated public cloud RMT Server, because:
  - an Uyuni Server does not come with "tokens" (unlike pay-as-you-go instances, see above)
  - an Uyuni Server does not know how to pass them to RMT Servers
  - an Uyuni Server does not know which repositories are served via such RMT Servers
  - an Uyuni Server does not know for which repos/products users are entitled for - which pay-as-you-go instances of which products they are running

Since the Uyuni server cannot contact the public cloud RMT servers the only option for users is to contact SUSE and get one SCC subscription which allows them to synchronize content from the SCC CDN.
The process for this is not straightforward and adds excessive complexity to users and SUSE teams.

The goal for this RFC is to propose a solution to simplify this process and allow Uyuni server to synchronize content directly from RMT public cloud servers in a self-serviceable way.


# Detailed design
[design]: #detailed-design

To be able to contact public cloud RMT server the uyuni server needs to collect authentication data from an existing pay-as-you-go instance.
For that uyuni server needs to ssh into the instance.
Since this authentication data have a time to live, uyuni server needs to extract it periodically, and for this reason the uyuni server needs to store ssh connection data.

Our solution will be based on the following steps:
  - Manage pay-as-you-go ssh connections data on Uyuni server
    - Register pay-as-you-go ssh connections data
    - Update existing ssh connections data
    - Delete pay-as-you-go ssh connections data
  - Develop a new taskomatic task and job schedule to:
    - Retrieve repositories and authentication data from the pay-as-you-go instance
    - Register repositories and authentication data on Uyuni server
  - Teach Uyuni reposync how public cloud RMT authentication data to synchronize product repositories


With this solution the expected user flow would be:
  - Provide to Uyuni server ssh information to connect to the pay-as-you-go instance
    - uyuni server will save this information on the database
    - start a single job execution to synchronize repositories and public cloud RMT authentication data
    - product loaded from the pay-as-you-go instance will be available to import after the task finishes
  - Import product using existing "add products" feature (available at UI, API, and cmd)
    - reposync will be able to download all needed data from public cloud RMT server
  - Bootstrap instances using the existing methods

## Manage pay-as-you-go ssh connection data

User should be able to register and manage ssh connection data to pay-as-you-go instances.
Connecting to those instances, uyuni server should extract repository information and authentication data.
Users should be able to manage ssh connection data using the web UI or the XML-RPC API.

Supported operations:
  - Add new ssh connection data for pay-as-you-go
    - should trigger an execution of the taskomatic task to extract data from the payg-as-you-go instance
  - Remove ssh connection data
    - Associated data in `suseCredentials` and `susesccrepositoryauth` should also be removed
  - Update ssh connection data
    - should trigger an execution of the taskomatic task to extract data from the payg-as-you-go instance
  - List existing ssh connection data

Data to be saved:
  - machine hostname
  - ssh port
  - ssh username
  - ssh password
  - ssh client certificate
  - ssh client certificate password
  - bastion hostname
  - bastion ssh port
  - bastion ssh username
  - bastion ssh password
  - bastion ssh client certificate
  - bastion ssh client certificate password

## Taskomatic task

RMT authentication data have a time to live (TTL). For this reason, we need refresh authentication data from the pay-as-you-go instance periodically.
For that, a new taskomatic job and schedule need to be developed to:
  - Connect to pay-as-you-go instance and retrieve the authentication data
  - Update existing data on Uyuni server

Task schedule frequency is an implementation detail but it should cope with the requirements of all public cloud providers. For example, Azure public cloud, RMT tokens have a TTL of 20 minutes.

### Retrieving authentication data from pay-as-you-go instance

A script will be created which could be run on a pay-as-you-go instance to extract all needed data to access RMT repos the instance has access to.
The returned data should be:
  - repository URL
  - authentication headers
  - HTTP authentication credential
  - RMT hosts name and IP address
  - RMT https certificate

The Uyuni server will execute this script on the pay-as-you-go client via SSH and retrieved data in JSON format.

#### URL and authentication header
Pay-as-you-go instances come with the `cloud-regionsrv-client` package, which provides a zypper plugin (`/usr/lib/zypp/plugins/urlresolver/susecloud`) that takes public cloud-specific crypto and configuration files from the instance and computes:
  - each repository full URL, including the hostname of the nearest RMT server
  - a special authentication header

Since zypper plugins are standalone executables and communicate via a simple text protocol on stdin/stdout:
https://github.com/openSUSE/zypp-plugin/blob/master/python/zypp_plugin.py

we can call such a zypper plugin ("impersonating zypper") to compute URLs and headers in a trivial and cross-cloud way.
https://gist.github.com/moio/b064c1d8cb91a00fd4545f3625ee3911

#### HTTP auth credentials
Plain HTTP authentication credentials are required to access the repositories.
Those credentials are stored in plain text `/etc/zypp/credentials.d/<repo_name>` and can be read by root.

#### RMT Server IP
RMT server domain name are not registered in DNS server, and the IP is specified on the `/etc/hosts` file of the pay-as-you-go instance.
We can call the command `getent hosts <RMT_HOST_NAME>` to retrieve the IP address, which will cope with future changes to this mechanism.

#### RMT Certificate
All pay-as-you-go instances connect to RMT servers via https, and their certificates are signed by SUSE, and added to the pay-as-you-go instance at creation.
We can load the certificate from `/usr/share/pki/trust/anchors/registration_server_<RMT_IP_REPLACE_DOT_WITH_UNDERSCORE>.pem`.

### Remotely run data extraction script

Uyuni sever should open an ssh connection to the pay-as-you-go machine, execute the data extraction script, and retrieve the result in JSON format.
Uyuni server should have support to receive the needed ssh parameters in the web UI (similar to the system bootstrap page) or via the XML-RPC API.
SSH authentication with basic auth and client certificate should be possible.

For this implementation we will use JSCH library, similar to what is being used in `SSHPushWorker` class.

### Store authentication data from pay-as-you-go instance

Uyuni server will create vendor channels for the pay-as-you-go integration. The advantage would be that if such vendor channels had the correct channel label, then mgr-sync would link them to the appropriate products at next `mgr-sync` time, allowing CVE Audit, Product Migration and other features requiring correct product data to work correctly.

Uyuni server always gets all products meta information from SCC: which products exists and all repositories assigned.
These products are only showed in the products setup wizard page if an authentication mechanism for the repositories is available, meaning users have access to it.

The proposed solution will implement a new authentication mechanism on uyuni server (named `cloudrmt`, for example) to deal with public cloud RMT server authentication. With this approach we will be able to reuse the existing product/channel management features.

#### Implementation step - Public cloud RMT server access

To access the public cloud RMT server uyuni server needs to know is IP address (which is not registered in DNS) and trust the server certificate.

The current public cloud setup requires changing `/etc/hosts` to reach the correct RMT server. This might not be possible if ever Uyuni server is delivered as containers. In the context of this RFC implementation we will follow the same approach a update `/etc/hosts` on Uyuni server.

Public cloud RMT https certificate is also returned by the data extraction tool and on uyuni server we need to:
  - add the certificate to folder `/etc/pki/trust/anchors/<label>`
  - run command `update-ca-certificates`

#### Implementation step - Register new pay-as-you-go repositories

After we get all repository information from the pay-as-you-go instance, for each repository we will need to:

##### Find internal SUSE SCC repository ID

Repositories are identified by its URL. We can extract repository endpoint from pay-as-you-go machine and find the corresponding repository in Uyuni database. Note that the public cloud RMT server have a url path have a prefix `/repo/` which we need to remove before compare.

Example:
- URL on pay-as-you-go instance: `https://host/repo/SUSE/Products/SLE-Module-Basesystem/15-SP2/x86_64/product/`
- URL uyuni database (suseSccRepository table): `https://updates.suse.com/SUSE/Products/SLE-Module-Basesystem/15-SP2/x86_64/product/`

Query to be executed: `select id from susesccrepository where url like '%SUSE/Products/SLE-Module-Basesystem/15-SP2/x86_64/product/';`

The query above will return the internal suse scc repository ID, to be used in next step.

##### Save repository authentication data

- If not exists, add a new entry to table `susecredentials`, with the new authentication type `cloudrmt`, containing the repository basic authentication credentials.
  - URL: RMT server base URL
  - New column to save authentication header
- Add a new entry to table `susesccrepositoryauth` for each repository, where:
  - repo_id: the one obtained in previous step
  - credentials_id: the one obtain from `susecredentials`
  - source_id: null
  - auth_type: `cloudrmt`

We also need to save the repository base URL in `suseCredentials` table. URL from table `susesccrepository` is pointing to SCC and we need to connect to the RMT public cloud servers. For that we need to save URL prefix, including hostname.
Example of RMT base URL:
- URL on pay-as-you-go instance: `https://host/repo/SUSE/Products/SLE-Module-Basesystem/15-SP2/x86_64/product/`
- Sub-string used to search repository on `susSccrespository` table: `/Products/SLE-Module-Basesystem/15-SP2/x86_64/product/`
- Repository base URL to save on `suseCredentials` table: `https://host/repo`

## Add product

When a product is added the table `rhncontentsource` is populated according to the authentication mechanism defined in table `susesccrepositoryauth`. The url saved to `rhncontentsource` depends on the authentication method in use.

For the new `cloudrmt` authentication method the url should be composed as:
- Concatenation of base URL from `suseCredentials` with the url path from `susesccrepository`
- Authentication will use the same mechanism as basic authentication, where id of `suseCredentials` is passed as query string in the repository URL

In case of multiple options authentication options are available we will need to select one to be used.
By default, uyuni server should select SCC CDN out of reliability concerns.

## Teach reposync on how to use public cloud RMT authentication mechanism

Reposync is already able to deal with the basic authentication mechanism. It receives the id of a `suseCredentials` record and loads the basic authentication data.
This mechanism will be enhanced to consider also the new column with the authentication headers. The following changes need to be implemented:
  - Modify method [`_url_with_repo_credentials`](https://github.com/uyuni-project/uyuni/blob/master/backend/satellite_tools/reposync.py#L1785) to also load and return the http authentication headers from table `suseCredentials`
  - Enhance [repository plugins](https://github.com/uyuni-project/uyuni/tree/master/backend/satellite_tools/repo_plugins) to receive http headers
  - Enhance reposync [zypper plugin](https://github.com/uyuni-project/uyuni/blob/master/backend/satellite_tools/spacewalk-extra-http-headers) to receive http header. Header will be written to a temporary file in the same location of zypper `.repo` file.

Another mechanism for [authentication headers](https://github.com/uyuni-project/uyuni/pull/2136) is already in place which loads headers from a configuration file. We should cope with this implementation and merger header loaded form both locations.

# Drawbacks
[drawbacks]: #drawbacks

* The current public cloud setup requires changing `/etc/hosts` to reach the correct RMT server. This can be a problem if Uyuni server is deliver as container in the future.

# Alternatives
[alternatives]: #alternatives

## Uyuni/SUSE manager pay-as-you-go

We could define a uyuni/suse manager pay-as-you-go server image with access to all public cloud RMT repositories.
It would be possible to synchronize any product directly from public cloud in a more simple and straightforward way.

**Drawbacks:**
- User will have access to repository and product he is not paying for.
- Will not be suitable for scenarios were Uyuni server is on-premise but managing public cloud instances

## Reposync only metadata

Change reposync and SCC to allow metadata access without SCC account to load repositories metadata.
Pay-as-you-go client could download data from public cloud RMT server directly.
This will be a huge change, not sure if it is even possible to all providers.
Possible security impact of having repository metadata publicly accessible.

# Unresolved questions
[unresolved]: #unresolved-questions

- What happens and how to deal if the pay-as-you-go instance we loaded the data from get terminated or stopped?
  - Possible approach is remove the affected cloudrmt auth configs from the Server. Channels will be kept with all the existing content and assigned server will still see it. But no new updates will added to the channels.

- Should we have a UI showing all the pay-as-you-go authentications registered and allow user to remove existing ones?
