- Feature Name: payg_cloud
- Start Date: 2021-08-11

# Summary
[summary]: #summary

In the three major Public Clouds (AWS, GCP and Azure), SUSE:
 - provides customized pay-as-you-go-specific product images (eg. SLES, SLES for SAP...)
 - operates per-region RMT Servers mirroring repositories for products available as pay-as-you-go

Pay-as-you-go instances all come with Cloud-specific "tokens" that authorizes the specific instance to download specific products from SUSE-operated RMT Servers. Pay-as-you-go instances are registered to the closest RMT Server at launch time (region/Server name is auto-determined).

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
  - a Uyuni Server does not come with "tokens" (unlike pay-as-you-go instances, see above)
  - Uyuni does not know how to pass them to RMT Servers
  - Uyuni Server do not know which repositories are served via such RMT Servers

Since Uyuni cannot contact the cloud RMT servers the only option for users is to contact SUSE and get one SCC account which allows to synchronize content from the SCC CDN.
The process for this is not straightforward and adds excessive complexity to users and SUSE teams.

The goal for this RFC is to propose a solution to simplify this process and allow Uyuni to synchronize content directly from RMT cloud servers in a user friendly way.


# Detailed design
[design]: #detailed-design

Our solution will be based on the following steps:
  - Connect to a pay-as-you-go instance, extract authentication data to Uyuni server
  - Teach Uyuni how to use pay-as-you-go authentication data to reposync product repositories
  - Manage existing pay-as-you-go ssh connections data saved on Uyuni

With this solution the expected user flow would be:
  - Provide to Uyuni ssh information to connect to the pay-as-you-go instance
    - uyuni will extract data from the pay-as-you-go instance
    - product of the pay-as-you-go instance will then be displayed on the Products Setup Wizard
  - Import product using existing "add products" feature (available at UI, API and cmd)
    - all channels will be added
    - reposync will be able to download all needed data fro cloud RMT server
  - Bootstrap pay-as-you-go instances using one of the existing methods

## Retrieving authentication data from pay-as-you-go instance

A script will be created which could be run on a pay-as-you-go instance to extract all needed data to access RMT repos the instance has access to.
Data retrieved by the extraction tool:
  - repository URL
  - authentication headers
  - HTTP authentication credential
  - RMT hosts name and IP address
  - RMT https certificate

Uyuni will execute this script on the pay-as-you-go client via SSH and retrieved data will be in JSON format.

### Data extraction script

Next we will explain how this data can be obtain in the pay-as-you-go instance.

#### URL and authentication header
Pay-as-you-go instances come with the `cloud-regionsrv-client` package, which provides a zypper plugin (`/usr/lib/zypp/plugins/urlresolver/susecloud`) that takes Cloud-specific crypto and configuration files from the instance and computes:
  - each repository full URL, including the hostname of the nearest RMT server
  - a special authentication header

Since zypper plugins are standalone executables and communicate via a simple text protocol on stdin/stdout:
https://github.com/openSUSE/zypp-plugin/blob/master/python/zypp_plugin.py

we can call such a zypper plugin ("impersonating zypper") to compute URLs and headers in a trivial and cross-Cloud way.
https://gist.github.com/moio/b064c1d8cb91a00fd4545f3625ee3911

#### HTTP auth credentials
Plain HTTP authentication credentials are required to access the repositories.
Those credentials are stored in plain text `/etc/zypp/credentials.d/<repo_name>` and can simply be read by root.

#### RMT Server IP
RMT server domain name are not registered in DNS server, and the IP is specified on the `/etc/hosts` file of the pay-as-you-go instance.
We can call the command `getent hosts <RMT_HOST_NAME>` to retrieve the IP address, which will cope with future changes to this mechanism.

#### RMT Certificate
All pay-as-you-go instances connect to RMT servers via https, and their certificates are signed by SUSE, and added to the pay-as-you-go instance at creation.
We can load the certificate from `/usr/share/pki/trust/anchors/registration_server_<RMT_IP_REPLACE_DOT_WITH_UNDERSCORE>.pem`.

### Remotely run data extraction script

Uyuni sever should open an ssh connection to the pay-as-you-go machine, execute the data extraction script, and retrieve the result in JSON format.
Uyuni should have support to receive the needed ssh parameters in the web UI (similar to the system bootstrap page) or via the XML-RPC API.
SSH authentication with basic auth and client certificate should be possible.

For this implementation we will use JSCH library, similar to what is being used in `SSHPushWorker` class.

Ssh connection data to the pay-as-you-go instance will be saved on Uyuni database. This data is needed to refresh repository authentication data periodically.

## Teaching Uyuni how to use cloud RMT

### Context

Uyuni will create vendor channels for the pay-as-you-go integration. The advantage would be that if such vendor channels had the correct channel label, then mgr-sync would link them to the appropriate products at next `mgr-sync` time, allowing CVE Audit, Product Migration and other features requiring correct product data to work correctly.

Uyuni always gets all products meta information from SCC: which products exists and all repositories assigned.
These products are only showed in the products setup wizard page if an authentication mechanism for the repositories is available, meaning users have access to it.

The proposed solution will implement a new authentication mechanism on uyuni (named `cloudrmt`, for example) to deal with cloud RMT server authentication. With this approach we will be able to reuse the existing product/channel management features.

### Implementation steps - Cloud RMT server access

To access the cloud RMT server uyuni server needs to know is IP address (which is not registered in DNS) and trust the server certificate.

Cloud RMT IP needs to be added to `/ets/hosts` on uyuni server. IP and hostname are returned by the data extraction script.

Cloud RMT https certificate is also returned by the data extraction tool and on uyuni server we need to:
  - add the certificate to folder `/etc/pki/trust/anchors/<label>`
  - run command `update-ca-certificates`

