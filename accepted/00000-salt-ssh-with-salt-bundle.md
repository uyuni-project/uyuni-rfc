- Feature Name: Salt-SSH with Salt Bundle
- Start Date: 2021-12-08

# Summary
[summary]: #summary

Use Salt Bundle to handle Salt-SSH sessions on the minion side.

Salt Bundle is a single package containing salt codebase, Python and python modules required for salt.

# Motivation
[motivation]: #motivation

Due to the deprecation of Python 2 and dropping support of it, while some of supported Linux systems still has no proper Python 3 version supported by Salt, we need to have a way to process Salt-SSH events on the minion side.

The following systems are using salt codebase older than `3002.2`:
- SLE 11 (LTSS ends 31 Mar 2022, no plans to support it with Salt Bundle)
- SLE 12
- RHEL 7 (and clones)
- Debian 9

We can deploy Salt Bundle with bundled Python inside the virtual environment and handle all the Salt-SSH events using Salt Bundle with making Salt-SSH independent from Python on the minion.
Additionally we are extending the list of working modules as Salt Bundle contains binary python modules required by some of Salt modules.

This approach will help us to limit the number of supported versions of Salt codebase and drop `py26-compat-salt`, `py27-compat-salt` (as these packages are shipping `2016.11.10` and `3000.3` respectively) and all Python 2 dependencies maintenance.
So we don't need to maintain old salt codebases, but focus only on the latest one.

# Detailed design
[design]: #detailed-design

## Uyuni roster

We can use Uyuni roster module to provide roster data instead of creating flat roster files with Java. PR moving the logic to Uyuni roster on Java side: https://github.com/uyuni-project/uyuni/pull/4457

This change can help to avoid creating temporary roster files (https://docs.saltproject.io/en/latest/topics/ssh/roster.html) and implements caching additionally.

## Pre flight script

Salt can execute a shell script on the salt-ssh client before the "real salt-ssh execution" starts.
This script downloads the salt-bundle package from the appropriate bootstrap repository and extracts the virtual environment.
By-default there is no way to pass additional parameters to pre fligt script running on the minion.
In this case we have to generate individual pre flight script to each of the minion. The main drawback here is maintaining these pre flight script files.

The other solution is to pass additional parameter to the static pre flight script.
The pre flight script calculates the bootstrap repository URL in a similar manner to the existing boostrap.sh script, based on the operating system and OS architecture of the system it is executed on.
It requires one parameter from the Uyuni server: host, port (entry point) for different contact methods and pathes (SSH from server/proxy, direct access to the repos or with the tunnel).
The salt codebase need to be modified to pass additional parameters, therwise we have to generate pre flight script individually for each minion.

## Deploying Salt Bundle to the minion

We don't need to install Salt Bundle package on the minion.
We need to extract the virtual environment of the bundle from the package.
Pre flight script is deploying it as described above.

## Using proper salt codebase

On deploying Salt Bundle with pre flight script, without modification salt-thin (`salt-thin` is a tarball with salt codebase created by the server to deploy salt on the salt-ssh minion: https://docs.saltproject.io/en/latest/ref/runners/all/salt.runners.thin.html) deployment, we will get two different codebases of salt deployed on the minion (one codebase is from salt bundle package for the OS+arch and the other one is from salt-master delivered with salt-thin tarball).
As the sources of these two codebases are different (update channel of the Server and client tools relevant for the system) these codebases are not in sync.
We can prevent deploying salt-thin in case if Salt Bundle has been deployed already and use it as preferred salt codebase to handle salt-ssh session with on the minion side.

In most cases the client tools channels are updating more frequently than the server and for the minions (not salt-ssh systems) we are using the salt codebase from client tools, it's better to use Salt Bundle codebase for salt-ssh systems.

If deploying Salt Bundle is not possible for some reason (no salt bundle package in the bootstrap repo for the system, no bootstrap repo at all or the server is unavailable with http(s)) we can use `salt-thin` on the minion, so we need to deploy it only in case if Salt Bundle was not deployed.
In case of using `salt-thin` the minion must have sufficient version of Python installed.

## Updating Salt Bundle on the minion

We already included `sha256` hash of the Salt Bundle package to `venv-enabled-ARCH.txt` in the root of bootstrap repo.
The pre flight script can store the hash of the deployed Salt Bundle and check if it should be updated by comparing it with the hash from `venv-enabled-ARCH.txt`.

# Drawbacks
[drawbacks]: #drawbacks

  * Salt Bundle consumes more space than salt-thin on the minion
    Each salt codebase consumes `~33Mb` on the minion (`99Mb` as now we have 3 codebases: `3002.2` from the master, `3000.3` and `2016.11.10`, as we are dropping `py26-compat-salt`, `py27-compat-salt` and all the dependencies `salt-thin` will contain only one salt codebase `33Mb`)
    The Salt Bundle deployed on the minion is slightly larger than `100Mb`
  * Salt is creating additional SSH connection to run the pre flight script 
  * Pre flight script requires an access to the bootstrap repository (salt-thin is deployed with ssh, no http(s) connection needed for salt-ssh)
    http(s) connection is used to get just 2 files: `venv-enabled-ARCH.txt` to get the exact path to the Salt Bundle package and the package itself
  * We need to modify salt codebase to handle Salt Bundle the proper way

# Alternatives
[alternatives]: #alternatives

- Prepare Salt Bundle for each OS and architecture on the Server, but it just make pre flight script bit smaller, the overall complexity is higher due to the bunch of additional changes on server side.
- With not doing this the systems having not having sufficient Python version can't be managed with Salt-SSH and bootstrapped with web UI

# Unresolved questions
[unresolved]: #unresolved-questions

- How to check if the Salt Bundle deployed on the minion is consistent (has all the files and the files was not changed)
  `salt-thin` is not checked for consistency on the minion, it's just starting redeployment if hash of extracted `salt-thin` (not calculated, but stored in separate file on time of exctracting previous copy of `salt-thin`) doesn't match the hash of the `salt-thin` archive.
- Testing need to be adopted somehow. The suggested solution is using Salt Bundle package `venv-salt-minion` from the bootstrap repo relevant for the minion, and gets the file name of the package from `venv-enabled-ARCH.txt` at the root of the bootstrap repo, while testing environment has no bootstrap repos generated on the server.
  Without pointing the correct package Salt-SSH system will be tested with salt-thin and it's not correct in context of using Salt Bundle for Salt-SSH

