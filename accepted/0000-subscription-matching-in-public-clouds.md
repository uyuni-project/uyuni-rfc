- Feature Name: Subscription matching in public clouds
- Start Date: 2019-08-14
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

This RFC set the guides for supporting "Subscription Matching" on virtual instances created on Public Clouds like AWS, Azure or Google Compute Engine. Exploring and gatehering virtual instances from those Public Clouds enables "Subscription Matching" to properly match subscriptions for "1-2 Virtual Machines".

# Motivation
[motivation]: #motivation

Currently the subscription matcher does not work for VMs that are running in public clouds. Our `virtual-host-gatherer` tool doesn't support exploring those public clouds, so there is no effective way to provide the needed information that makes subscription matcher be aware of the virtualization environments and therefore match the subscription and benefits from "1-2 Virtual Machine" licencing.

This RFC defines the procedures to enabling "Subscriptions Matching" on different Public Clouds providers.

Also provides implementation details for implementing the following modules for `virtual-host-gatherer`:

- A generic (JSON-file based) module that enables Administrators to provide its own custom virtual instances definition.
- A module for gathering virtual instances from Azure Cloud.
- A module for gathering virtual instances from AWS.
- A module for gathering virtual instances from Google Compute Engine.

This way, the Administrators will be able to define and/or gather their virtualization environments in the public clouds and make the subscription matcher do a succesfull matching of the "1-2 Virtual Machine" subscriptions.

# Detailed design
[design]: #detailed-design

Most of the implementation effort needed is about coding each one of the needed plugins for `virtual-host-gatherer`. On the Java side, we would need to adapt `VirtualHostManagerProcessor.java` and most probably also `VirtualInstanceManager.java` in a similar way that we do when processing a KUBERNETES virtual host, since we don't always know about amount of RAM, number of CPUs, etc from the Virtualization Host.


## 1-2 Virtual Machine Licensing
From [SUSE Terms & Conditions](https://www.suse.com/products/terms_and_conditions.pdf):

> Up to 2 Virtual Machines running on the same Virtualization Host or Virtualization Environment or within the same Private Cloudaccount or **Public Cloud zone can be deployed with one "1-2 Sockets or 1-2 Virtual Machines" Subscription Offering**.


## The output from a `virtual-host-gatherer` plugin:
The required output from a plugin is a JSON response to the STDOUT, like the following

```
{
    "my-amazon-ec2-region-X": {
        "tendancy1": {
            "hostIdentifier": "tenancy1",
            ...
            "type": "aws",
            "vms": {
                "my-aws-instance-1": "564d6d90-459c-2256-8f39-3cb2bd24b7b0"
            }
        },
        "tenancy2": {
            "hostIdentifier": "tenancy2",
            ...
            "type": "aws",
            "vms": {
                "my-aws-instance-2": "4230c60f-3f98-2a65-f7c3-600b26b79c22",
                "my-aws-instance-3": "4230b00f-0b21-0e9d-dfde-6c7b06909d5f",
                "my-aws-instance-4": "4230e924-b714-198b-348b-25de01482fd9"
            }
        }
    }
}
```
TODO: Complete the example JSON to add all attributes required from the Uyuni database.

NOTE: All "vms" that belongs to the same virtual-host-manager, in the above example "my-amazon-ec2-region-X", regarding its tenancy, they all will be considered in the same virtualization group.

## Add new Virtual Instance Types to the DB
New virtual instance types would be needed on the `rhnVirtualInstanceType` database table, these would be `azure`, `aws`, `gce` and `generic` to indicate the type of the instance.


## Gather instances and "uuid" from Public Clouds using API

### Azure module:

TODO: Examples of how to deal with Azure API

The `vmId` reported from the API response corresponds with the "uuid" of the instance.

### AWS module:

TODO: Examples of how to deal with AWS API

The `instanceId` returned from the API is **NOT** the "uuid", on this particular module, we could get the corresponding "uuid" from an "uuid" instance tag that needs to be set before in order to this module to incorporate this instance into the generated output.

### Google Compute Engine module:

TODO: Examples of how to deal with GCE API

In the case of GCE, the instance id is **NOT** the "uuid" so we need to also to gather the "uuid" from a previously store "uuid" on the instanceMetadata.

### A generic JSON-file module:

TODO: Describe generic module

# Drawbacks
[drawbacks]: #drawbacks

## Gathering the UUID for the virtual instances

For AWS and GCE, the instance id that is returned from the API is not actually the real "uuid" from the instance. In order to get it, it would be previously needed to store that "uuid" on the metadata/tags for each instance.

TODO: Evaluate if the "uuid" could be stored from within the instance into the "instanceMetadata" / "instanceTags" using the internal API available for the instances. That way, an automate action could be executed on the registered instances to store this information and then have it available when running `virtual-host-gatherer`.

# Alternatives
[alternatives]: #alternatives

### Use special "System Grouping" and do not use `virtual-host-gatherer`:
This alternative approach will be based on implementing an special "System Groups" where Administrators could define their virtualization enviroments and set the systems that belong to those groups.

Pros:
- All virtual environments are defining via grouping. No need to actually reach the Public Clouds, no external APIs.

Cons:
- These virtualization groups need to be defined manually. No way of automation.
- Refreshing the state of a virtualization group also needs to be done manually.
- Require new DB tables and UI for managing those groups.

# Unresolved questions
[unresolved]: #unresolved-questions
