- Feature Name: OS detection in Salt grains
- Start Date: Tue, 16 June 2016
- Rfc PR:

# Summary
[summary]: #summary

When returning an information from the Salt's grains, data isn't
consistent across different versions of SLE and openSUSE
distributions. 

# Motivation
[motivation]: #motivation

When modules or states or SUSE Manager is trying to detect a
particular OS, grains should be the same in the sense of format and
expected data return. Otherwise it leads to an artificially
conditioned code that is processing the grain's output.

# Detailed design
[design]: #detailed-design

The expected values for each grain variable should yield the followin table:

| Grain |SLE-11-SP3 |SLE-11-SP4 |SLE-12 |SLE-12-SP1 | openSUSE Leap 42.1 | openSUSE Tumbleweed |
| --- | --- | --- | --- | --- | --- | --- |
| `os` | SUSE | SUSE | SUSE | SUSE | SUSE | SUSE |
| `os_family` | Suse | Suse | Suse | Suse | Suse | Suse |
| `osarch` | x86_64 | x86_64 | x86_64 | x86_64 | x86_64 | x86_64 |
| `osfullname` | SLES | SLES | SLES | SLES | Leap | Tumbleweed |
| `oscodename` | SUSE Linux Enterprise Server 11 SP3 | SUSE Linux Enterprise Server 11 SP4 | SUSE Linux Enterprise Server 12 | SUSE Linux Enterprise Server 12 SP1 | openSUSE Leap 42.1 (x86_64) | openSUSE Tumbleweed (20160117) (x86_64) |
| `osrelease` | 11.3 | 11.4 | 12 | 12.1 | 42.1 | 20160117 |
| `osrelease_info` | [11, 3] | [11, 4] | [12] | [12, 1] | [42, 1] | [20160117] |

On the SLE part in the `osrelease` grain the fraction represents a
service pack and on Leap it represents a version (?).

The `os_release_info` should return an array of values, even if there
is only one value.

The data is kept to the semantics of the operating system. I.e. if
there is no Service Pack version (GA, for example), then the
`osrelease_info` will return just one number.

## Caveats

* SLE 11/SP3 do not have `/etc/os-release` which was introduced in the
Service Pack 4 and now is in the SLE 12. For this matter, the
`CPE_NAME` cannot be used.

* Leap values do not make sense compared to Tumbleweed and SLES. All
the values in the `/etc/os-release` differ.
