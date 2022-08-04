- Feature Name: Replace Salt Toaster
- Start Date: 2022-08-03

# Summary
[summary]: #summary

Replace Salt Toaster with an approach that's less complicated and uses
existing tools we know.

# Motivation
[motivation]: #motivation

<!-- - Why are we doing this? -->
<!-- - What use cases does it support? -->
<!-- - What is the expected outcome? -->

<!-- Describe the problem you are trying to solve, and its constraints, without
coupling them too closely to the solution you have in mind. If this RFC is not
accepted, the motivation can be used to develop alternative solutions. -->

Salt Toaster was developed a few years ago and filled a gap in the Salt world.
Over the last years, maintaining the downstream `suse.tests` was too much effort
-- so much that we didn't do it. Maintaining the docker images that Salt Toaster
uses to run the upstream test suite against our patched Salt grew into a bigger
and bigger task. We didn't keep up with upstream's changes to the test
dependencies and use a number of workarounds to still run a test suite.

At the same time, Salt upstream improved their test suite a lot. They added new
test types and now have a similar test framework to Salt Toaster. 

The purpose of this change is to lessen our maintenance burden and to be good
open-source citizens that collaborate with our upstream project when it comes to
testing Salt. Additionally, we have knowledge about running a test suite within
our team that we want to take advantage of.

# Detailed design
[design]: #detailed-design

<!-- This is the bulk of the RFC. Explain the design in enough detail for
somebody familiar with the product to understand, and for somebody familiar with
the internals to implement. -->

<!-- This section should cover architecture aspects and the rationale behind
disruptive technical decisions (when applicable), as well as corner-cases and
warnings. Whenever the new feature creates new user interactions, this section
should include examples of how the feature will be used. -->

## Overview

The Salt upstream test suite is executed in virtual machines (VMs) that run the
different operating systems we support. These VMs are set up with sumaform.
Terracumber triggers terraform to create the VMs from within a Jenkins job and
launches the test suite, connecting to each VM over SSH. Salt and the test suite
are installed in the VM via a Salt Bundle that includes the tests.

Pull Request tests are handled slightly different, using a Container containing
the test dependencies. Management of the dependencies is not done through a
Dockerfile that lists all dependencies, instead the dependencies are pulled in
via RPM dependencies.

## Provisioning Test VMs with Sumaform

A new module "salt\_testenv" is added to sumaform. This module defines a new
role, "salt\_testenv", and the default values needed to run all test suites,
e.g. 4GiB of RAM. Sumaform installs the test suite from an RPM/Deb package.
This package is, in most cases, a special Salt Bundle flavor that includes the
test suite and its dependencies. Only for SLE 15, we additionally use a Salt
sub-package that only contains the test suite. This sub-package pulls in the
test dependencies via RPM dependencies.

## Provisioning Test VMs for GitHub Actions

GitHub Actions use so-called runners, which are VMs running Windows, macOS or
Linux. It is possible to host your own runners, but we currently neither do not
do that. We can't use sumaform to provision GitHub-hosted runners, so GH Actions
will use a different approach.

Since the GitHub-hosted Linux runners only run Ubuntu, we will use a Docker
container that is based on openSUSE Leap (latest version). This container's
Dockerfile installs a Salt sub-package that pulls in all required test
dependencies. The container image can be build in OBS, which will automatically
rebuilt it when included packages change.

### Alteratives

We could package the test suite and the dependencies as ".deb" packages instead
of running a Leap-based container in GitHub Actions. This might be less overhead
when running the tests, but adds the overhead of maintaining ".deb" packages of
all test dependencies.

Using the Salt Bundle flavor that we install in the Sumaform-provisioned test
VMs could be an option, but then we would need to move the application and test
code into the bundle.

## Terracumber

Terracumber is a tool used by our QE squad to operate terraform and cucumber for
their regular test suite executions. The same tool can be extended to set up the
required VMs and start the Salt test suite execution.

## Executing the Salt Test Suite

While upstream uses `nox` to set up a Python virtual environment with all
required dependencies, we run the test directly on the system. The reason for
not using `nox` is that would require too much effort to work around it
installing Python packages with `pip`. `nox` does not use our packaged
dependencies, which means we test a different program than we ship.

