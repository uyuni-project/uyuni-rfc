- Feature Name: Salt-SSH with Salt Bundle
- Start Date: 2021-12-08

# Summary
[summary]: #summary

Use Salt Bundle to handle Salt-SSH sessions on managed system side.

# Motivation
[motivation]: #motivation

As the Python 2 gets deprecated and out of support and some of the supported Linux systems still has no proper Python 3 version supported by Salt, we need to have a way to process Salt-SSH events on managed system side.

We can deploy Salt Bundle with bundled Python inside the virtual environment and handle all the Salt-SSH events using Salt Bundle and make Salt-SSH independent from Python on the managed system.
Additionally the list of working modules will be extended as Salt Bundle contains binary python modules required by some of Salt modules.

This approach will help us to limit the number of supported versions of Salt codebase and drop `py26-compat-salt`, `py27-compat-salt` and all Python 2 dependencies maintenance.

# Detailed design
[design]: #detailed-design

## Uyuni roster

Uyuni roster module is used to provide roster data instead of creating flat roster files with Java. Java change to move all the logic to Uyuni roster: https://github.com/uyuni-project/uyuni/pull/4457

## Pre flight script

Pre flight script is used to detect OS and architecture to get proper Salt Bundle from the package available with bootstrap repository.

By-default there is no way to pass additional parameters to pre fligt script running on the managed system. We need to pass the entry point (host and port) to get bootstrap repository from. The salt codebase need to be modified to pass additional parameters, otherwise we have to generate pre flight script individually for each managed system.

## Deploying Salt Bundle to the managed system

We don't need to install Salt Bundle package on the managed system. Only virtual environment of the bundle need to be extracted from the package. It can be done with pre flight script.

## Using proper salt codebase

On deploying Salt Bundle with pre flight script, without modification salt-thin deployment, we will get two different codebases of salt deployed on the managed system. We can prevent deploying salt-thin in case if Salt Bundle has been deployed already and use it as preferred salt codebase to handle salt-ssh session with on managed system side.

# Drawbacks
[drawbacks]: #drawbacks

  * Salt Bundle consumes more space than salt-thin on managed system
  * One more additional script required to run on managed system (pre flight script)
  * Requires an access to the bootstrap repository (salt-thin is deployed with ssh, no http(s) connection needed for salt-ssh)
  * Few changes required in salt codebase

# Alternatives
[alternatives]: #alternatives

- Prepare Salt Bundle for each OS and architecture on the Server, but it just make pre flight script bit smaller, the overall complexity is higher due to the bunch of additional changes on server side.
- With not doing this the systems having Python 2 or not having Python at all can't be managed with Salt-SSH and bootstrapped with web UI

# Unresolved questions
[unresolved]: #unresolved-questions

- The way to update Salt Bundle used for Salt-SSH on the managed system and validate it (cases when we need to redeploy it).
