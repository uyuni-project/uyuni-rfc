- Feature Name: Salt Testing Suite
- Start Date: 2016-04-25
- RFC PR:
- Rust Issue:

---
- Bo Maryniuk <bo@suse.de>


# Summary
[summary]: #summary

Salt codebase and package testing, maintentance and development.

## TL;DR

Fundamentals:

1. Test the Salt packages, not just the source code in the Git.

2. Test the Salt packages from the branch during the package maintenance procedure, right before submitting request.

3. Eliminate ignorable failures in automated build systems, so then we can focus only on important failures if they happen.

## Definitions

1. SUSE-related: All SUSE products, such as SLE, Manager, Storage, Cloud etc., as long as Salt is "touching" them or any related to it.

2. openSUSE-related: All what is related to Leap and Tumbleweed, 3rd party software and community.

3. Product: final product that consists of source and created packages, available for use.

# Motivation
[motivation]: #motivation

SaltStack is a cornerstone component of many SUSE-related products. In order to assure stability of the integrated part with the SUSE products, a thorough covered areas testing is required. Since Salt upstream community takes very broadly on the tests and they are quite often broken (or in the state *red*), we need a stable process and testing system that would at least make sure SUSE Manager part is always working as expected.

# Detailed design
[design]: #detailed-design

## Types of Test Suites

There are at least two types of testing approaches available:

1. Test driven (known as TDD for development)

2. Behavior driven (known as BDD for development)

An example of TDD type is a classic Unit Test. An example of BDD type is Cucumber Test Suite, where additionally to an actual test there is a verbose layer of a description, usually human-readable, what a test should do.

## Primary Requirements to the Test Framework

At least these requirements should be met in the Test Suite:

1. Shouldn't be rock-stateful so the next test not necessarily should depend on the results of the previous test, although such feature should be there too

2. Should support classic mocking, allow running a tests in an isolated sandbox-like environment

3. Should stop at first error and therefore should be fast to run it locally, fixing the whole suite

4. Should best describe an error, so the developers can get to the point easily

5. Should not be "cryptic" and complex in the learning curve

6. Should be highly documentable so each test should be documented and explained

7. Tests should be easily readable. This refers to the understandability for a fastest possible comprehension of the whole test suite.

8. Usage of the Test Suite should make it possible to use various types of tests from the same framework. Framework should be as close as possible compatible with the upstream, ideally accepted by the upstream at some point.

Bonus points: Test suite should be also able to run in a renewable Docker container.

## Secondary Requirements to the Test Framework

Extended list of requirements as follows:

1. Avoid "Cucumber Syndrome", where one stateful test error produces wast amount of consequences. However, depends what kind of test is running, it should support a) "Stop at first error" as well as b) "Collect errors" modes. For example, Unit Test should _not be stopped_ at first error, but rather collected into one single report, so the developer(s) can fix it asynchronously. Same is valid to the _stateful_ tests, in case they are not affecting any other tests. In this case should be a `decorator` function which describes a functional/integration test as an independed, so its result is only collected for future report but the whole Test Suite continue running.

2. Should segregate test sections (e.g. `make docker-unittests`, `make docker-infrastructure` etc) as well as allow run everything at once (typical `make all`).

3. Should not affect upstream code get changed in order to run it. All really required changes should be able to perform inside the Test Suite, leaving upstream code untouched.

## Testing Concepts

As of practice, tests themselves are usually boolean "Green"/"Passed", or "Red"/"Failed". Regardless what fails, as long something fails, the Product is considered faulty and has to be fixed in priority action. Therefore, in order to let package update pass to the production, no tests should be allowed as Failed. For that we introduce a concept of a "White List" testing of upstream tests (all kind):

1. Only tests that are relevant to SUSE products (Manager, Storage, SLE etc). Tests like Facebook, Cassandra, OSX, Solaris etc are excluded and ignored.

2. All "flapping" tests are subject of White List. That is, if a test is either broken and has to be fixed or is irrelevant, it is subject to the put off this list.

3. *Strongly preferrable* is a practice where no SUSE-related tests ends up outside of the White List

The White list is **not**:

1. A pool of technical debt for "we will fix this later"

2. Muting trash-bin for failing tests to avoid them run at all

## Three Types of Tests

There should be at least three types or kinds of tests covered:

1. Unit Tests (all upstream)

2. Upstream's integration tests White List

3. SUSE-related integration tests

## State of the Tests

Since the desired state of a test always should be "Green" or "Passed", therefore to achieve this, the following policies should be kept:

1. All upstream tests are not reliable by definition and may fail at any time due to the various external reasons (test is broken or not updated to the latest version, missing fixture etc). It is *strongly preferrable* that the test is not muted but rather fixed and synchronized with the upstream. Do this whenever possible. Muting a previously working upstream test should have a very good solid reason.

2. Since the desired state should be always in passed condition, only SUSE-related tests should be primarily focused at. The second level of the tests has to cover openSUSE-related components, however this should not be a first priority.

