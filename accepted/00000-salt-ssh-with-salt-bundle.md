- Feature Name: Salt-SSH with Salt Bundle
- Start Date: 2021-12-08

# Summary
[summary]: #summary

Use Salt Bundle to handle Salt-SSH sessions on managed system side.

# Motivation
[motivation]: #motivation

Due to the deprecation of Python 2 and dropping support of it, while some of supported Linux systems still has no proper Python 3 version supported by Salt, we need to have a way to process Salt-SSH events on managed system side.

We can deploy Salt Bundle with bundled Python inside the virtual environment and handle all the Salt-SSH events using Salt Bundle with making Salt-SSH independent from Python on the managed system.
Additionally we are extending the list of working modules as Salt Bundle contains binary python modules required by some of Salt modules.

This approach will help us to limit the number of supported versions of Salt codebase and drop `py26-compat-salt`, `py27-compat-salt` and all Python 2 dependencies maintenance.

# Detailed design
[design]: #detailed-design

## Uyuni roster

We can use Uyuni roster module to provide roster data instead of creating flat roster files with Java. PR moving the logic to Uyuni roster on Java side: https://github.com/uyuni-project/uyuni/pull/4457

## Pre flight script

Salt can execute a shell script on the salt-ssh client before the "real salt-ssh execution" starts. This script downloads the salt-bundle package from the appropriate bootstrap repository and extracts the virtual environment.

The "Pre flight script" calculates the bootstrap repository URL in a similar manner to the existing boostrap.sh script, based on the operating system and OS architecture of the system it is executed on. It requires one parameter from the Uyuni server: (host, port) (entry point) for SSH connections through tunnels.

By-default there is no way to pass additional parameters to pre fligt script running on the managed system. We need to pass the entry point (host and port) to get bootstrap repository from. The salt codebase need to be modified to pass additional parameters, otherwise we have to generate pre flight script individually for each managed system.

## Deploying Salt Bundle to the managed system

We don't need to install Salt Bundle package on the managed system. We need to extract the virtual environment of the bundle from the package. Pre flight script is deploying it as secribed above.

## Using proper salt codebase

On deploying Salt Bundle with pre flight script, without modification salt-thin deployment, we will get two different codebases of salt deployed on the managed system. We can prevent deploying salt-thin in case if Salt Bundle has been deployed already and use it as preferred salt codebase to handle salt-ssh session with on managed system side.

# Drawbacks
[drawbacks]: #drawbacks

  * Salt Bundle consumes more space than salt-thin on managed system
  * Salt is creating additional SSH connection to run the pre flight script 
  * Pre flight script requires an access to the bootstrap repository (salt-thin is deployed with ssh, no http(s) connection needed for salt-ssh)
  * We need to modify salt codebase to handle Salt Bundle the proper way

# Alternatives
[alternatives]: #alternatives

- Prepare Salt Bundle for each OS and architecture on the Server, but it just make pre flight script bit smaller, the overall complexity is higher due to the bunch of additional changes on server side.
- With not doing this the systems having not having sufficient Python version can't be managed with Salt-SSH and bootstrapped with web UI

# Unresolved questions
[unresolved]: #unresolved-questions

- The way to update Salt Bundle used for Salt-SSH on the managed system and validate it (cases when we need to redeploy it).
