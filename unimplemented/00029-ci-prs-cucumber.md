- Feature Name:  ci-prs-cucumber
- Start Date: 2017-10-16)
- RFC PR: (leave this empty)

# Unimplemented note

This RFC was not ultimately implemented due to time limitations. It is still archived here for historical purposes.

# Summary
[summary]: #summary

Run SUSE-Manager acceptance tests on GitHub PRs.

# Motivation
[motivation]: #motivation

Having Acceptance Tests for SUSE-Manager on each PRs increase the level of confidence about the stability of the product.

We can ensure that no fundamental regression will impact the product and each developer can contribute **pro-actively** (before changes broke) on the testsuite and the product, knowing in advance which tests he need to fix before merging a new feature, or which new bugs the PR would introduce if merged.

With this we will decrease the maintenance of reviewing the results, fixing broken tests, because this cost will be spread in singles PRs reviewF, which the mantainer of the feature PR  will have the responsability to maintain, fix the tests, or the codebase if the PR contains a bug.

In this way, we will also remove the fixed roles of 'maintainers' of the testsuite, which is not agile and represent a single point of failure.

The expected outcome is to have for each PRs an automatically deployed Manager30/31/HEAD CI infrastructure, based on custom spacewalk OBS pkgs,  having the result of the tests linked  on the PR.
If the PR break the package during building, no Test Infrastructure will deployed and the result will be which package broke the build, so we spare time and costs. 

The tests need to be performant and fast as possible, so as a first step, we will run  only the releases https://github.com/SUSE/spacewalk-testsuite-base/releases.
No new/feature machine will be added, as soon we cannot solve the performance issues on the testsuite. ( parallelism of tests, removing of rendudant features, removing of hardcoded SUSE Infra tests, such the IPMI tests and so on)

The results will be the cucumber output.html format. 

We will have only the results as a stable output, meaning that we cannot have the CI machines for debugging purpose that are running.

Each PR will destroy the existent CI machines and destroy the OBS Branch that is used for building pkgs.

The PR Author if it cannot find the error with the cucumber output.html and screenshot, will need to deploy the CI machines on his own workstation. 

Since Production and local deployment are 1:1 , this can be easy achieved following the documentation.
 

# Detailed design
[design]: #detailed-design

The RFC will make possible from a PR (1) to build a complete SUSE-Manager Server (2),
and deploy the CI-Infrastructure to a dedicated KVM Server (3).
Once the CI is deployed, we will run all needed acceptance tests and publish the result link to the PR Review. (4)


![Design](images/00035-ci-prs-cucumber.png)


As you can see,  we have 5 important Phases which concern the design.
We will describe them in detail.

0. Gitarro fetching GITHUB PRs.
1. Build Rpm Packages from PRs.
2. SSH Sumadocker-Provo (Salt setup): Communication from Jenkins Slaves to KVM Server
3. Deploy the SUSE-Manager CI Machines (server,clients) from OBS PKGs and run tests.
4. Publish the results of tests to the respective PRs.


## 0) Gitarro fetching GITHUB PRs.

Gitarro allow us to fetch PRs open and execute programs, updating the results to the respective PR etc.

We will have a general shared repo  https://gitlab.suse.de/galaxy/galaxy-pr-ci

the repo galaxy-pr-ci will contain code for building obs/pkgs/ and deploy run tests.

About gitarro:

Gitarro is a well-known project in galaxy, that is running in production and i have created since one year https://github.com/openSUSE/gitarro.
We use on Sumadockers hosts tags to deploy gitarro. fixed tags we will provide stability and don't interfer with dev process for the rubygems

### TODOS: On Jenkins side:

- We will create a context "cucumber-tests-prs", all the code executed will contained in this gitlab repo: https://gitlab.suse.de/galaxy/galaxy-pr-ci
  This repository will be cloned by jenkins each run.

- We will create 2 Jenkins Jobs as usual for gitarro (1 fetcher/scheduler, 1 job executor)

## 1) Build Rpm Packages from PRs 

