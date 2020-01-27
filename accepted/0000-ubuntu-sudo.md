- Feature Name: automated ubuntu onboarding without need to manually configure sudo
- Start Date: (2020-01-27)
- RFC PR:

# Summary
[summary]: #summary

As Ubuntu clients have no root users enabled by default, we tell the user to manually use visudo to enable a user for Python (i. e. for Salt)
https://opensource.suse.com/doc-susemanager/suse-manager/develop/client-configuration/clients-ubuntu.html#_root_access

This proposal tries to avoid the need to manually configure sudo before being able to bootstrap Ubuntu clients.

# Motivation
[motivation]: #motivation

- Why are we doing this?

Better user experience, make it easier to onboard Ubuntu minions

- What use cases does it support?

Onboarding Ubuntu minions

- What is the expected outcome?

Ubuntu clients should be as easy to onboard as any other client. This means it should be sufficient to just enter the root password in the SUSE Manager UI without also manually configuring the to-be-onboarded Ubuntu minion.

# Detailed design
[design]: #detailed-design

When onboarding a minion via ssh, SUSE Manager asks for a user and password with sufficient privileges. On non-Ubuntu systems this typically is the root user. On Ubuntu systems, there typically is just an ordinary user, but this user can do almost anything via sudo. This user is referred to as "ubuntuser" in this document. Unfortunately it is necessary to supply the user's password to sudo. So currently the SUSE Manager documentation asks the admin to enable some special commands in sudo to be executed even without providing the password. The goal is to do this modification directly from SUSE Manager, so there is no need to manually prepare the system for onboarding.

So the actual workflow would be like this:

SUSE Manager UI asks for user and password like with any other client. The password needs to get stored in some local temporary file, so it can be transferred to the minion without being visible in the process list:

1. umask 0377 && echo $PASSWORD > /run/usr/$UID/pass.txt
2. scp -p /run/usr/$UID/pass.txt ubuntuser@ubuntu-minion.target.system:/run/usr/$UID/pass.txt

Now that the password exists on the minion, the needed modifications to the sudo configuration can be done from the SUSE Manager server by running the following ssh command on the minion:

3. sudo -S sh -c "umask 0377 && echo 'ubuntuser ALL=NOPASSWD: /usr/bin/python, /usr/bin/python2, /usr/bin/python3' > /etc/sudoers.d/00001-susemanager" < /run/usr/$UID/pass.txt

Now the system can be boostrapped like any other client because ubuntuser can do all the needed steps via sudo without password. Finally both copies of the file containing the password are deleted:

4. rm -f /run/usr/$UID/pass.txt && ssh ubuntuser@ubuntu-minion.target.system rm -f /run/usr/$UID/pass.txt

See also https://github.com/SUSE/spacewalk/issues/10246

# Drawbacks
[drawbacks]: #drawbacks

Unknown so far

# Alternatives
[alternatives]: #alternatives

- unknown

# Unresolved questions
[unresolved]: #unresolved-questions

- Unknown
