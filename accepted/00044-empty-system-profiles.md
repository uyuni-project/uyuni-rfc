- Feature Name: Ability to add system profiles for system to be registered in the future
- Start Date: 2018-08-14
- RFC PR: TBD

# Summary
[summary]: #summary

SUSE Manager creates system profiles during system minion registration.
This RFC proposes a way to allow SUSE Manager to create system profiles before actual minion registration and then connecting existing system profile with minion during its registration.

# Motivation
[motivation]: #motivation

SUSE Manager for Retail requires some specific configuration for each minion serving as Retail Branch server. There can be hundreds of Branch servers and they may be geographically placed in various places with great challenges when setting up retail branch. For this scenario, previous product SLEPOS has ability to preconfigure Branch servers in database and the configuration and deployment of the Branch is matter of physical connection and providing proper login details.

This functionality is not available to SUSE Manager yet. This RFC proposes to solve this use case by allowing SUSE Manager to create "empty" system profiles before actual system 
registration using XMLRPC API. Then connect this existing "empty" profile with actual minion during its registration.

Existing "empty" profile then allows user to assign it various formulas, pillar data, entitlements (build host, etc) which will then be automatically available to newly registered 
minion and minion will be correctly configured once highstate is applied after successful registration and profile reconnection.

Even though primary interface for large Retail environment configuration is XMLRPC API, some UI design changes are later considered for better user experience.
Retail environment works only with Salt managed minions. For this reason I am not considering traditional entitlement at all.

# Detailed design
[design]: #detailed-design

There are two independent parts in this proposal:
* creation of "empty" system profiles
* matching and connecting "empty" system profile to real minion during its registration

## Matching strategies for system profile during minion registration

Since the matching of system profile to real minion directly affects the parameters of resulting XMLRPC API call this needs to be cleared first.

Considering Retail use case first, the primary method of matching is based on MAC address of the machine. This is based on information obtained from the field, where customers 
collects and knows this information before machines are actually deployed. Therefore they can use this information as an identification and should be generally unique.
Focusing solely on MAC address also simplifies the matching logic and can be eventually expanded later, if there is such a need, by creating overloaded XMLRPC API call.

As a result in current iteration only MAC addresses are considered.

Matching of empty profile and minion is done only after minion key is accepted. User is expected to do all sanity and security checks as in case of new minion registration to 
prevent profile mismatch, i.e. by MAC spoofing.

## Creating empty system profile

A XMLRPC call need to be added to the SUSE Manager.

This call will require authentication, require **system name**, optional **comment** and require at least one **network device** with its MAC address specified.
Technically **system name** may be optional as well and use MAC as a system name too.

As a suggestion, there is already a XMLRPC call `system.createSystemRecord` which concerns Cobbler records. In my practical experiments I created a `system.createSystemProfile` 
call as follows:

    /**
     * Creates a system record in database for a system that is not (yet) registered.
     * @param loggedInUser the currently logged in user
     * @param sysName name of the system profile
     * @param comment comment
     * @param mac MAC address of identifiable network interface
     * @return int - 1 on success, exception thrown otherwise.
     *
     * @xmlrpc.doc Creates a system record in database for a system that is not registered.
     * @xmlrpc.param #param("string", "sessionKey")
     * @xmlrpc.param #param("string", "sysName")
     * @xmlrpc.param #param("string", "comment")
     * @xmlrpc.param #param("string", "mac")
     * @xmlrpc.returntype #return_int_success()
     */

Implementation wise there are following possibilities how to store these empty profiles in the database:
* use new object derived from Server object (i.e. EmptyServer)

Having separate object for empty server is clean solution when comparing to Server object and SALT or other entitlement mix. However it may require much more code changes and I 
cannot foresee how intrusive they will be. These still will be issues to solve with FormulaFactory and filename to use for formula data.

* use Server object with BaseEntitlement BOOTSTRAP:

There are several required values to be provided for successful object creation. They are:

- system name
  provided as API call parameter
- organization to which this system belongs
  taken from user initiating API call
- creator
  taken from user initiating API call
- os and release
  because at the time of creating this information may not be known, some generic string is recommended e.g. unknown
- secret
  `RandomStringUtils.randomAlphanumeric(64)`
- autoupdate
  "N" taken from default minion registration handler
