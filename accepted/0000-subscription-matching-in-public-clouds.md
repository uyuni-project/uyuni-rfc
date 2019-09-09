- Feature Name: Subscription matching in public clouds
- Start Date: 2019-08-14
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

This RFC set the guides for supporting "Subscription Matching" on virtual instances created on Public Clouds like AWS, Azure or Google Compute Engine. Exploring and gatehering virtual instances from those Public Clouds enables "Subscription Matching" to properly match subscriptions for "1-2 Virtual Machines". In the context of Public Clouds, "Unlimited VMs" subscriptions are not allowed by T&C.

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

In the Public Cloud, the "region" is defined as de geographic location where the public cloud datacenter resides (like, US-East, Asia, US-West, etc). On the other hand, a "zone" represents an isolated location within a particular datacenter (region) where the cloud services originate and operate. i.a. "us-west-2a", "europe-west2-b", etc.

This means, all virtual instances that belong to the same "zone" (not region) will match with the "1-2 Virtual Machines" subscription.

## The output from a `virtual-host-gatherer` plugin:
The required output from a plugin is a JSON response to the STDOUT, that looks like the following:

```json
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

All the attributes on the above JSON example are currently required by SUMA to properly create the entries on the DB. Since we don't know the real hardware used to virtualize the instances, those values like `ramMb`, `cpuMhz`, `totalCpuCores`, `totalCpuSockets` have been faked to 0. As mentioned before, with some adaptations in the Java side we could not require those values (like for KUBERNETES).

NOTE: All the "vms" that belongs to the same "Virtual Host Manager", are considered in the same "Virtualization group" for subscription matching. In the case of Public Clouds, this means a different "Virtual Host Manager" needs to be added for each one of the "Zones" of the particular Public Cloud provider where we want gather virtual instances.

## Add new Virtual Instance Types to the DB
New virtual instance types would be needed on the `rhnVirtualInstanceType` database table, these would be `azure`, `aws`, `gce` and `generic` to indicate the type of the instance.

Also, it's necessary to add new types of CPU Arch ("rhnCpuArch" DB table) and "Server Arch" ("rhnServerArch") to allow those new types of systems. We could adding one type per public cloud provider, i.a. aws, azure, etc, or maybe go with a generic type called `public_cloud`.

An important thing is also to add the corresponding entry to `rhnServerServerGroupArchCompat` database table to allow `FOREIGN_ENTITLEMENT` to be assigned to any of these new architectures.

## Gather virtual instances and "instance id" from Public Clouds using API

Neither EC2, GCE or Azure expose the smbios "uuid" from the virtual instance through the public API, but instead they identify each instance using an "instance id" which is unique on that particular Public Cloud.

Examples:

- AWS EC2: i-1234567890abcdef0
- GCE: 152986662232938449
- Azure: 13f56399-bd52-4150-9748-7190aae1ff21

Since the `virtual-host-gatherer` would only deal with the public APIs, each virtual instance will be identified by its "instance id" on the JSON output from the `virtual-host-gatherer` execution. In order to properly match this "instance id" with the "uuid" of a registered system, this will need some ajustments as describer later on this RFC.

### Azure module:

This is an example about how to deal with Azure Public API to collect the virtual instances, using Azure Python SDK:

```python
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.resource import ResourceManagementClient, SubscriptionClient


# Tenant ID for your Azure Subscription
TENANT_ID = 'MY-TENANT-ID'

# Your Service Principal App ID
CLIENT = 'MY-CLIENT-ID'

# Your Service Principal Password
KEY = 'MY-SECRET'

credentials = ServicePrincipalCredentials(client_id = CLIENT, secret = KEY, tenant = TENANT_ID)
subscription_id = 'MY-SUBSCRIPTION-ID'
compute_client = ComputeManagementClient(credentials, subscription_id)

vmss = compute_client.virtual_machines.list_all()
for i in vmss:
    print(i.name)
```

The response contains the "instance name" as well as the "instance id".

### AWS module:

This is an example about how to deal with AWS EC2 Public API to collect the virtual instances on a particular Zone, using "boto3":

```python
import boto3
ec2 = boto3.client("ec2",
                   region_name='MY-REGION-NAME',
                   aws_access_key_id='MY-AWS-ACCESS-KEY-ID',
                   aws_secret_access_key='MY-AWS-ACCESS-KEY-SECRET')

response = ec2.describe_instances()
for i in response['Reservations']:
    for j in i['Instances']:
        print(j)
```

The response contains the "instance name" as well as the "instance id".

### Google Compute Engine module:

This is an example about how to deal with Google Compute Engine API to collect the virtual instances on a particular Zone, using "google-api-python-client":

```python
import googleapiclient.discovery

def list_instances(compute, project, zone):
    result = compute.instances().list(project=project, zone=zone).execute()
    return result['items'] if 'items' in result else None

    zone = 'MY-ZONE'
    project = 'MY-PROJECT-NAME'

    compute = googleapiclient.discovery.build('compute', 'v1')

instances = list_instances(compute, project, zone)
for i in instances:
    print(i)
```

The response contains the "instance name" as well as the "instance id".

### A generic JSON-file module:

Currently, there is already a "File based" plugin for `virtual-host-gatherer` which allows to import instances from a custom provided JSON file. According to the existing documentation, the aim of this plugin is to import VMware instances when there is no access from the SUSE Manager server to the VMware.

We can already use this plugin for importing virtual instances from the Public Cloud using a tailored JSON file like the one from the above example, so it would be worth to generalize the SUSE Manager documentation to expose this plugin as a general virtual instances importer and not as a VMware-specific.

# Drawbacks
[drawbacks]: #drawbacks

## Gathering the UUID (instance id) from virtual instances

For AWS and GCE, the instance id that is returned from the API is not actually the real "uuid" from the instance. On Azure, the instance id is an UUID but not necessary correspond with the SMBIOS "uuid" value we get from Salt.

An easy approach here would be to use the "Instance ID" (instead of smbios uuid) when registering a system which is a public cloud virtual instance. Salt currently does not provide the instance id as part of the grains but it would be really easy to provide a custom grain at the time of registration that would expose the "instance id" as part of the grains only when the system is an EC2, GCE or Azure instance. [Example here](https://gist.github.com/meaksh/1ed58ece0f26ce27a8445985de9ad6a2)

This way, doing some minor fixes on the Java side ([example here](https://github.com/meaksh/uyuni/commit/03d88550dd87d22f3fabd25cebd7c23432285a3c)), we could easily use the "instance-id" as "UUID" for the registered system and automatically match it with the data provided by the `virtual-host-gatherer` plugin (which does not include "uuid" but instance id).

In case of systems that are already registered in SUSE Manager using a smbios "uuid", if the new "instance_id" grain is there, it should be enough with scheduling a "Hardware Refresh" action to reflect the new "instance_id" grain value as the "uuid" for that system.

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
