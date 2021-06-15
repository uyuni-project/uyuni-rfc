- Feature Name: Mirror PTF repositories in Uyuni
- Start Date: 2021-05-17

# Summary
[summary]: #summary

SUSE want to provide customers PTFs (Product Temporary Fixes) in repositories.
Uyuni should be able to offer these repositories as channels for syncing and management.

# Motivation
[motivation]: #motivation

PTFs are Product Temporary Fixes for Service Requests opened by SUSE customers.
The resulting packages are the last released maintenance update plus a patch which fixes the actual issue.

PTFs are made for dedicated customers. This means every customer has different PTF repositories, with different content and fixes for different service requests.

With Uyuni we should provide the possibility to mirror the content of these repositories and let the customer use it for there clients.


# Detailed design
[design]: #detailed-design

## How to generate the Channels from the SCC Data

The mapping of SCC repositories to Uyuni Channels is done via a prepared product tree file which contains the definitions for all products and its repositories.
It enhances the information from SCC with values required for Uyuni.

Such an entry is defined by 3 values:

- the scc product id
- the scc product id of the root product
- the scc repository id

The following values are set by the product tree:

- channel label: it must be unique on the whole Uyuni Server
- parent channel label: what is the parent of this channel
- channel name: similar to channel label but human readable
- update tag: a special value to modify the errata id during import [1]
- mandatory: defines if this channel is required for the product it belongs to

As PTF repositories are customer specific, such a hard coded definition cannot 
be provided upfront.
They must be generated out of existing data.

As SCC needs to crawl the buildservice to find all the existing PTF repositories, they agreed on a path structure to map the repositories to the products.
The defined path is:

    PTF/Release/<Customer Account ID>/<Product Identifier>/<Product Version>/<Product Architecture>/ptf[_debug]/

When Uyuni is listing the repositories available for an organizations, it may find repositories which `id` is not known in the complete product tree.
To identify them as PTF repositories we can check if the path start with `PTF/Release`.

If they are PTF repositories, we need to generate the missing values for the Channel mapping like this:

- scc repository id: take it from the repository definition
- scc product id: search for the product using `Product Identifier`, `Product Version`, and `Product Architecture` like specified in the URL
- scc root product id: find all existing root products for the product id. We need to generate an entry for all of them

The values for update tag and mandatory can be hard coded as they are the same 
for all PTF repositories.

- update tag: empty [1]
- mandatory: false

As PTF repositories do not get patches, an update tag is not needed.
The mandatory flag should be `false` as PTF repositories should only be used when needed.

As we need to generate entries for all existing root products we can iterate over all we found.
For every root product we take the first channel we can find which does have a `parent channel label` set.
We can take this as parent channel label for our new entry.

As the channel label and name must be unique.
We can generate the label and name from the URL components:

    <Customer Account ID> <Product Identifier> <Product Version> "PTFs" ["Debuginfo"] <Product Architecture>

The label is computed using the lowercase components joined with a dash ("-") and the name just joined with a space (" ").

This can either be done by Uyuni Server or SCC. In case SCC use this algorithm it could set it as `repository name`
joined with a dash ("-") and in `repository description` using spaces.

The product tree uses additional suffixes for products which belongs to multiple root products to make label and name unique.
The suffix is appended always after the architecture of the channel label.
We can parse it from the entry we used to find the `parent channel label` and use it to enhance the component list.


## Test Package Channels

Before generating PTFs, SUSE will first create so called TEST packages.
The customer need to test them and report positive result before SUSE make an official supported PTF out of it.

TEST packages should only be installed on dedicated test systems.
Therefor it is important that they get not installed on any system where just the version of the TEST package is higher than the installed one.

Current idea is, that TEST packages will go into a different channel. Probably the last directory will be names "test" and "test_debug".
We would use the same rules as for PTF Channels and adjust the name and label.


# Drawbacks
[drawbacks]: #drawbacks

- we are guessing the values. Some, like the channel label, are sensitive and must not be changed. We have to be sure that the rules and the structure never changes.
- ptf handling for non SUSE OSes will not be as nice as for SUSE OSes.

# Alternatives
[alternatives]: #alternatives

Stop using product unscoped SCC endpoint and use the product scope of the requesting organization. In this endpoint we see the PTF repositories directly with its ids.
SCC needs to be adapted to provide the channel labels and names directly in its API.

Downside:

- when multiple organization credentials are used, we need to request and parse multiple product scopes which cost much more time.
- we might need to do bigger changes in the backend as we need to adapt to getting only parts of the data.
- dependency to other product development teams. Requires agreements to change other products as well

# Unresolved questions
[unresolved]: #unresolved-questions

- None so far

# Appendix
[appendix]: #appendix

1. Update Tag

When SUSE starts an incident which requires a patch, the developer submit the affected package sources to the buildservice.
They get build under an (internal) incident id. After QA, when the fix should be released it could happen that multiple update channels are affected.
Example "salt":

- salt, salt-minion, ... belongs to sle-module-basesystem15-SP2-Updates
- salt-master, salt-api, ... belongs to sle-module-server-application15-SP2-Updates.

But the `id` in the updateinfo (patch) must be unique. The buildservice has for every release channel an id_template configured which take care for making it unique.
The id_templates for this example are defined as:

- `SUSE-SLE-Module-Basesystem-15-SP2-%Y-%C`
- `SUSE-SLE-Module-Server-Applications-15-SP2-%Y-%C`

where `%Y` will be exchanged with the current Year and `%C` is a counter.
It is guarantied that the counter result in the same number for one incident.

When Uyuni now import the patches from different channels we could import them as single patches.
This would result in a lot more patches in the DB as really exists and it could happen that users clone/use only "parts" of a fix if they select only 1 and not all for the action they want to do.

The update tag identifies the part of the ID Template which make it unique and try to "rollback" the split made by the buildservice when releasing the patch.
The Update Tag in the example case are:

- SLE-Module-Basesystem
- SLE-Module-Server-Applications

During reposync this part is cutted away from the ID. Both patches would end up with the ID `SUSE-15-SP2-%Y-%C`.
The reposync process search in the DB if an errata with this ID already exists.
If yes, it merges the details together. In the DB we have now only 1 errata.

When we re-generate the metadata, we add the update tag again to the resulting updateinfo metadata.

This explains also why the "update tag" must not change.
If it would change we cannot find already imported errata and would duplicate everything.

