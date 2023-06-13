- Feature Name:  ci-prs-cucumber
- Start Date: 2017-10-16)
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

Run SUSE Manager acceptance tests on GitHub PRs, for x86_64 only.

# Motivation
[motivation]: #motivation

Having Acceptance Tests for SUSE Manager on each PR increases the level of confidence about the stability of the product.

We can ensure that no fundamental regression will impact the product and each developer can contribute **pro-actively** (before breaking changes) to the testsuite and the product. Developers will know in advance which tests need fixing before merging a new feature, or which new bugs the PR would introduce if merged.

With this we will decrease the maintenance of reviewing the results, fixing broken tests, because this cost will be spread in single PRs reviews, which the maintainer of the feature PR will have the responsibility of.

This way we will also remove the fixed role of 'maintainer' of the testsuite, which is not agile and represents a single point of failure.

The expected outcome is to have for each PRs an automatically deployed Manager30/31/HEAD CI infrastructure, based on custom Spacewalk OBS packages,  having the result of the tests linked  on the PR.
If the PR breaks the package during building, no Test Infrastructure will deployed and the result will be which package broke the build, so we save time and costs.

The tests need to be as fast as possible, so as a first step, we will run only the releases listed at: 

https://github.com/SUSE/spacewalk-testsuite-base/releases

No new feature machine will be added, as soon we cannot solve the performance issues on the testsuite (parallelism of tests, removing of rendudant features, removing of hardcoded SUSE Infra tests, such the IPMI tests and so on).

The results will in be the Cucumber output.html format. 

We will have only the results as a stable output, meaning that we cannot have the CI machines for debugging purposes. Each PR will destroy the existent CI machines and destroy the OBS Branch that is used for building the packages.

In other words, PR authors will need to deploy the CI machines on his own workstation for further inspection if needed. Documentation is already available to do this reliably.

# Global Picture 

![Global Picture](images/00038-ci-prs-cucumber2.png)


Having the PRs will give the author of PR the possibility to fix bug before his PR is merged.
This will ping directly the author of the regression, and give the possibility to fix the bug or tests.

We will have the Branch tests, for taking care that all Pull Request can work together after merging.
The branch tests are the last final step.

# Detailed design
[design]: #detailed-design


From a GitHub PR (0) we will build a complete set of packages for the SUSE Manager Server (SUSE Manager Client tools will not be covered per PR) (2),

This server packages will be injected and deployed to the CI-Infrastructure to a dedicated KVM Server (3).

Once the CI infrastructure is deployed, we will run all needed acceptance tests and publish the result link to the PR Review. (4)


![Design](images/00038-ci-prs-cucumber.png)


There are 5 important Phases which concern the design:

0. Gitarro fetches GitHub PRs
1. KVM server is managed via Salt states
2. SSH Sumadocker-Provo (Salt setup): Communication from Jenkins Slaves to KVM Server
3. Deploy the SUSE Manager CI Machines (server and clients) from OBS packages and run the tests
4. Publish the results of tests to the respective PRs

## 0) Gitarro fetches GitHub PRs

Gitarro allows to fetch open PRs and execute programs, updating the results to the respective PR etc.

We will have a general shared repo called `galaxy-ci`. (hosted on Github/Gitlab)

This repo will contain code for building OBS packages and inject them in the deployed CI infrastructure, which will run integration tests.

About gitarro:

Gitarro is a well-known project within the team, and it is running in production since about one year: https://github.com/openSUSE/gitarro.

Jenkins host tags will be used to avoid interference with regular integration tests.

### TODO

- On the Jenkins side:
  - We will create a context (testname) "cucumber-tests-prs", all the code executed will contained in this gitlab repo: https://gitlab.suse.de/galaxy/galaxy-pr-ci. This repository will be cloned by Jenkins each run.
  - We will create 2 Jenkins jobs as usual for gitarro (1 fetcher/scheduler, 1 job executor)

## 1 - KVM server is managed via Salt states

We will reuse all Salt states in the gitlab repo `infrastructure` to manage our KVM server.

### TODO

Create Salt states for the metropolis server, to be a KVM server and have a web-service to host the cucumber outputs. Currently the server is completely unconfigured.

## 2 - Build RPM Packages from PRs 

In the SUSE Manager Project amost specfiles are hosted inside of the GitHub repo.
Once gitarro has cloned the code, it will execute the script: https://gitlab.suse.de/galaxy/infrastructure/blob/master/srv/salt/pr-automation/git2OBS.sh

This script will execute `rel-eng` tools already existing in Spacewalk repo.

In OBS I have created 3 special branches called `Pr-Automation` for versions 3.0, 3.1 and HEAD. Those are used to build SUSE Manager Server packages.
https://build.suse.de/repositories/Devel:Galaxy:Manager:Head:Pr-Automation, https://build.suse.de/project/show/Devel:Galaxy:Manager:3.1:Pr-Automation

The rel-eng tools will push all the latest git changes to OBS, depending on the PR's branch (3.0/3.1/HEAD/..)

The script checks if **all** packages build successfully. If a package is broken, the script fails and the whole process is interrupted, the result of the package breakage will be sent to the PR.

This Phase is **already working and implemented for all branches**. Checkout the test/context on PR: `OBS_packages_build_susemagr`.

### TODO

We need to copy the working scripts on the specific repo, and maybe some cosmetic fixes (to improve output readability).

## 3 - Deploy the SUSE Manager CI Machines (server and clients) from OBS packages and run the tests

We will use the same logic that we use here: https://gitlab.suse.de/galaxy/sumaform-test-runner.

We will have a central script that is taking care of the sumaform client commands, and copy the results to respective webservice.

The end results of phase will be to have the output.html cucumber result to the webservice directory copied. (Jenkins Artifacts is planned)

### TODO

- implement this phase and copy it to the https://gitlab.suse.de/galaxy/galaxy-pr-ci. (no e-mail or IRC notification is planned)
- merge spacewalk-testsuite into spacewalk repo  

## 4 - Publish the results of tests to the respective PRs

We will append the Jenkins Job URL with gitarro to the GitHub PR. 

Since now we can export PR-NAMES or PR-Numbers, we can rename the html output file to the name of PR.

For example we can have:

`metropolis.net/pr-results/2188.html` ( 2188 will be the number of PR )

If there is no output, this mean that something went wrong (eg. deployment problem), so that the PR author can see the Jenkins URL, and debug it.

The next run will destroy the CI Machines.

###  Final TODO list

- Use Jenkins Artifacts to compact and store all results. (not fondamental for core functionality)
 
# Drawbacks
[drawbacks]: #drawbacks

I see no drawback on this RFC, since it can improve and bring no regression.

# Alternatives
[alternatives]: #alternatives

On the OBS side we could have OBS PR-Branches builded, instead of 3/4 central branch. 
This approach add however extra complexity, artifacts that need cleanup. (I am not even sure that we could gain speed).
The only advantage would be that packages would be not destroyed but could be reused.


# Unresolved questions
[unresolved]: #unresolved-questions

We need to solve a problem:
  - differences with GitHub spec and OBS spec.

If people modify directly OBS packages but doesn't modify the GitHub specs, the server on Pull-Request cannot build or have problems.
We need to ensure that OBS packages are always update on GitHub spec. ( so we avoid these fatal problems). 
We need a technical way to ensure this.
