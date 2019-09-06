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
    "my-amazon-us-east-2c": {
        "my-amazon-us-east-2c": {
            "name": "my-amazon-us-east-2c",
            "hostIdentifier": "my-amazon-us-east-2c",
            "ramMb": 0,
            "cpuArch": "aws",
            "cpuMhz": 0,
            "os": "Amazon AWS",
            "osVersion": "Amazon AWS",
            "totalCpuCores": 0,
            "totalCpuSockets": 0,
            "type": "aws",
            "vms": {
                "instance4": "i-fffcb2bd24b7b9",
                "instance5": "i-fffcb2bd24b7b11"
            }
        }
    }
}
```

All the attributes on the above JSON example are currently required by SUMA to properly create the entries on the DB. Since we don't know the real hardware used to virtualize the instances, those values like `ramMb`, `cpuMhz`, `totalCpuCores`, `totalCpuSockets` have been faked to 0.


## Add new Virtual Instance Types to the DB
New virtual instance types would be needed on the `rhnVirtualInstanceType` database table, these would be `azure`, `aws`, `gce` and `generic` to indicate the type of the instance.

Also, it's necessary to add new types of CPU Arch ("rhnCpuArch" DB table) and "Server Arch" ("rhnServerArch") to allow those new types of systems. We could adding one type per public cloud provider, i.a. aws, azure, etc, or maybe go with a generic type called `public_cloud`.

An important thing is to add the respective entry to `rhnServerServerGroupArchCompat` database table to allow `FOREIGN_ENTITLEMENT` to be assigned to these new architectures.

## Gather virtual instances and "instance id" from Public Clouds using API

Neither EC2, GCE or Azure expose the smbios "uuid" from the virtual instance through the public API, but instead they identify each instance using an "instance id" which is unique on that particular Public Cloud.

Examples:

- AWS EC2: i-1234567890abcdef0
- GCE: 152986662232938449
- Azure: 13f56399-bd52-4150-9748-7190aae1ff21

Since the `virtual-host-gatherer` would only deal with the public APIs, each virtual instance will be identified by its "instance id" on the JSON output from the `virtual-host-gatherer` execution. In order to properly match this "instance id" with the "uuid" of a registered system, this will need some ajustments as describer later on this RFC.

### Azure module:

TODO: Examples of how to deal with Azure API

The `vmId` reported from the API response corresponds with the "uuid" of the instance but might be swapped.

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

## Gathering the UUID (instance id) from virtual instances

For AWS and GCE, the instance id that is returned from the API is not actually the real "uuid" from the instance. On Azure, the instance id is an UUID but not necessary correspond with the SMBIOS "uuid" value we get from Salt.

An easy approach here would be to use the Instance ID (instead of smbios uuid) when registering a system which is a public cloud virtual instance. Salt currently does not provide the instance id as part of the grains but it would be really easy to provide a custom grain at the time of registration that would expose the "instance id" as part of the grains only when the system is an EC2, GCE or Azure instance. [Example here](https://gist.github.com/meaksh/1ed58ece0f26ce27a8445985de9ad6a2)

This way, doing some minor fixes on the Java side [Example here](https://github.com/meaksh/uyuni/commit/03d88550dd87d22f3fabd25cebd7c23432285a3c), we could easily use the "instance-id" as "UUID" for the registered system and automatically match it with the data provided by the `virtual-host-gatherer` plugin (which does not include "uuid" but instance id).

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
