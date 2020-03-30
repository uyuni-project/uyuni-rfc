- Feature Name: trust-vendor-gpg-keys
- Start Date: 2020-03-25
- RFC PR: https://github.com/uyuni-project/uyuni-rfc/pull/38

# Summary
[summary]: #summary

Provide a secure way to trust GPG keys needed for repository synchronization and later to install packages on Clients.

# Motivation
[motivation]: #motivation

When connecting Uyuni to SCC we provide a Product page where products provided by SUSE can be synced.
But we provide also 3rd party repositories where metadata or packages are singed with not SUSE GPG keys.

We need a way to provide the key and the info which key belong to which repository.
We need a secure way to ask the admin if he wants to trust the key.

After we got the permissions from the admin we can import the key in the keyring and also deploy the key
to clients when they use the channels.

# Detailed design
[design]: #detailed-design

## How to provide the keys?

We should build a package which contains all the keys and get installed as files at `/etc/pki/rpm-gpg/<keyid>.key` ?
The file is a GPG armored key which can also be directly used to import via rpm or apt.
One key per file and named with its keyid.


## How to provide the information?

We can provide extra data with the product_tree for channels which require extra keys.
We would provide the `<keyid>` as value. One value per channel should be enough.
The path to the file and the suffix is hard coded in Uyuni.

A Channel already has values to store `gpg_key_url`, `gpg_key_id` and `gpg_key_fp` (Fingerprint).
We should make use of them.

For product channels we do not need to specify keys when they are in the default key set.

### yum-rhn-plugin and dnf-plugin-spacewalk

The yum-rhn-plugin has a mechanism for accepting keys which uses `gpg_key_url` value of the channel.
It requires that `gpg_key_url` is a file URL and it point to a file below `/etc/pki/rpm-gpg/`.
The file must exist local on the client to get imported.

To not destroy this mechanism which seems to be used on Red Hat clients, we should put our keys in
this directory as well and set the correct URL for the channels.


## How to trust the keys?

When the admin go into the products page and click on synchronizing products, we collect a unique list of keyids
which needs to be accepted. Keys which were already accepted can be skipped.

This should be done by an Ajax call to the backend. We send the channel identifiers and the backend lookup the
keyids, reduce them by keyids already imported and send back detailed information about the ids which needs to be accepted.

The User Interface show a popup and present all keys with User ID and fingerprint and ask the admin if he trust the keys
and if they should be imported. To make it easier we allow only all presented keys or none.
When he answer with "yes", we add the channels and import the keys. For this we call a tool to import the key
to the keyring (`/var/lib/spacewalk/gpgdir/pubring.gpg`) and copy the key to the public web space and to the salt file system
for use them in states and bootstrap scripts.
In case the admin answer with "no", we exit and no product will be added.

We can also import the key in the DB as "Crypto Key" to be used during auto installation
(See Systems => Autoinstallation => GPG and SSL Keys)

In case of `mgr-sync` we need to do the same from the command line. The information about missing GPG keys should be
provided via a XMLRPC API.


## How to update keys?

When keys expire and get extended we need to update them. To do this we should update the key in the package.
The package should get a `post` script which lookup which keys are expired in the keyring. Only for these keys
it try to update them from the new files in the package.


## How to trust keys when using spacewalk-common-channels?

In spacewalk-common-channels we can configure GPG key URLs. We can download the file and present it to the admin
similar to what we do in the User Interface.


# Drawbacks
[drawbacks]: #drawbacks


# Alternatives
[alternatives]: #alternatives


# Unresolved questions
[unresolved]: #unresolved-questions

- What does the security team say?
