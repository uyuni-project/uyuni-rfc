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

PTFs are made for dedicated customers. This means every customer has different PTF repositories, with different 
content and fixes for different service requests.

When we provide these PTFs in SUSE Manager as channels, it is easier to roll out the fixes to multiple clients.
We need to take care that the PTFs can be installed, updated and been replaced by a regular maintenance update which 
contains the fix.

Sometimes SUSE provide also TEST packages. The difference is, that they are just meant for testing on a single system 
to better identify the problem and gather logfiles. These packages are not supported and should not roll out on 
multiple systems. It is planned to have them in separate channels. We need to provide a best practice to work 
with them. We need to be able to install and update them. Replacing them by a PTF or a maintenance update 
needs to be possible.

# Detailed design
[design]: #detailed-design

## General PTF design for SUSE OSes

A PTF release consists of multiple rpm packages plus one master "PTF" package. The master PTF package has two purposes:

- it allows to easily query which PTFs are installed in the system;
- it makes sure that all the installed rpm packages come from the same release, i.e. there is no mix up
  between multiple releases are non-PTF package.

To do this the master PTF package contains the following elements (incident 1234, first release):

```
Name: ptf-1234
Version: 1
Release: 1                 # always 1
Provides: ptf() = 1234-1
Requires: (pkg1 = pkg1EVR if pkg1)
Requires: (pkg2 = pkg1EVR if pkg2)
...
```

I.e. if pkg1 is installed it must be installed with version pkg1EVR. We do not use `Conflict: pkg1 != pkg1EVR` for
SUSE because that would not work with multi-version packages like the kernel. 
For Non-SUSE systems and packages, which do not support multi-version  packages, we could generate `Conflicts` 
dependencies.

Each individual rpm package part of the PTF must require the specific master PTF package:

```
Name: pkg1
Requires: ptf-1234 = 1-1
Provides: ptf-package()
```

This makes sure that the solver cannot pull in the rpm packages, as that would mean to also pull in the blacklisted
master PTF package. They also provide `ptf-package()` so they can be easily identified.

All packages providing `ptf()` get blacklisted by the solver, meaning they can only be installed by a specific solver
job that addresses them. This means that selecting a specific PTF master package via yast or "zypper in" works, but 
they can not be pulled in via dependencies.


### Updates

PTFs can be updated to a new release by calling 'zypper up'. This will update the master PTF package to some higher
version (e.g. PTF-1234 = 2-1) and also pull in the corresponding rpm packages.

This should work with any installer.

### Uninstalling PTFs

'zypper rm PTF-1234' will uninstall the PTF and revert back to non-PTF packages.

We need to check if this is working out of the box or if we need to implement something in Uyuni to make it work.

### Making sure that no fixes are lost

If all the bugs fixed by a PTF are also fixed in maintenance updates, a new PTF release consisting only of the 
master PTF package is done:

```
Name: ptf-1234
Version: 3
Release: 1                 # always 1
Provides: self-destruct-pkg()
Requires: (pkg1 >= maintpkg1EVR if pkg1)
Requires: (pkg2 >= maintpkg2EVR if pkg2)
```

Updating to this version will make sure that this system will contain only the fixed packages from the maintenance
updates. The special "self-destruct-pkg()" provides will tell the solver that this will be a package erase 
instead of an installation. This means that installing this package will actually erase the master PTF package.

### Test Packages

Before generating PTFs, SUSE will first create so called TEST packages. The customer need to test them and report
positive result before SUSE make an official supported PTF out of it.

TEST packages should only be installed on dedicated test systems. Therefore, it is important that they get not 
installed on any system where just the version of the TEST package is higher than the installed one.

Current plan is to ship test packages in separate channels.


## PTFs with Uyuni for SUSE and non SUSE OSes

The general PTF design has 3 key points:

1. a new PTF master package to install the PTF;
2. multiple packages that are part of the PTF;
3. a self-destruction package.

For SUSE operating systems they will all be handled on solver level, but for Uyuni Web UI they will need a special 
treatment.

### PTF Master package 

The user shall not be able to interact directly in the UI only the master PTF packages. By default, if a system is 
subscribed to a channel that contains one or more PTF, they will not be installed, but they will appear in the list 
of installable packages. If a PTF is installed and an update is available, the new version will be shown as 
an update candidate for the PTF master package.

The package itself needs to be handled correctly by any non SUSE client. The "boolean dependencies" are supported in 
`rpm` since version 4.13. This means they should work for SLE15+ and RHEL8+. SLE12 will get a different solution with 
some enhancements to the solver. In addition:
   
   - RHEL 8 and Clones use a rpm version which provide the required syntax;
   - RHEL 7 and Clones cannot use `Requires`, they should use `Conflicts` with the limitation of not supporting
     multi-version installations;
   - Ubuntu and Debian do not support something like the `if installed` syntax for dependencies, but the `Conflicts`
     trick should work.
   
The number of packages which potentially get a PTF for Non-SUSE OSes is very limited. We will only ship PTF packages
for the Client Tools, which is a handful of packages.

### Packages part of the PTF

All the packages that are part of a PTF cannot be operated directly, and the UI must prevent that. This means that all 
the packages providing `ptf-package()` must be hidden when checking for install/update candidates. This is similar
to the behaviour we currently implement for ["retracted patches"](https://github.com/uyuni-project/uyuni-rfc/blob/master/accepted/00074-retracted-updates-support.md)

In particular, PTF packages can be identified by the special provides value `ptf-package()` available in the header. 
This will allow the web UI to manage PTF differently, depending on the context. In detail, when working on a system:

- there are not listed as installable packages;
- they are not shown as update candidates for both normal and ptf packages, even if their version is higher;
- if they are currently installed, they are listed, but they aren't selectable for removal.

All these operation, in fact, will be executed automatically when the master package is installed, updated or removed. 

On the other hand, when inspecting the packages associated with a channel, they will be visible as normal packages.

The same result should be expected by the APIs, and any attempt to install or remove a PTF package directly will 
generate a new specific fault.

In order to obtain these new behaviours, multiple queries need to be adapted. To facilitate this refactoring, a new 
database view will list only the packages that do not contain the special `ptf-package()` header. This new view
will have the same structure as the existing `rhnpackage` table, and it will act as a simple "drop-in" replacement 
that might be used in any query where PTF packages must not be visible.

### PTF self-destruction packages
   
While on SUSE OSes this would work out of the box, we need to implement something for non SUSE OSes. We could write 
a state which automatically uninstall all packages which `Provides: self-destruct-pkg()`. This approach, though, would 
be limited to salt managed systems. In any case, keeping a PTF package installed is not a problem as this cleanup step 
is not strictly required.


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