The Python testing framework `pytest` is used to run the tests. We tell `pytest`
which tests to run by passing the paths to the respective test group (e.g.
"unit") and by deselecting those tests we define in our skip list. 

### Test Script

A test script that passes the correct arguments makes it easy to run the same
test selection in different environments: locally on a developer's machine, in
Jenkins or in GitHub Actions on Pull Requests. The script is simple on purpose.
It takes a configuration file that maps test group names to the test locations
and includes a skip list, one for each test group.

Example:
```sh
$ cat test_config.yml
groups:
  unit:
    tests_dirs:
      - tests/pytests/unit
      - tests/unit
    skipped_tests:
      - tests/unit/flaky.py::flaky_func
$ test_script unit
-> pytest --deselect=tests/unit/flaky.py::flaky_func tests/pytests/unit tests/unit
```

### Skipping Tests

Causing a new test failure needs to feel bad. Turning a test result from green
to red is a strong signal that either the product code or the test code has not
reached an acceptable quality level yet. At the same time, we inherit flaky
tests from upstream and don't have the time to fix them. These tests can be
skipped to keep the overall test results green. But we need to be careful: when
skipping tests is more convenient than fixing them, we risk skipping too many --
which directly lowers the value we get from running tests in the first place.
Adding a test to the "skip list" is as big of a bad smell as is turning the
result red.

The skip list is maintained in a GitHub repository. All changes must be
peer-reviewed and accepted by the rest of the Salt maintainers. Optionally, we
can use a GitHub Action to set hard upper limits on the number of skip list
entries. The purpose of this strict process is to nudge developers towards
fixing test code over skipping failing tests.


### Test Groups

We follow upstream's tests. At this time, there are four test groups. In this
list they are sorted by how close they are to a production environment, in
increasing order.
1. `unit`
1. `functional`
1. `integration`
1. `scenario`


### Operating Systems Covered

The list of operating systems covered by our test suite will change. At the time
of writing this RFC, Uyuni
[supports](https://www.uyuni-project.org/uyuni-docs/en/uyuni/client-configuration/supported-features.html)
the following operating systems:
- SLE (all supported versions and SPs)
- openSUSE Leap (all supported versions)
- RHEL and clones (7, 8, 9)
- Debian (10, 11)
- Ubuntu LTS (18.04, 20.04, 22.04)

We build the special "Salt Bundle for Testing" flavor for all supported
operating systems, since different operating systems hit different code paths.
We don't have to run all tests on all operating systems, but we need to execute
those tests that can find OS-specific defects (e.g. grains tests). This special
Bundle contains Salt, Salt's dependencies, Salt's test suite, and test
dependencies.

For SLE 15 and Leap 15.x, we additionally build a Salt sub-package that contains
only the test suite as well as `Requires` relationships on the test
dependencies. This sub-package is used in Jenkins for SLE 15 and in GH Actions
on Pull Requests, using a Container that includes the Leap build (in practice,
since Leap 15.4 we don't build separate packages).

# Drawbacks
[drawbacks]: #drawbacks

<!-- Why should we **not** do this? -->

<!--   * obscure corner cases -->
<!--   * will it impact performance? -->
<!--   * what other parts of the product will be affected? -->
<!--   * will the solution be hard to maintain in the future? -->
- This approach directly depends on multiple projects (sumaform, terracumber)
  and requires more coordination than Salt Toaster which is 100% controlled by a
  small group.
- This approach adds complexity on the already somewhat-complex packaging setup.

# Alternatives
[alternatives]: #alternatives

<!-- - What other designs/options have been considered? -->
<!-- - What is the impact of not doing this? -->
Keep the Salt Toaster approach: Tests are executed inside Docker containers,
which we build from generated Dockerfiles. The Dockerfile generation is based on
Jinja2 templates. We could do a throughout clean up of the templates and
simplify the process, but in the end we would still maintain Dockerfiles.

# Unresolved questions
[unresolved]: #unresolved-questions

- How often do we run which test group?
- Which test groups do we run where?
- What hardware do we need to request? VMs need at least 4GiB to run the
  integration tests
