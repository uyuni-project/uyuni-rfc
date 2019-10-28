- Feature Name: `mgr-ldapsync`: LDAP sync tool
- Start Date: 2019, Oct 28
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

The `mgr-ldapsync` is a tool that configures and manages users in Uyuni
from a directory service.

# Motivation
[motivation]: #motivation

Uyuni server can authenticate users from LDAP via PAM. For this, users
need to be added to Uyuni with the flag "PAM authentication" and thus
their credentials will be verified via LDAP directory. Synchronisation
tool should transparently synchronise users from certain groups and/or
roles in LDAP and reflect that in Uyuni server, overriding local
changes.

Often LDAP configuration at infrastructures is unpredictable. This
tool should bring certain boundaries and over up most common LDAP
setups for users and their roles management.

# Detailed design
[design]: #detailed-design

The tool should work as an aggregator, collecting users from LDAP and
Uyuni server synchronising them.

## Functionality Aspects

The following functions should be implemented:

- Distinguish between local users in Uyuni and LDAP users.
- Prevent UID clashes between the local users and LDAP users.
- Prevent accidental modification or removal of the local user.
- Flexible support various LDAP schemas, such as eDirectory, POSIX,
  Active Directory etc.
- Role management.
- Dry run mode (preview only).

## Configuration

Configuration should be default in a separate file
`/etc/rhn/ldapsync.conf`. Alternatively, user should be able to
specify own path, in case the default one is not created or used.

The main principle of the tool is to map specific roles and or groups
in LDAP to the roles in the Uyuni server via the configuration. Adding
or removing LDAP users from these groups or roles should reflect in
Uyuni without additional manual changes in the Uyuni server.

Configuration should be just a YAML file and the mapping should
implement a relation between LDAP group to a set of roles from
Uyuni. So each user in LDAP that is a member of such group would
inherit these roles. For example:

```yaml
directory:
  groups:
    cn=sysop,ou=groups,dc=example,dc=com:
      - activation_key_admin
      - channel_admin
      - config_admin
```

The configuration above would allow creating `groupOfNames` class in
LDAP and add users via `member` attribute. As long as DN of that
member is valid LDAP object and is not clashing with the local user in
the Uyuni server, it should be synchronised. Similarly roles LDAP
objects are configured as same as `groups` but via `roles`.

## Frozen Users

Frozen user is a local user in Uyuni, which has verified `org_admin`
privileges (all) and is mentioned as "frozen" in the
configuration. Such user is usually used as an emergency user, in case
LDAP fails to respond and/or authenticate anyone. LDAP synchronisation
should not proceed unless there is at least one "frozen" user.

Frozen users configuration option can be also used to explicitly lock
certain UIDs, even if they are listed in LDAP. In this case "frozen"
UID should be entirely ignored by the `mgr-ldapsync` tool.

Configuration:

```yaml
directory:
  frozen:
    - administrator  # This is the UID
```

## LDAP vs Local Users

The `mgr-ldapsync` should distinguish between LDAP users and Uyuni
users, and operate adding, modifying or removing them only in LDAP
context. As long as the user is not specified in LDAP, it should be
treated as "Uyuni local users" and be ignored therefore.

## Clashed UIDs

Any UID that exists in the Uyuni server but has different
authentication method than PAM or is mentioned as "frozen users"
should be marked as conflicting and therefore ignored.

Conflicting UIDs should be not processed, but reported to the log file
as erroneous. However this should not prevent to process the rest
of the existing users.

However, any UID that has PAM authentication mode configured or is not
mentioned as "frozen user" should be managed by LDAP.

## Usage

Typical use of the `mgr-ldapsync` should be straightforward by
periodically run in cron. In console mode it should also provide a
possibility of "dry-run" where only planning of actions to be taken
will be shown.

The output should be stored either to a configured log file or to the
STDOUT, if requested.

# Drawbacks
[drawbacks]: #drawbacks

N/A

# Alternatives
[alternatives]: #alternatives

Alternative design would be to extend user management in the very
Uyuni server, making it LDAP-aware natively. However, the amount of
changes to the existing code might be very large.

# Unresolved questions
[unresolved]: #unresolved-questions

N/A
