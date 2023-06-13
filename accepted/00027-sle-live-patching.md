- Feature Name: Better support SLE-Live-Patching in SUSE Manager
- Start Date: 2016-10-21
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

Reflect new support model in SUSE Manager by supporting SLE-Live-Patching.

# Motivation
[motivation]: #motivation

Live Patching brings a new support model, which Manager should recognize. The support model can be summarized as follows:

*System is in supported state when there is either
latest kernel running or the latest kGraft patch is
active.*

With live patching you can patch a kernel without the need to reboot.
Beside of the regular kernel patches, live-patching provide special
kgraft patches which fixes the same issues but the patches do not have
the `reboot_suggested` flag set.

The procedure should look like this:

## Initial Setup

* customer create clones of the channels
* regular kernel patches are added to the clones only up to the version they want to install on there systems
* kgraft patches are added to the cloned channels
* the customer install the kernel including the latest kgraft patch
* customer reboot the server to hide the "reboot required" banner.

## Live Kernel Update without reboot

* when a new kernel is released, the customer clone the kgraft patch to the cloned channel - **not** the regular kernel patch
* the customer apply the kgraft patch on there systems. No reboot needed.

## Full Kernel Update

* At some later point in time (latest after 1 year - at the next maintenance window when he is allowed to reboot)
  the customer clone the regular kernel patches in the cloned channels
* he update all systems to the new kernel version including the matching kgraft patch.
* he "reboot" the systems.



# Detailed design
[design]: #detailed-design

## Scope

This feature should be implemented only for salt minions.

## Known issues

1. system show old kernel version. It is not visible that this system is patches with kgraft.
1. CVE Audit feature still see a CVE number as "not patched", even if the kgraft patch which list the CVE number is installed
1. Bad visibility of patches which require a reboot like "regular kernel updates"

### Show kgraft patched systems in the UI

The user should see that a system is patched with kgraft. kgraft has a tool which can return the current patch level. We could write a module
which call:

```
$> kgr -v patches
kgraft_patch_2_2_1
    active: 0

kgraft_patch_3_2_1
    active: 1
    RPM: kgraft-patch-3_12_51-60_25-default-3-2.1.x86_64
    CVE: CVE-2016-2384 CVE-2016-0774 CVE-2015-8812 CVE-2015-8709 CVE-2015-8660 CVE-2015-8539 CVE-2013-7446
    bug fixes and enhancements: (none)
```

and return the patch name of the active patch as string. This should be shown in the systems details page behind the kernel version:

```
Kernel: 3.12.51-60.25-default (kgraft_patch_3_2_1)
```

Keep the implementation open for others. RedHat is using a different technology. In case we want to support RedHat,
we might need to call another tool.

### CVE Audit

We need to adapt the CVE Audit feature. This feature look up all channels and will find the regular kernel patches and will show them as
need to be applied. The reason is, that the kgraft patch has a different package list. We need a mapping between kgraft and kernel packages
and use it to not show updates for a kgraft patched kernel.

* kgraft-patch-&lt;version&gt;-&lt;release&gt;-default =&gt; kernel-default = &lt;version&gt;-&lt;release&gt;
* kgraft-patch-&lt;version&gt;-&lt;release&gt;-xen =&gt; kernel-xen= &lt;version&gt;-&lt;release&gt;

Note: version and release in the kgraft patch name replaces dots '.' with underscore '_'.

A regular kernel patch include more packages then the pure kernel like `kernel-macros`, `kernel-devel` and `kernel-syms`.
They are not installed by default and cannot be patched with kgraft. In case they are installed we should see the system
as affected even when the latest kgraft patch is installed.

### Additional information about patches

In order to make it easier for the customer to identify patches which requires a reboot, we should add an icon in the patch list
of the Web UI. A generic infrastructure is recommended to enhance it later with similar information like "update stack patch" or
"EULA available".


# Drawbacks
[drawbacks]: #drawbacks

Why should we *not* do this?

# Alternatives
[alternatives]: #alternatives

What other designs have been considered? What is the impact of not doing this?

# Unresolved questions
[unresolved]: #unresolved-questions

## A kernel patch contains multiple packages. Which of them are fixed by a kgraft patch?

Example packages in a kernel patch:
* kernel-default
* kernel-default-base
* kernel-devel
* kernel-macros
* kernel-source
* kernel-syms
* kernel-xen
* kernel-xen-base
* kernel-xen-devel
* lttng-modules
* lttng-modules-kmp-default

Example Packages in the kgraft patch:
* kgraft-patch-3_12_44-52_18-default
* kgraft-patch-3_12_44-52_18-xen
* kgraft-patch-SLE12_Update_7 (source)

**Answer**: kgraft-patch-&lt;version&gt;-default can patch kernel-default.
kgraft-patch-&lt;version&gt;-xen can patch kernel-xen.

## What should we do with the "regular kernel updates/patches"?

* Show them as "non Important updates" ?
* do not list them at some places ?
* list them in other places ?

**Answer**: we document to use channel cloning and the customer should not provide the regular kernel updates
in the cloned channel. This solve most of the display problems. The only known problem is CVE Audit feature
which must be fixed.

Need to check the following SUSE Manager features. We need to check if they behave correctly:
* spacewalk-report errata-systems
* errata.listAffectedSystems()
* system.getRelevantErrata() and system.getRelevantErrataByType()
* system.getUnscheduledErrata()
* spacecmd: system_listerrata, errata_listaffectedsystems, report_errata
* webUI: Systems list: Updates icon, number of patches and packages
* webUI: System details: status banner
* webUI: Patches =&gt; Relevant
* webUI: Advanced Search
* webUI: CVE Audit

## Showing patch series is "finalized"

**Answer**: Showing patch series is "finalized" cannot be displayed, because there is no design for it in SLE-Live-Patching channel yet.

Live Patching Project Manager: there is a new lifecycle feature which will solve this problem.

This feature is something for a second iteration when the infos are available how things look in the live-patching channel.

# Requirements
[requirements]: #requirements

In the code we had to rely on some namings and behavior of tools. These
dependencies are documented here:

* we support currently 2 kernels with the names:
   * kernel-default
   * kernel-xen
* the live patching names start always with "kgraft-patch" and end
  with the kernel flavor - "-default" or "-xen"

We rely also on the "kgr" tool and its output. We use the following commands:

$> kgr status

we test on the output "ready" before we read the active patch using the command below.

$> kgr -v patches

We expect a line starting with "kgraft" contains the name/version of the live patch.
We also check for "  active: 1" using the following regexp:

```
r"^\s+active:\s*1$"
```

We report the first **active** name to the server and display it in the UI.

See also internal kGraft WIKI page at https://wiki.microfocus.net/index.php?title=SUSE/Labs_Publications/kGraft_Patches
