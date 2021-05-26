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

## General PTF design

A ptf release consists of multiple rpm packages plus one
master "ptf" package. The master ptf package has two
purposes:

- it allows to easily query which ptfs are installed
  in the system
- it makes sure that all of the installed rpm packages
  come from the same release, i.e. there is no mix up
  between multiple releases are non-ptf package

To do this the master ptf package contains the following
elements (incident 1234, first release):

    Name: ptf-1234
    Version: 1
    Release: 1                 # always 1
    Provides: ptf() = 1234-1
    Requires: (pkg1 = pkg1EVR if pkg1)
    Requires: (pkg2 = pkg1EVR if pkg2)
    ...

I.e. if pkg1 is installed it must be installed with version
pkg1EVR. (We do not use Conflict: pkg1 != pkg1EVR because that
would not work with multiversion packages like the kernel.)

All packages providing ptf() get blacklisted by the solver,
meaning they can only be installed by a specific solver job
that addresses them. This means that selecting a specific
ptf master package via yast or "zypper in" works, but they
can not be pulled in via dependencies.

Each individual rpm package must require the specific
master ptf package:

    Name: pkg1
    Requires: ptf-1234 = 1-1

This makes sure that the solver cannot pull in the rpm
packages, as that would mean to also pull in the blacklisted
master ptf package.


### Updates

Ptfs can be updated to a new release by calling 'zypper up'.
This will update the master ptf package to some higher
version (e.g. ptf-1234 = 2-1) and also pull in the corresponding
rpm packages.


### Uninstalling ptfs

'zypper rm ptf-1234' will uninstall the ptf and revert back to
non-ptf packages.


### Making sure that no fixes are lost

If all of the bugs fixed by a ptf are also fixed in maintenance
updates, a new ptf release consisting only of the master ptf
package is done:

    Name: ptf-1234
    Version: 3
    Release: 1                 # always 1
    Provides: self-destruct-pkg()
    Requires: (pkg1 >= maintpkg1EVR if pkg1)
    Requires: (pkg2 >= maintpkg2EVR if pkg2)

Updating to this version will make sure that this system will
contain only the fixed packages from the maintenance updates.
The special "self-destruct-pkg()" provides will tell the
solver that this will be a package erase instead of an
install. This means that installing this package will actually
erase the master ptf package.

### Test Packages

Before generating PTFs, SUSE will first create so called TEST packages.
The customer need to test them and report positive result before SUSE make an official supported PTF out of it.

TEST packages should only be installed on dedicated test systems.
Therefor it is important that they get not installed on any system where just the version of the TEST package is higher than the installed one.


## PTFs with Uyuni for SUSE and non SUSE OSes

The general PTF design has 3 key points.

1. A new ptf package to install the PTF.
   
   The "boolean dependencies" are supported in `rpm` since version 4.13.
   This would work for SLE15+ and RHEL8+.
   Other OSes needs a different solution.
   
   While SUSE is working on ideas which might cover SLE12, there might be no solution for non SUSE OSes.
   This topic is only valid for SUSE Manager shipping Client Tools (e.g. salt) for RHEL, Ubuntu and Debian.
   We could just use normal hard dependencies without checking if the package is installed. In most cases
   there are no optional packages involved which might or might not be installed.

2. "All packages providing ptf() get blacklisted by the solver"
   
   This will not be the case for non SUSE operating system.
   For SUSE operating systems this will work on solver level, but not in the Uyuni Web UI.
   
   One possible solution could be, that we check for the special provides Header of packages and keep them away from calculation for possible update candidates.
   Something similar is done for ["Retracted Patches"](https://github.com/uyuni-project/uyuni-rfc/blob/master/accepted/00074-retracted-updates-support.md) already.
   
   Another idea is to provide special CLM filter together with a best practice docs. This should be handled in a separate RFC.

3. "Self destructing Packages"
   
   While on SUSE OSes this would work out of the box, we need to implement something for non SUSE OSes.
   We could write a state which automatically uninstall all packages which `Provides: self-destruct-pkg()`.
   This would be limited to salt managed systems, but keeping a ptf package installed is not a problem.
   This is just a cleanup step which is not strictly required.


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

