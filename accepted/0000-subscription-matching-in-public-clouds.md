- Feature Name: Subscription matching in public clouds
- Start Date: 2019-08-14
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

This RFC set the guides for supporting "Subscription Matching" on virtual instances created on Public Clouds like AWS, Azure or Google Compute Engine. Exploring and gatehering virtual instances from those Public Clouds enables "Subscription Matching" to properly match subscriptions for "1-2 Virtual Machines". In the context of Public Clouds, "Unlimited VMs" subscriptions are not allowed by the "[Terms & Conditions](https://www.suse.com/products/terms_and_conditions.pdf)".

# Motivation
[motivation]: #motivation

Currently the subscription matcher does not work for VMs that are running in public clouds. Our `virtual-host-gatherer` tool doesn't support exploring those public clouds, so there is no effective way to provide the needed information that makes subscription matcher be aware of the virtualization environments and therefore match the subscription and benefits from "1-2 Virtual Machine" licencing.

This RFC defines the procedures to enabling "Subscriptions Matching" on different Public Clouds providers.

Also provides implementation details for supporting the following modules for `virtual-host-gatherer`:

- A generic (JSON-file based) module that enables Administrators to provide its own custom virtual instances definition.
- A module for gathering virtual instances from Azure Cloud.
- A module for gathering virtual instances from AWS.
- A module for gathering virtual instances from Google Compute Engine.
- A generic Public Cloud module based on Apache Libcloud (support for multiple Public Clouds).

This way, the Administrators will be able to define and/or gather their virtualization environments in the public clouds and make the subscription matcher do a succesfull matching of the "1-2 Virtual Machine" subscriptions.

# Detailed design
[design]: #detailed-design

Most of the implementation effort needed is about coding each one of the needed plugins for `virtual-host-gatherer`. On the Java side, an alternative is to fake some info provided by the gatherer since we don't know really about some details of the Public Cloud node: like "CPUArch", "RAM", "number of CPU" and some others. On the other hand, an adaptation could be done in `VirtualHostManagerProcessor.java` and most probably also `VirtualInstanceManager.java` in a similar way that we do when processing a KUBERNETES virtual host, to not require those values when creating the information about the nodes (foreign hosts):

