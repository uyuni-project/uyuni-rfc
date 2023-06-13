- Feature Name: Autogenerate Bootstrap Repositories
- Start Date: 2020-02-19
- RFC PR: https://github.com/uyuni-project/uyuni-rfc/pull/33

# Summary
[summary]: #summary

Automatically generate bootstrap repositories

# Motivation
[motivation]: #motivation

To be able to register a system to Uyuni Server you need to have the software installed which provide the required tooling.

A bootstrap repository provide the software for the supported operating systems with its dependencies. The content for the
bootstrap repositories come from the normal channels which must be synchronized and updated on regular base.

Users very often do not know this, or forget to create them when they synchronize a new products and channels.
Also the bootstrap repository is only updated when the user execute the generator script again.

This RFC should describe how to change the current tools to automatically 
execute the generation of bootstrap repositories after a new product or channel was added,
and after a channel changed because the underlying repositories synced new or updated packages.

# Detailed design
[design]: #detailed-design

The currently existing tool `mgr-create-bootstrap-repo` list all available bootstrap repositories it could generate.
This list depends on the products/channels the user has synchronized.

Step 1: provide an option to enable an automatic mode which iterate over all available bootstrap repositories and generate them
when needed. As we have sometimes have multiple options for the same local "path" we should iterate over the paths to minimize
the number of runs.

Step 2: add a log file to `mgr-create-bootstrap-repo`. Currently it has no log file. But when this tool is running in the background
we need the possibility to debug problems. All messages should go to a log file.

Step 3: let `mgr-create-bootstrap-repo` use a configuration file. All command line options useful for automatic mode should be possible
to set via configuration file. This allows to influence the behavior even in automatic mode when it is not possible to change the commandline
options.

Step 4: implement a locking mechanism to run only 1 instance of `mgr-create-bootstrap-repo` at the same time or more fine grained
to prevent generating the same repository from 2 instances. As triggering from reposync already serialize the generation of bootstrap
repositories, we need to take care only about manual called `mgr-create-bootstrap-repo`. A full lock on the whole application
should be sufficient here.

To trigger the re-generation we implement the following algorithm:

- call `mgr-create-bootstrap-repo` from a successful finished reposync
- It calculate all channels which are needed to create the bootstrap repository for every available OS
- It compare the `last_synced` timestamps of the channels (DB) with the `modified date` of the main metadata file
  (repomd.xml or Release)
- if all `last_synced` timestamps are newer then the timestamp of the main metadata file, re-generate the bootstrap repository
- if any `last_synced` timestamps is newer then the timestamp of the main metadata file and the latest `last_synced` DB value
  is older than 4 hours ago, re-generate the bootstrap repository. This is for the case a channel has a different schedule as the other
  channels. Or somebody called `spacewalk-repo-sync` manual for one channel only. The 4 hours are a grace period to prevent inconsistent
  data in the bootstrap repo. We only generate the repository when all mandatory repositories finished syncing at least 1 time in the past.

To force a generation of a bootstrap repo, the user can always call `mgr-create-bootstrap-repo` on the command line in interactive mode.


## Optional feature enhancements
[optional]: #optional

### User Notifications

As this now run in background we should add notifications for the users. The following are useful:

1. On Error: when regeneration of a bootstrap repository failed.
2. On Success: when a regeneration successfully finished.


# Drawbacks
[drawbacks]: #drawbacks

- Information when a product is ready to be used/bootstrap is not available. This problem is not new and exists already now.
  Adding notification would give at least a hint.


# Alternatives
[alternatives]: #alternatives

1. Execute the `mgr-create-bootstrap-repo` one time per day in the morning via taskomatic expecting the nightly reposync is finished.

2. Create a taskomatic job running every 15 minutes and call `mgr-create-bootstrap-repo --auto`. This would decouple bootstrap repo generation
   from repository syncing, but we would get a delay and we would call it more often then needed in case a long running reposync is happening.


# Unresolved questions
[unresolved]: #unresolved-questions