3. Therefore all upstream tests that are related to the SUSE products, should run from the White List

4. Therefore if any test from the upstream's white list fails, this is *our* problem

5. Therefore if any test outside the upstream's white list fails, this is *not our* problem

## Invokation and Structure

One framework should cover all test kinds and types. The same framework should be segregated by a type. That should yield to the following:

> For every OS version (i.e. SLE11/SP3, SLE11/SP4, SLE12, SLE12/SP1 and openSUSE Leap 42) should be a separate suite that runs only one type of the test.

That would typically mean at least 5x4 jobs in Jenkins. The Test Suite can have more jobs, in case there is a strong demand to support other distributions in our lab (Debian, CentOS etc), a number of jobs increases.

# Current Framework

Current framework is a set of Bash scripts that is running the following:

1. Infrastructure tests. Not really an integration test, but a response of the Salt components on certain commands and/or environment changes.

2. SUSE-related upstream unit tests on the exact package sources

3. It cannot run on anything else than SLE or Leap

4. Quick ad-hoc solution with ad-hoc tests. Did the job perfectly and released SUSE Manager 3, but time to make it even better.

All the tests are running inside the Docker container and can work in a "debug mode", where Docker can be run with the shell.

# What Is The Target of a New Framework

New framework should do pretty much the same what current one is doing, but also:

1. Run integration tests from the upstream _(NOTE: partially done.)_

2. Run integration SUSE- and openSUSE- related from the in-house.

3. Unify all type of tests under one umbrella.

4. Support any Linux distribution (in a theory). At least we will need CentOS/RHEL for sure because of RES in SUSE Manager program.

# What to Test

Test should cover:

1. An exact patched source from the exact package

2. Current codebase branch

3. An actually installed product (once #1 passes) and its functionality

# Process Improvement

## Motivation

Salt is in SUSE-related products and will be a part of SLE products. Therefore faulty Salt package is very dangerous. At the same time, Salt has a very rapid development and code fixing, hence patches are frequent. Because of that, everyone who is going to support/maintain Salt package should follow one standard instructions and always end up with the same result. Motivation of the maintenance support process is to eliminate:

1. Elements of "one man show", where best practices aren't in the _process documentation_

2. Rely on the strict process, rather then uncertainty

3. Minimize a single point of failure, where everyone can support the package _equally efficient_

4. Test not just Git sources (this is 33% at its best), but the final "baked" package itself.

## Current Problems

Current Salt package support has the following problems:

1. Package is tested _after_ being accepted to the OBS. This leads to overlook e.g. mistakes in `.spec` file that allows package to be built, but breaking other components at runtime/installing time). Instead, package should be accepted already tested.

2. Consequentially of No. 1, the Submit Request of the package is usually accepted by "let's see how Jenkins reacts". This leads to periodic failure e-mails which we get used to ignore. It is therefore very easy to miss a problem that should be addressed _right now_. Instead, any non-green failure in Jenkins should be _always_ treated as a serious problem and reacted immediately.

## The Process Itself

This testing suite is _not_ mandatory for a 3rd party developers, who submits openSUSE-related improvements to the Salt package. This testing suite _is_ mandatory for SUSE-related improvements to the Salt package. Therefore internal testing process should be a _part of_ package release/maintenance and be tightly integrated into Salt package support.

That said, each accepted package maintenance Submit Request should be validated by this testing environment. Salt package is maintained by its own Git repository, which is an officially released tarball + SUSE patches, all kept in the Git repo. Patches are generated by the Git, not manually.

This is the proposal to the integration between Salt package support and testing processes:

1. A fix is placed to the internal Git repository _branch_. Such fix generally should be cherry-picked from the **upstream**, unless the fix is strictly SUSE- or openSUSE- related and is only for the package and is outside the upstream code. Follow the [forkflow and policies](https://github.com/opensuse/salt/wiki) for more details.

2. A Pull Request should be opened against the appropriate main branch, e.g. `openSUSE-2015.8.8`, where patch to the candidate SR resides.

3. Patches are generated from exactly that Pull Request.

4. A package branch from corresponding package on OBS is created and the new patches are added to this branched package from the Git PR's in a typical OBS's routine as usual.

5. A branched package candidate has been committed to the OBS in its revisions and built in contributor's home sub-project along with the Test Suite. Essentially Test Suite should build the package, by triggering first OBS usual build process, then fetching newly locally built packages, installing them into the Docker space as they would be installed from the final repository, and run all the test suite on them. At this stage all test suite errors are strictly isolated only to the contributor, who is dealing with it.

6. Once changes are done and Test Suite passes, package candidate creates Submit Request, its number is should be mentioned in the corresponding Pull Request in the Git (see Step 2).

7. Package now can be submitted to the request only after **this** Test Suite is in state "Green"/"Passed" for further final review (usually double-checking of the correctness of `.changes`, `.spec` file and diff of the added patches. Comment of the SR should contain a Pull Request URL.

8. If package gets accepted to the destination, the Pull Request is merged to the main branch against the package.

9. At this point Jenkins runs **this** Test Suite one more time against the newly built package and should be always in Green/Passed status.

## Effects

The proposed maintenance process does the following changes and improvements:

- No more `systemsmanagement:saltstack:testing` repository in terms of "can be completely broken".

- New repositories: a) `systemsmanagement:saltstack:susemanager` (what is used by SUSE Manager) and b) `systemsmanagement:saltstack:stable` what is used by openSUSE.