- Implement different Public Cloud providers plugins for `virtual-host-gatherer` as detailed later on this RFC.
- Modify the Java side to allow "nodes" (`FOREIGN` hosts) that doesn't contains "RAM", "number CPU", "Mhz", etc (as currently required and described later on the example JSON). (optional)
- Add a generic `cloud` CPUArch/ServerArch value to allow "nodes" from Public Cloud where we don't know the architecture. Allow `FOREIGN_ENTITLEMENT` for it.
- Generalize the documentation about File-based Virtual Host Manager to extend it to the Public Cloud usage [link to doc](https://www.suse.com/documentation/suse-manager-4/4.0/suse-manager/client-configuration/virt-file.html)


## 1-2 Virtual Machine Licensing
From [SUSE Terms & Conditions](https://www.suse.com/products/terms_and_conditions.pdf):

> Up to 2 Virtual Machines running on the same Virtualization Host or Virtualization Environment or within the same Private Cloudaccount or **Public Cloud zone can be deployed with one "1-2 Sockets or 1-2 Virtual Machines" Subscription Offering**.

In the Public Cloud, the "region" is defined as de geographic location where the public cloud datacenter resides (like, US-East, Asia, US-West, etc). On the other hand, a "zone" represents an isolated location within a particular datacenter (region) where the cloud services originate and operate. i.a. "us-west-2a", "europe-west2-b", etc.

This means, all virtual instances that belong to the same "zone" (not region) will match with the "1-2 Virtual Machines" subscription.

## The output from a `virtual-host-gatherer` plugin:
The required output from a plugin is a JSON response to the STDOUT, that would look like the following:

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

All the attributes on the above JSON example are currently required by SUMA to properly create the entries on the DB. Since we don't know the real hardware used to virtualize the instances (node info), those values like `ramMb`, `cpuMhz`, `totalCpuCores`, `totalCpuSockets` have been faked to 0. As mentioned before, with some adaptations in the Java side we could not require those values (similar to the KUBERNETES case).

NOTE: All the "vms" that belongs to the same "Virtual Host Manager", are considered in the same "Virtualization group" for subscription matching. In the case of Public Clouds, this means a customer needs to add a different "Virtual Host Manager" in SUSE Manager for each one of the "zones" of the particular Public Cloud provider where customer wants to gather virtual instances. The "Terms & Conditions" explicitly mentions grouping by "Public Cloud zone" (and not account). Therefore, a customer using i.a. AWS will need to create as many "Virtual Host Manager" on SUSE Manager as "zones" they want to gather. Then each one of those "Virtual Host Manager" is considered as independent Virtualization Group for "1-2 subscriptions" matching.

## Add new Virtual Instance Types to the DB
New virtual instance types would be needed on the `rhnVirtualInstanceType` database table, these would be `azure`, `aws` and `gce` to indicate the type of the instance.

Also, keep in mind that on Public Clouds we don't really know the architecture of the node that is running the Virtual Instances (we only know the arch of the VM itself) so it might be necessary to add new types of CPU Arch ("rhnCpuArch" DB table) and "Server Arch" ("rhnServerArch") to allow those new types of systems. We could add one type per public cloud provider, i.a. aws, azure, etc, or maybe go with a generic type called `cloud`.

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

### A generic LibCloud based module:

The [Apache libcloud](https://libcloud.readthedocs.io/en/latest/index.html) library allows to deal with different Public Cloud providers using a common interface. Currently it supports EC2, Azure, GCE amount other providers, so this would allow to not only support EC2, Azure and GCE but also any other Public Cloud provider.

The idea here would be to create a generic `libcloud` plugin for `virtual-host-gatherer` that would received the selected provider and the necessary authentication parameters. Then, the plugin would use a common interface to gather the instances.

Resquirements:

- Provide a map between "provider" -> "authentication parameters".
- A dynamic form in the UI (based on the selected Public Cloud provider from a SelectBox) to ask for the necessary credentials that this provider requires.

Example of gathering instances using libcloud using for different providers. Notice that each provider requires different authentication parameters, but the interface is common (`driver.list_nodes()`).

```python
#-*- coding: utf8 -*-

# AWS related variables
AWS_ACCESS_KEY_ID = "EXAMPLE"
AWS_SECRET_ACCESS_KEY = "EXAMPLE"
AWS_REGION = "us-east-2"

# Azure related variables
AZURE_SUBSCRIPTION_ID = "EXAMPLE"
AZURE_APPLICATION_ID = "EXAMPLE"
AZURE_TENANT_ID = "EXAMPLE"
AZURE_SECRET_KEY = "EXAMPLE"

# GCE related variables
GOOGLE_SERVICE_ACCOUNT_EMAIL = "EXAMPLE"
GOOGLE_CERT_PATH = "/foo/bar/example.json"
GOOGLE_ZONE = "us-central1-a"
GOOGLE_PROJECT_ID = "EXAMPLE"

# Import
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

# List Google Compute Engine virtual machines
cls = get_driver(Provider.GCE)
driver = cls(GOOGLE_SERVICE_ACCOUNT_EMAIL, GOOGLE_CERT_PATH, datacenter=GOOGLE_ZONE, project=GOOGLE_PROJECT_ID)
nodes = driver.list_nodes()
print ("Listing Google Compute Engine virtual machines...")
for node in nodes:
    print ("{} - {} - {}".format(node.id, node.name, node.state))
print()

# List AWS virtual machines
cls = get_driver(Provider.EC2)
driver = cls(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, region=AWS_REGION)
nodes = driver.list_nodes()
print ("Listing AWS virtual machines...")
for node in nodes:
    print ("{} - {} - {}".format(node.id, node.name, node.state))
print()

# List Azure virtual machines
cls = get_driver(Provider.AZURE_ARM)
driver = cls(tenant_id=AZURE_TENANT_ID, subscription_id=AZURE_SUBSCRIPTION_ID,
             key=AZURE_APPLICATION_ID, secret=AZURE_SECRET_KEY)
nodes = driver.list_nodes()
print ("Listing Azure (classic) virtual machines...")
for node in nodes:
    print ("{} - {} - {}".format(node.id, node.name, node.state))

```

It's also interesting that "libcloud" also provides information about the "Princing" of each Public Cloud provider. This means, it allows us to think in estimating and optimizing infrastructure costs. Of course, this would require a different RFC in the future.

### A generic JSON-file module:

Currently, there is already a "File based" plugin for `virtual-host-gatherer` which allows to import instances from a custom provided JSON file. According to the existing documentation, the aim of this plugin is to import VMware instances when there is no access from the SUSE Manager server to the VMware. [link to doc](https://www.suse.com/documentation/suse-manager-4/4.0/suse-manager/client-configuration/virt-file.html)

We can already use this plugin for importing virtual instances from the Public Cloud using a tailored JSON file like the one from the above example, so it would be worth to generalize the SUSE Manager documentation to expose this plugin as a general virtual instances importer and not as a VMware-specific.

## Gathering the UUID (instance id) from virtual instances

For AWS and GCE, the instance id that is returned from the API is not actually the real "uuid" from the instance. On Azure, the instance id is an UUID but not necessary correspond with the SMBIOS "uuid" value we get from Salt.

An easy approach here would be to use the "Instance ID" (instead of smbios uuid) when registering a system which is a public cloud virtual instance. Salt currently does not provide the instance id as part of the grains but it would be really easy to provide a custom grain at the time of registration that would expose the "instance id" as part of the grains only when the system is an EC2, GCE or Azure instance. [Example here](https://gist.github.com/meaksh/1ed58ece0f26ce27a8445985de9ad6a2)

This way, doing some minor fixes on the Java side ([example here](https://github.com/meaksh/uyuni/commit/03d88550dd87d22f3fabd25cebd7c23432285a3c)), we could easily use the "instance-id" as "UUID" for the registered system and automatically match it with the data provided by the `virtual-host-gatherer` plugin (which does not include "uuid" but instance id).

In case of systems that are already registered in SUSE Manager using a smbios "uuid", if the new "instance_id" grain is there, it should be enough with scheduling a "Hardware Refresh" action to reflect the new "instance_id" grain value as the "uuid" for that system.

# Drawbacks
[drawbacks]: #drawbacks

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
- Most probably no customer would maintain these data.

# Unresolved questions
[unresolved]: #unresolved-questions

- This approach is based on matching only Salt virtual instances. Should we also change the reported "uuid" for Traditional Clients running on the Public Cloud?
