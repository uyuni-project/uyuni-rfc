- Feature Name: Autogenerate Bootstrap Repositories
- Start Date: 2020-02-19
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

Automatically generate bootstrap repositories

# Motivation
[motivation]: #motivation

To be able to register a system to Uyuni Server you need to have the software installed which provide the required tooling.

A bootstrap repository provide the software for the supported operating systems with its dependencies. These content for the
bootstrap repositories come from the normal channels.

Users very often do not know this, or forget to create them when they sync a new product. Also the bootstrap repository is
only updated when the user execute the generator script again.

This RFC should describe how to change the current tools to automatically execute the generation of bootstrap repos after
a new product was added and after every channel change when a maintenance update was synced to Uyuni Server.

# Detailed design
[design]: #detailed-design

The currently exiting tool `mgr-create-bootstrap-repo` list all available bootstrap repos it could generate.
This list depends on the products the user has synchronized.

Step 1: provide an option to enable an automatic mode which iterate over all options and generate all bootstrap repos.
As we have sometimes multiple options for the same local `path` we should iterate over the paths to minimize the number
of runs.

Step 2: add a logfile to `mgr-create-bootstrap-repo`. Currently it has no logfile. But when this tool is running in the background
we need the possibility to debug problems. All messages should go to a logfile.

Step 3: let `mgr-create-bootstrap-repo` use a config file. All commandline options should be possible to set via config file.
This allows to influence the behavior even in automatic mode when it is not possible to change the commandline options.

To trigger the re-generation we implement the following algorithm:

- Create a taskomatic job running every 15 minutes and call `mgr-create-bootstrap-repo --auto`
- It find all channel labels which are needed to create the bootstrap repo for every available OS
- It compare the last_modified timestamps of the channels (DB) with the modified date of the main metadata file (repomd.xml or Release)
- if all are newer then last_modified, generate the bootstrap repository
- if any is newer then last_modified and last_modified is older than 26 hours, re-generate the bootstrap repository.
This is for the case a channel is not synced. Can happen on custom repositories needed for bootstrap repositories.

Provide a `--force` option to enforce recreation of all bootstrap repositories without checking if needed. Mostly for manual usage.

# Drawbacks
[drawbacks]: #drawbacks

We maybe 15 minutes late with the bootstrap repository or maybe longer when a channel failed to sync or does not sync at all.

# Alternatives
[alternatives]: #alternatives

1. Execute the `mgr-create-bootstrap-repo` one time per day in the morning via taskomatic expecting the nightly reposync is finished.

2. Every finished repo sync trigger a `mgr-create-bootstrap-repo --for_updated_channel <label>`. It check if this channel is used
for any bootstrap repository. If yes, regenerate them. If not, exit without doing anything.


# Unresolved questions
[unresolved]: #unresolved-questions

