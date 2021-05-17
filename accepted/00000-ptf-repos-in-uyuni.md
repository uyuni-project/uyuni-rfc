- Feature Name: PTF repositories in Uyuni
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

The mapping of SCC repositories to Uyuni Channels is done via a prepared product tree file which contains the definitions for all products and its repositories.
It enhances the information from SCC with values required for Uyuni.

Such an entry is defined by 3 values:

- the product id
- the product id of the root product
- the repository id

The following values are set by the product tree:

- channel label: it must be unique on the whole Uyuni Server
- parent channel label: what is the parent of this channel
- channel name: similar to channel label but human readable
- update tag: a special value to modify the errata id during import
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

- repository id: take it from the repository definition
- product id: search for the product using `Product Identifier`, `Product Version`, and `Product Architecture` like specified in the URL
- root product id: find all existing root products for the product id. We need to generate an entry for all of them

The values for update tag and mandatory can be hard coded as they are the same 
for all PTF repositories.

- update tag: empty
- mandatory: false

As we need to generate entries for all existing root products we can iterate over all we found.
For every root product we take the first channel we can find which does have a `parent channel label` set.
We can take this as parent channel label for our new entry.

As the channel label and name must be unique.
We generate the label and name from the URL components:

    <Customer Account ID> <Product Identifier> <Product Version> "PTFs" ["Debuginfo"] <Product Architecture>

The product tree uses suffixes for products which belongs to multiple root products to make label and name unique.
The suffix is appended always after the architecture of the channel label.
We can parse it from the entry we used to find the `parent channel label` and use it to enhance the component list.

The label is computed using the lowercase components joined with a dash ("-") 
and the name just joined with a space (" ").

# Drawbacks
[drawbacks]: #drawbacks

- we are guessing the values. Some, like the channel label, are sensitive and must not be changed. We have to be sure that the rules and the structure never changes.

# Alternatives
[alternatives]: #alternatives

Stop using product unscoped SCC endpoint and use the product scope of the requesting organization. In this endpoint we see the PTF repositories directly with its ids.
SCC needs to be adapted to provide the channel labels and names directly in its API.

Downside:

- when multiple organization credentials are used, we need to request and parse multiple product scopes which cost much more time.
- we might need to do bigger changes in the backend as we need to adapt to getting only parts of the data.
- dependency to other product development teams which slow down the development

# Unresolved questions
[unresolved]: #unresolved-questions

- None so far
