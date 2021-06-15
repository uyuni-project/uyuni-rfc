- Feature Name: Use PTFs in Uyuni
- Start Date: 2021-06-21

# Summary
[summary]: #summary

SUSE want to provide customers PTFs (Product Temporary Fixes) in repositories.
This RFC is about how PTFs will look like and how we can manage and install them on clients.

# Motivation
[motivation]: #motivation

PTFs are Product Temporary Fixes for Service Requests opened by SUSE customers.
The resulting packages are the last released maintenance update plus a patch which fixes the actual issue.

PTFs are made for dedicated customers. This means every customer has different PTF repositories, with different content and fixes for different service requests.

When we provide these PTFs in SUSE Manager as channels, it is easier to roll out the fixes to multiple clients.
We need to take care that the PTFs can be installed, updated and been replaced by a regular maintenance update which contains the fix.

Sometimes SUSE provide also TEST packages. The difference is, that they are just meant for testing on a single system to better identify the problem and gather logfiles.
These packages are not supported and should not rolled out on multiple systems.
It is planned to have them in separate channels. We need to provide a best practice to work with them.
We need to be able to install and update them. Replacing them by a PTF or a maintenance update needs to be possible.

# Detailed design
[design]: #detailed-design

## General PTF design for SUSE OSes

A ptf release consists of multiple rpm packages plus one
master "ptf" package. The master ptf package has two
purposes:

- it allows to easily query which ptfs are installed
  in the system
- it makes sure that all of the installed rpm packages
  come from the same release, i.e. there is no mix up
  between multiple releases are non-ptf package

To do this the master ptf package contains the following
elements (incident 1234, first release):

    Name: ptf-1234
    Version: 1
    Release: 1                 # always 1
    Provides: ptf() = 1234-1
    Requires: (pkg1 = pkg1EVR if pkg1)
    Requires: (pkg2 = pkg1EVR if pkg2)
    ...

I.e. if pkg1 is installed it must be installed with version
pkg1EVR. We do not use `Conflict: pkg1 != pkg1EVR` for SUSE because that
would not work with multiversion packages like the kernel.
But for Non-SUSE systems and packages, which do not support multiversion
packages, we could generate `Conflicts` dependencies.

All packages providing ptf() get blacklisted by the solver,
meaning they can only be installed by a specific solver job
that addresses them. This means that selecting a specific
ptf master package via yast or "zypper in" works, but they
can not be pulled in via dependencies.

Each individual rpm package must require the specific
master ptf package:

    Name: pkg1
    Requires: ptf-1234 = 1-1

This makes sure that the solver cannot pull in the rpm
packages, as that would mean to also pull in the blacklisted
master ptf package.



### Updates

Ptfs can be updated to a new release by calling 'zypper up'.
This will update the master ptf package to some higher
version (e.g. ptf-1234 = 2-1) and also pull in the corresponding
rpm packages.

This should work with any installer.

### Uninstalling ptfs

'zypper rm ptf-1234' will uninstall the ptf and revert back to
non-ptf packages.

We need to check if this is working out of the box or if we need to
implement something in Uyuni to make it work.

### Making sure that no fixes are lost

If all of the bugs fixed by a ptf are also fixed in maintenance
updates, a new ptf release consisting only of the master ptf
package is done:

    Name: ptf-1234
    Version: 3
    Release: 1                 # always 1
    Provides: self-destruct-pkg()
    Requires: (pkg1 >= maintpkg1EVR if pkg1)
    Requires: (pkg2 >= maintpkg2EVR if pkg2)

Updating to this version will make sure that this system will
contain only the fixed packages from the maintenance updates.
The special "self-destruct-pkg()" provides will tell the
solver that this will be a package erase instead of an
install. This means that installing this package will actually
erase the master ptf package.

### Test Packages

Before generating PTFs, SUSE will first create so called TEST packages.
The customer need to test them and report positive result before SUSE make an official supported PTF out of it.

TEST packages should only be installed on dedicated test systems.
Therefor it is important that they get not installed on any system where just the version of the TEST package is higher than the installed one.

Current plan is to ship test packages in separate channels.


## PTFs with Uyuni for SUSE and non SUSE OSes

The general PTF design has 3 key points.

1. A new ptf package to install the PTF.
   
   The "boolean dependencies" are supported in `rpm` since version 4.13.
   This would work for SLE15+ and RHEL8+.
   SLE12 will get a different solution with some enhancements to the solver.
   
   - RHEL 8 and Clones use an rpm version which provide the required syntax.
   - RHEL 7 and Clones cannot use `Requires`, they should use `Conflicts` with the limitation of not supporting multiversion installations.
   - Ubuntu and Debian do not support something like the `if installed` syntax for dependencies, but the `Conflicts` trick should work.
   
   The number of packages which potentially get a PTF for Non-SUSE OSes is very limited. We only ship PTF packages for the Client Tools which
   is a handlul of packages.

2. "All packages providing ptf() get blacklisted by the solver"
   
   This will not be the case for non SUSE operating system.
   For SUSE operating systems this will work on solver level, but not in the Uyuni Web UI.
   
   The solution could be, that we check for the special provides Header of packages and keep them away from calculation for possible update candidates.
   We do this already now for ["Retracted Patches"](https://github.com/uyuni-project/uyuni-rfc/blob/master/accepted/00074-retracted-updates-support.md).
   The packages who belong to a PTF are hidden. Only the master ptf packages are visible. By default they are not installed, but appear in the list of installable packages.
   When a PTF is installed and an update is available, it will be shown as update candidate for the ptf master package. In case of an update, its dependencies will
   automatically install the other packages which are hidden.
   
3. "Self destructing Packages"
   
   While on SUSE OSes this would work out of the box, we need to implement something for non SUSE OSes.
   We could write a state which automatically uninstall all packages which `Provides: self-destruct-pkg()`.
   This would be limited to salt managed systems, but keeping a ptf package installed is not a problem.
   This is just a cleanup step which is not strictly required.


# Drawbacks
[drawbacks]: #drawbacks

- The handling for PTFs for Non-SUSE systems will not be as good as for SUSE systems as we cannot patch the solver behavior.


# Alternatives
[alternatives]: #alternatives

- Do not support Non-SUSE systems and let the users install such packages manually.


# Unresolved questions
[unresolved]: #unresolved-questions

- None so far

# Appendix
[appendix]: #appendix