- contact method
  `ServerFactory.findContactMethodByLabel("default")`
- last boot time
  either current time or beginning of epoch to indicate system never booted
- architecture
  Retail use case supports only AMD64, so `ServerFactory.lookupServerArchByLabel("x86_64-redhat-linux")` should do the trick
- entitlement
  `EntitlementManager.BOOTSTRAP`, see below
- digital server id
  see below

In general, there are 2 alternatives for filling these:
1. Use some dummy values (os = 'Dummy OS')/values derived from the MAC address (`digitalServerId`)
2. Force the user to explicitly fill those in the API endpoint (so that they aren't surprise if they see weird values in the UI = MAC address)

### BOOTSTRAP entitlement

Server object with BOOTSTRAP entitlement has a benefit of requiring minimal code changes.
By default however BOOTSTRAP does not allow manipulation with Formulas and Groups. This can be solved by modifying ACLs in `java/code/webapp/WEB-INF/nav/system_detail.xml` file by 
adding `system_has_bootstrap_entitlement()` condition for Formulas and Groups tabs.
Enabling Formulas and Groups modifications to BOOTSTRAP entitlement systems can have some unforeseen consequences. It can be expected that in Retail environment, there can be 
hundreds of these kind of systems and user may try different management work on them. However exposure  of BOOTSTRAP systems to SUSE Manager features is quite limited by ACLs and 
entitlement checks lowering the risks.

### digitalServerID
Mandatory **digitalServerID** of Server object need to be somehow determined, in my experiments I used MAC address provided in XMLRPC API call.

This field appears to not have a clear usage and format in current SUSE Manager code. Known usages are:
- traditional clients uses it to store ID-$rhnServer.id
- salt minions uses it to store machineId
- foreign entitlements uses custom value (virtualization hosts)
- s390x uses custom value

Given the field attributes:
- it is NOT NULL, something need to be there anyway
- it is UNIQUE INDEX in the scheme already, uniqueness guaranteed and indexed for quick search
- it is VARCHAR2(1024), can handle MAC addresses as is

It is reasonable to assume this field is meant as general identifier of unique system and in this RFC I suggest to use it as is with the format of MAC address.
MAC address format is different enough not to be confused by any other usage. It should be generally unique. And it is small enough to fit **digitalServerID** length.

However this usage is basically some form of abuse of this field. Adding yet another usage format certainly does not help to clarify the situation. There are suggestions to fix 
this unclarity by removing **digitalServerID** field and replace it by individual field and indexes, depending on usage context (using **id** for traditional clients, 
**machineId** for minions, etc. In this case, there are two options how to proceed with MAC address storage:
- add hw_addr column + index
- use `rhnNetworkInterface` table and add index (additional drawback that it required device name to be stored as well, thus XMLRPC API call would need to be extended to include it)

In order not to duplicate the data in the database even more, let's use the `rhnNetworkInterface` table.

### FormulaFactory

Problematic is also the FormulaFactory object where it relies on **minionId** to name stored files. This field is however not available at the time of creation of empty profile. 
Solution is to use available data and that is MAC address. Either in form of using **digitalServerID** or one of the other methods used to store MAC address.

For the future reference, using of **minionId** in FormulaFactory is inconsistent with the rest of the stack and should be converted to one method (e.g. usage of **machineId** ), 
either in direct form, or indirectly through **digitalServerID**.

## Connecting empty system profile to registering minion

`RegisterMinionEventMessageAction` is where minion registration is happening. Two actions will need to happen in this place: finding previously created empty profile and updating possible formula and pillar data.

### find the empty profile using MAC address

When minion key is accepted, registration routine is started. During registration, handler is trying to find terminal using **machineId**, if unsuccessful it proceeds to create a 
new MinionServer object. This behaviour needs to be adapted to look for MAC address match. If the profile is found it needs to update its primary identifier to the correct on 
(e.g. in case **digitalServerID** usage this would need to be changed to **machineId** value) and all the other basic (i.e. **minionId** ) filled in. Then continue to update 
hardware and software details as is the case when new profile is created.
If profile is not found neither using **machineId** nor MAC address, new profile is created as in default SUSE Manager behaviour.

If Server object was used with SALT BaseEntitlement, then Server object should be converted to MinionServer using the same mechanism as traditional to salt client migration. Also 
entitlement must be changed to SALT.

### update formula and pillar data, salt state files

Formula and pillar data are stored in files named by **minionId**. Since before minion id is known, in previous step using MAC address was suggested. Now these formula and pillar 
files need to be renamed to use **minionId**. After rename, pillar data should be refreshed and salt external minion should be able to find correct pillars.

State files are stored using **machineId** variable. This variable is not known in empty profile, to allow states to be assigned to empty profile some workaround needs to be used, 
e.g. use **digitalServerID** as a filename. Then after minion registration, these files should be renamed to use **machineId**.

Finally, the **digitalServerId** field should be aligned to match the **machineId**, so that we are consistent with other minions.

## GUI changes

In Retail scenario it can be expected to have hundreds of empty profiles. This may in some way affect overall user experiences. It is suggested to create a new Systems folder for 
these empty profiles.

In case of using BOOTSTRAP entitlement, SUSE Manager already sort these empty profiles in `Unprovisioned systems` category.


# Drawbacks
[drawbacks]: #drawbacks

Enabling Formulas and Groups modifications to BOOTSTRAP entitlement systems can have some unforeseen consequences. It can be expected that in Retail environment, there can be 
hundreds of these kind of systems and user may try different management work on them.
However exposure  of BOOTSTRAP systems to SUSE Manager features is quite limited by ACLs and entitlement checks lowering the risks.

# Unresolved questions
[unresolved]: #unresolved-questions

## Usage of empty profiles to create an empty profile of salt based SUSE Manager Proxy.

Retail uses specific types of servers (Branch servers) which manages local network and also 
acts as a local salt proxy. Currently there seems to be no way how to trigger automatic proxy activation from SUSE Manager on certain minion.

## Salt state assignment to empty profiles

Branch server also synchronizes images from SUSE Manager to local storage. This functionality is provided by image-sync state. Ideally, in next development, when branch server 
empty profile is created, there is a possibility to attach salt state to be run after existing machine is provisioned and connected with its empty profile.

# Alternatives

## Using Activation keys for specifying empty profiles
In SUMA, there is already a way to define a system "shape" before it exists: Activation keys. With some additions, they could be used for the purposes of this RFC. They allow defining:
* SW channels (base + children)
* Add-On system types (e.g. `Container Build Host`)
* Contact method
* Configuration channels
* System groups

### Missing pieces
* Assigning formulas to activation keys (POC implemented - extending `FormulaFactory/Manager` doesn't seem to be hard)
* Binding activation keys with MAC address (or some other system attribute (general grains?)) and implementing the matching logic in the `RegisterMinionEventMessageAction`)

### The workflow
* The user creates an Activation key, assigns a MAC address and various configuration (e.g. Formulas) to it
* The system boots up, the `salt-minion` service is started up
* Minion `start` event is fired, if the system hasn't been registered yet, a new system profile is created based on an activation key, which can come from various places:
  * Web UI/XMLRPC API (user can specify an AK there)
  * Grain (`susemanager -> activation_key`)
  * **Lookup an AK based on associated MAC address**
* The newly created system profile gets all the assets from the activation key assigned

### The workflow - the saltbooted minion
In this case things get a little bit more complicated because:
* the saltboot has 2 phases (verify: the AK should be used in both of them (in the 1st one to assign the correct minion organization, in the 2nd one to assign remaining assets (Formulas...))), and
* the saltbooted minion in retail case contains some activation key in grains (since its image is typically built with SUMA Kiwi image building feature).

TODO, add the saltboot scenario.

### Advantages
* The concept of Activation keys has been used in SUMA for some time
* No cryptic `digitalServerId/machineId/minionId` adjustment
* UI and XMLRPC for handling Activation keys is present (minus the Formula/MAC address handling)

### Drawbacks
* Multiple Activation keys handling: what happens when there is an AK in grains, but the system MAC address also matches some Activation keys? Possible solutions:
  * The AK with MAC address would "win" (otherwise all systems would end up with AK from the built image (retail scenario))
  * Support multiple AKs? In the traditional scenario we had that, we'd need to revisit it.
* UI filtering for the systems is much better (grouping systems by system group provides a better overview)
* Multiple API endpoints for configuring system (for not-existing systems user must use the AK API/UI, for existing systems, user uses the Systems API/UI)