### Implementation steps - Register new pay-as-you-go repositories

After we get all repositories information from the pay-as-you-go instance, for each repository we will need to:

#### Find internal SUSE SCC repository ID

Repositories are identified by its URL. We can extract repository endpoint from pay-as-you-go machine and find the corresponding repository in Uyuni database. Note that the cloud RMT server have a url prefix `/repo/` which we need to remove before compare.

Example:
- URL on pay-as-you-go instance: `https://host/repo/SUSE/Products/SLE-Module-Basesystem/15-SP2/x86_64/product/`
- URL uyuni database (suseSccRepository table): `https://updates.suse.com/SUSE/Products/SLE-Module-Basesystem/15-SP2/x86_64/product/`

Query to be executed: `select id from susesccrepository where url like '%SUSE/Products/SLE-Module-Basesystem/15-SP2/x86_64/product/';`

The query above will return the internal suse scc repository ID, to be used in next step.

#### Insert repository authentication data

- If not exists, add a new entry to table `susecredentials`, with the new authentication type `cloudrmt`, containing the repository basic authentication credentials.
  - URL: RMT server base URL
  - New column to save authentication header
- Add a new entry to table `susesccrepositoryauth` for each repository, where:
  - repo_id: the one obtained in previous step
  - credentials_id: the one obtain from `susecredentials`
  - source_id: null
  - auth_type: `cloudrmt`

We also need to save the repository base URL in `suseCredentials` table. URL from table `susesccrepository` is pointing to SCC and we need to connect to the RMT cloud servers. For that we need to save URL prefix, including hostname.
Example of RMT base URL:
- URL on pay-as-you-go instance: `https://host/repo/SUSE/Products/SLE-Module-Basesystem/15-SP2/x86_64/product/`
- Sub-string used to search repository on `susSccrespository` table: `/Products/SLE-Module-Basesystem/15-SP2/x86_64/product/`
- Repository base URL to save on `suseCredentials` table: `https://host/repo`


### Implementation steps - Add product with setup wizard

When a product is added in the setup wizard table `rhncontentsource` is populated according to the authentication mechanism defined in table `susesccrepositoryauth` using the repository url defined in table `susesccrepository`.

We need to adapt this feature to consider the new `cloudrmt` authentication mechanism. URL that will be inserted in `rhncontentsource` will have the following rules:
  - Concatenation of base URL from `suseCredentials` with the url path from `susesccrepository`
  - Authentication will use the same mechanism as basic authentication, where id of `suseCredentials` is passed as query string in the repository URL


### Implementation steps - reposync

Reposync is already able to deal with the basic authentication mechanism. It receives the id of a `suseCredentials` record and loads the basic authentication data.
This mechanism will be enhanced to consider also the new column with the authentication headers. The following changes need to be implemented:
  - Modify method [`_url_with_repo_credentials`](https://github.com/uyuni-project/uyuni/blob/master/backend/satellite_tools/reposync.py#L1785) to also load and return the http authentication headers from table `suseCredentials`
  - Enhance [repository plugins](https://github.com/uyuni-project/uyuni/tree/master/backend/satellite_tools/repo_plugins) to receive http headers
  - Enhance reposync [zypper plugin](https://github.com/uyuni-project/uyuni/blob/master/backend/satellite_tools/spacewalk-extra-http-headers) to receive http header. We have two implementation options:
    - Add http headers to zypper `.repo` file as extra field. Verify if the implementation is possible and doesn't impact zypper command.
    - Write the headers to a temporary file in the same location of zypper `.repo` file

Another mechanism for [authentication headers](https://github.com/uyuni-project/uyuni/pull/2136) is already in place which loads headers from a configuration file. We should analyze if it can be merged with the new implementation.


### Implementation steps - Refresh repository authentication data

RMT authentication data have a time to live (TTL). For this reason, we need to load new authentication data from the pay-as-you-go instance periodically. For that, a new taskomatic job needs to be defined to:
  - Connect to pay-as-you-go instance and retrieve the authentication data
  - Update existing data on Uyuni server


## Manage ssh connection data to pay-as-you-go instance

Since ssh connection data to pay-as-you-go instances are saved on Uyuni database a mechanism to manage it needs to be provided.
Uyuni should have support to manage this data using the web UI or XML-RPC API.

Supported operations:
  - Remove ssh connection data
    - Associated data in `suseCredentials` and `susesccrepositoryauth` should also be removed
  - Update ssh connection data


# Drawbacks
[drawbacks]: #drawbacks

# Alternatives
[alternatives]: #alternatives

## Uyuni/SUSE manager pay-as-you-go

We could define a uyuni/suse manager pay-as-you-go image with access to all cloud RMT repositories.
It would be possible to syncronize any product directly from cloud in a more simple and straightforward way.
Drawbacks: User will have access to repository and product he is not paying for.

## Reposync only metadata

Change reposync and SCC to allow metadata access without SCC account to load repositories metadata.
Pay-as-you-go client could download data from cloud RMT server directly.
This will be a huge change, not sure if it is even possible to all providers.
Possible security impact of having repository metadata publicly accessible.

# Unresolved questions
[unresolved]: #unresolved-questions

- What happens and how to deal if the pay-as-you-go instance we loaded the data from get terminated or stopped?
  - Possible approach is remove the affected cloudrmt auth configs from the Server. Channels will be kept with all the existing content and assigned server will still see it. But no new updates will added to the channels.

- Should we have a UI showing all the pay-as-you-go authentications registered and allow user to remove existing ones?

- In case of multiple options, what should be preferred? I think it also depends on where Uyuni Server is running. If it is running in the cloud, the local RMT servers should be preferred, while if the Server is running outside of the Cloud, SCC should be preferred.
