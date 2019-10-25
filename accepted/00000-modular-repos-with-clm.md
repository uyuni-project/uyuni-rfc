- Feature Name: Modular Repositories with CLM
- Start Date: 2019-10-23
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

Implement additional functionality on top of content lifecycle management to be able to build regular repositories out of modular repositories.

Design additional CLM "module" filters to let the user pick desired modules and streams.

# Motivation
[motivation]: #motivation

RHEL/CentOS 8 inherits a new concept of [modularity and modular repositories](https://docs.fedoraproject.org/en-US/modularity/).
Modularity allows different major versions (streams) to coexist in a single repository.
Users enable/disable streams so that there is only a single stream of a module is visible to the package manager at once.

Modular repositories are defined in a new type of metadata called `modulemd` in a file named `modules.yaml`. This metadata has to be interpreted properly to manage these repositories.
Unless this metadata is handled, managing modular repositories causes problems with package operations, specifically, suggesting incorrect package updates in the UI.

Currently, Uyuni has only the most basic support for modularity by displaying the following message in the package management UI:
```
At least one of the channels this system is subscribed to contains modules. If you have activated modules on this system, please refrain from using Spacewalk for package operations. Instead, perform all package actions from the client using dnf.
```

The goal is to handle modular repositories in a way that the clients can be still managed through the Uyuni UI.

# Detailed design
[design]: #detailed-design

## Overview

Instead of implementing the modularity logic inside the core of Uyuni, this document describes a design to simulate the modularity behavior by building regular repositories out of modular repositories by filtering out packages from unselected streams.
The resulting repository is a "flat" repository with no modularity, so it can be managed with Uyuni's existing package operations logic.

Conceptually, a module can be in one of the following three states at any time:
 - Enabled
 - Disabled
 - Neither enabled nor disabled

When a module is neither enabled nor disabled, all the alternative streams and contexts of a stream are available to the package manager. This state confuses Uyuni when comparing the package versions.

The key to building a regular repository with no conflicting packages is to simulate the modules in a way that every single module is either "enabled" or "disabled".

Therefore, the high-level algorithm is proposed as:
 1. Let the users pick desired streams so that every module is either "enabled" or "disabled"
 2. Compile a blacklist of RPM artifacts from the "disabled" modules
 3. Generate a "regular" repository, filtering out the blacklisted RPMs

The design utilizes content lifecycle management filters and repository building capabilities to implement the algorithm above.

## Components

This section summarizes the different components involved in the design.

### Backend
The Java backend is responsible for filtering out unselected module streams and building the repository with the desired packages through CLM.

### API
A Python API parses and interprets the module metadata, resolves modular dependencies and translates specified modules and streams to an actual package list.
The API utilizes the Python port of [libmodulemd](https://github.com/fedora-modularity/libmodulemd), which is used for structural parsing of `modules.yaml` files.

An example of such implementation is provided in [attachments/00000-modular-repos-api.py](attachments/00000-modular-repos-api.py).

### UI
The UI consists of a new type of CLM filter called "module". The filter provides inputs for a module name and a stream name.
Each filter selects a stream for a single module. The stream input can be left empty to select the default stream.
Since a CLM filter is not related to any channels, it is not possible to display a list of modules/streams on the filter form and the inputs can only be simple text inputs.
The module information for a modular repository is displayed under an additional "Modules" tab on the "Channel Details" page.
A modular repository is indicated with an icon next to the name of the repository in the CLM sources list. A click on the icon navigates to the "Modules" tab of the channel details.

## The Process

This section describes the detailed design for the different phases of a CLM project.

### Project setup
At the project setup, the backend checks if any of the sources are modular repositories.
This check is done by doing a `getChannel().getModule()` call on the source object.
For every modular source, a proper indicator is displayed as described in the UI component section.

Currently, every CLM filter displays a field to choose one of two hard-coded rules: `allow` or `deny`. For module filters, this field must be hidden.
Each added module filter stores the value of a chosen module/stream in `name` or `name:stream` format.

*There is no API communication required during the project setup phase.*

### Build/promote
At build time, all the module filter values are read in the form of `name:stream` tuples or only `name` in case the default stream is chosen.
With a list of name/stream tuples, the API is called to resolve the modular dependencies and the appropriate contexts (see next section).
If successful, the API returns a list of full RPM names belonging to all the enabled streams.
Additionally, the backend retrieves a full list of all the modular RPMs and subtracts the enabled ones from this list. The resulting list is translated into corresponding `Package` objects.
This list is then filtered out in a way similar to the package filters.

### Modular dependency and context resolution
Module metadata includes information about "modular dependencies" where a module is dependent on another module.
Moreover, in modular repositories, a "context" depicts a variation of the module which is built against some specific set of dependencies. Multiple contexts for a module means that there are multiple variations of the module available that are built against a different set of dependencies. The context value of a stream is a hexadecimal hash of some fundamental metadata fields including the stream's dependencies.

The API resolves the dependencies and the proper context values using [libmodulemd](https://github.com/fedora-modularity/libmodulemd).

**Input:**
 - A list of `modules.yaml` file locations from every modular source, to be merged and loaded into `libmodulemd`
 - A list of `(name, stream)` tuples gathered from the module filters

**Output:**
 - A map of package names to lists of RPMs provided by the enabled modules

The API picks the right `(name, stream, context)` tuples using the following algorithm for each selected module:
 1. Get all dependencies from every available context of the stream
 2. For every dependency, collect the default stream or the enabled stream if there is one
 3. Find a context where all of its dependencies are in the collected dependency list
 4. Recurse into the default non-enabled dependencies to enable them
 5. Enable the stream with the context found earlier

The output map is generated by looping through the enabled streams to collect the package names from the `api` section and full RPM names from the `artifacts` section of the module definitions (explained further below).

In case of any errors where a specific combination of streams cannot be possibly enabled, the API returns a proper error status, which can be propagated to the UI during project build.

### Cross-dependencies and conflicts with other repositories
There are some cases where a stream manifests some non-modular packages residing in either the same repository or some other, non-modular repository. To prevent conflicts with these packages, those external RPMs must also be blacklisted when an alternative stream of the module is enabled. This is observable in the metadata when a package name appears in the `api` section, but a corresponding RPM does not exist in the `artifacts` section.

> **api:**
>
> The module's public RPM-level API.
> A list of binary RPM names that are considered to be the
> main and stable feature of the module; binary RPMs not listed
> here are considered "unsupported" or "implementation details".
>
> **artifacts:**
>
> This section lists binary artifacts shipped with the module, allowing
> software management tools to handle module bundles.  This section is
> populated by the module build system.

*modulemd specification*

This situation is handled with the following additional procedure:

Instead of a plain list of RPMs, the API returns a map of package names provided in the `api` section to non-empty lists of artifacts that match the corresponding package names. If a module lists a name in the `api` section but does not provide any artifacts, that name will not be included in the map.

Since not all of the artifacts are listed in the `api` section, the remaining artifacts are put into a special "null" key.

For each key of the map, the backend gets the packages with the same name from all available sources. If any of the packages are not included in the corresponding artifacts list, the package is added to the blacklist.

As a result, when a module defines a package name in its API *and* provides an actual RPM with it, all the other RPMs with the same name are effectively blacklisted even if they are in a different source.

### Module updates and multiple versions
Every released update of a module is added into the module metadata as a separate module entry with a new `version` number. By design, Uyuni needs to include either all versions of a module or none at all.
This can be achieved by enabling all versions of the module in the API at the same time. As a result, all the artifacts from all versions will be included sharing the same key in the returning map.

# Drawbacks
[drawbacks]: #drawbacks

For each build of the project, the backend needs a full list of RPMs that each module provides. The most important drawback is the amount of data to process for each build considering the module metadata will grow constantly with each released update.

# Alternatives
[alternatives]: #alternatives

The current version of Uyuni supports modular repositories in the most basic way. Modular repositories are recognized, mirrored correctly and can be assigned systems. However, doing package operations on these systems through the Uyuni UI is not supported. These systems must be managed from their own package managers.

The next step to supporting modular repositories would be to implement modularity in the core with dedicated logic for package operations and a new set of UI. The most obvious benefit of this would be to be able to do package operations through the UI while still providing modular repositories to the clients. However, this implementation would require much more effort and currently beyond the scope.

# Further enhancements
[enhancements]: #enhancements

### Interactive inputs for filters
To provide better user experience, the filter inputs can be turned into responsive dropdowns showing a list of module/stream names with realtime feedback.
However, since the module list can only be retrieved from the project sources and the current implementation of CLM filters are independent of the sources, this is not currently achievable.
One possible enhancement could be adding some supplementary auto-complete feature in cases where some sources are added to the CLM project.

### Selective version filtering
If required, it is possible to selectively filter a specific version of any module by introducing additional types of module filters.

# Unresolved questions
[unresolved]: #unresolved-questions

 - How to communicate between the Python API and the Java backend
 - What should be the behavior for the unselected modules? Should the modules be disabled unless there is a filter targeting them? Should they be enabled with default streams in the best effort?
 - What should be the behavior if no module filter is added to a project? Should the resulting repository be "flattened" or should it be modular?