In SUSE Manager Project all specs are inside github repo.
Once gitarro have cloned the code, it will execute the script: https://gitlab.suse.de/galaxy/infrastructure/blob/master/srv/salt/pr-automation/git2obs.sh

This script execute `rel-eng` tools already existing in spacewalk repo.

In OBS i have created 3 special branches: .. Pr-Automation. 30/31/HEAD, which are used to build SUSE-Manager server for spacewalk.
Example : https://build.suse.de/repositories/Devel:Galaxy:Manager:Head:Pr-Automation, https://build.suse.de/project/show/Devel:Galaxy:Manager:3.1:Pr-Automation

The rel-eng tools will push all the latest gitchanges to OBS , depending on the PR's branch OBS will build the server. (30/31/HEAD/..)

The script check if **all** packages build successefully. If a package is broken, the script fails and the whole process is interrupted, the result of the pkg breakage will send to the PR.

This Phase is **already working and implemented for all branches**. Checkout the test/context on PR: `obs_pkgs_build_susemagr`.

### TODOS:

We need only to copy the working scripts on the specific repo, and maybe some cosmetical fixes (better output printing).


## 2 SSH Sumadocker-Provo (Salt setup): Communication from Jenkins Slaves to KVM Server

This phase and others will run only if 1 it was sucessefull (pkgs building).

We will use ssh with private key from a random picked sumadocker from jenkins to the server Metropolis.

All sumadockers are managed in gitlab. The ssh command will be part of script from the only one PRs-CI repo : https://gitlab.suse.de/galaxy/galaxy-pr-ci

We will use ssh because terraform-libvirt-plugin has latency problems/bugs and will be unstable to use a remote-kvm server configuration.

### TODOS:

- update salt states for sumadockers in gitlab to have some key and deploy this to metropolis.
- create salt states  for metropolis server, to be a KVM server and have a minimal web-server running (apache2/nginx) 
- the whole metropolis server is atm not configured, so with salt state we need to make it kvm-server.

## 3 Deploy the SUSE-Manager CI Machines (server,clients) from OBS PKGs and run tests.

With the ssh protocol we will run sumaform : https://github.com/moio/sumaform/ for deployng all CI Infrastructure.

We will use the same logic that we use here: https://gitlab.suse.de/galaxy/sumaform-test-runner.

Meaning we will have a central script that is taking care of the sumaform client commands, and copyng the results to respective webserver.

The end results of phase will be to have the output.html cucumber result to the webserver copied. 

### TODOS:

We need to implement this phase and copy it to the https://gitlab.suse.de/galaxy/galaxy-pr-ci. ( we dont need e-mail or IRC notifications for this)
 
## 4 Publish the results of tests to the respective PRs.

Gitarro can append an url to the web-server. We will append the Jenkins Job as url. ( we cannot append 2 urls in GITHUB api, this by githubs design).

In the lastest line of the Jenkins we can print the url of the job.

Since now we can export PR-NAMES or PR-Numbers, we can rename the html output to the name of PR.

For example we can have:

`metropolis.net/pr-results/2188.html` ( 2188 will be the number of PR )

If there is no output, this mean that something went wrong ( deployment problem), so the PR Author can see the Jenkins URL, and debug it by itself.

Since the PR automation spread Responsability, the PR author should submit a PR to sumaform or other components if he found the problem, and not ask maintainers of the components to fix them,like open issues etc. 
( he can ask for info, but it can be that the maintainer of a components has the same knowledge like the PR author)

The next run will destroy the CI Machines.

### TODOS:

- we need to implement this 4 phase
- we need to introduce good agile habits.

 
# Drawbacks
[drawbacks]: #drawbacks

I see no drawback on this RFC, since it can improve and bring no regression.

# Alternatives
[alternatives]: #alternatives

This is the best realistic design that we can have.

The only alternative would be to bypass the sumadocker in Nurnberg and do everything in Provo, but due to OBS in NUE, we will have only network latency problems.

# Unresolved questions
[unresolved]: #unresolved-questions

I put in every phase the todos.

We need to implement 3/4, which are not the **core** of the project. All essential tools for this project are already implemented and production ready. (gitarro, sumaform, and helper scripts)