- Each update to the `systemsmanagement:saltstack:susemanager` should be reflected by updating it to the internal SUSE Manager repository.

- Everything that goes to these repositories is _already tested_. At this point central Jenkins's job should run **this** Test Suite once again, but merely for the verification purposes (should be always Green/Passed). In case Jenkins job got Red/Failed, this should be _always_ treated as a priority.

- OBS is not multi-tasked, but rather _single-tasked_, where only one package SR can be processed at a time. Very rarely with a very good luck some merge is possible, but this always a big risk. Therefore, we should always treat OBS's SRs are single-threaded. The process should eliminate this race condition clash by an existence of a PR that wasn't merged. If a PR in the Git already exists with an appropriate URL to the package branch that is going to be an SR, no further work should be done unless the Git PR disappears by being either merged or rejected.

- Git repository to the package from which the final package is generated should be write-able only to those people, who can accept OBS SRs.

## Dealing With Third-Party openSUSE-related SR

No trust should be allowed to the third-party openSUSE-related SR from the community. Therefore, _while accepting_ the SR, **this** Test Suite should be applied by the following process:

1. Verify if Git repository contains an appropriate PR and refers to the SR branch in OBS.

2. Verify if the SR is utilising the Git PR and is referring to it.

3. Checkout this package from the user's SR's branch

4. Run the Test Suite by simply rebuilding the branched package with it. The Test Suite shoud rebuild the package, install freshly built locally packages into the docker and run the whole test suite

5. Accept or reject accordingly

6. While rejecting, thorougly describe why this happens and how to fix the problem

7. While rejecting, close the PR with the explanation from No. 6 or merge the PR while accepting

# Roadmap

Currently we are using "suse-tester" Bash-based test suite, that runs a subset of this. Replacement will be consisting of moving all the tests contents to the [PyTest framework](http://www.pytest.org/latest) having available:

- upstream Integration Tests

- upstream Unit Tests

- Internal SUSE- and openSUSE- related Integration Tests

Ideally internal SUSE- and openSUSE- related tests should become upstream. The concept of the "internal tests" would serve a pre-upstream pool of tests and later be put to the upstream, if any possible.

Migration from the current "suse-tester" should be based on demand: all new tests should go to the new framework.

# Drawbacks
[drawbacks]: #drawbacks

## Notes on BDD (Behaviour Driven Development)

While having a good points, overall BDD considered overkill to the current testing process, because:

1. It requires too much verbocity to get to the point: a) story in English, b) parser, then c) an actual test. Apparently, we all (QA, dev) agree that it can be just a nicely documented test.

2. It doesn't scale. At some point, when the test suite gets big and tests are mostly similar or _almost_ same, a little altering or rephrasing is required at the "English level". This often pushes to use English as a programming language, e.g. "If I click on CSS class '.foo' then...". At this point English is started to be used as a yet another programming language. Workaround: split the test. Drawback to the workaround: slow.

3. Use case stories are generally no use for programmers. BDD in general by definition was designed for those, who aren't familiar with programming. The idea is to look at the story and then understand what is happening. Developers and programmers can read just code. Python language is designed to be as readable as English (and if it isn't, it should be!).

4. No area strictly requires BDD. E.g. Unit tests do not require BDD. The integration tests do not require that either as they are basically just a stateful or a stateless unit tests, only at live system level.

5. Not BDD that matters. Green Jenkins's set of jobs, a good test documentation and an easy-readable test Python code does! :-)

However, the used framework (PyTest in this case) should be able to enable the [BDD plugin](https://pypi.python.org/pypi/pytest-bdd) in principle, in case there is a strong valid requirement for it.

## Notes on Running Test Suite Over Package Branch

Main issue is that the culture using OBS is not designed to use it with the Git/testing integrated. Historically, everyone was making patches with any tools they knew. Current approach is relying on the following requirements that not always required or not even popular in use:

1. Patches are _generated_ from the separate Git repository.

2. Patch(-es) aren't going anywhere to the Git repository main trunk, unless OBS SR has been accepted and thus the same person merges the Git PR.

3. Package should be _always_ branched.

## Plans With Upstream

Currently upstream has no good united test suite. Using mainly `nosetest` and some integration tests with own way. With PyTest we are already running their code with no changes. Encapsulating everything into one testing codebase is a good proposal to the upstream.
