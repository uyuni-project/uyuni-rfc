- Feature Name: trust-vendor-gpg-keys
- Start Date: 2020-03-25
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

Provide a secure way to trust GPG keys needed for reposyncing and later to install packages on Clients.

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

We should build a package which contains all the keys and get installed as files at `/usr/share/susemanager/gpg-keys/<keyid>.key` ?
or `/srv/www/htdocs/pub/gpg-keys/...` ?

or `/etc/pki/rpm-gpg/...` used by yum-rhn-plugin for trusting GPG keys.

## How to provide the information?

We can provide extra data with the product_tree for channels which require extra keys.
We would provide the `<keyid>` as value. One value per channel should be enough.
The path to the file and the suffix is hardcoded in Uyuni.
The file is a GPG armored key which can also be directly used to import via rpm or apt.

A Channel already has values to store `gpg_key_url` (file URL in /etc/pki/rpm-gpg/ local on clients),
`gpg_key_id` and `gpg_key_fp` (Fingerprint). We should make use of them.

## How to trust the keys?

When the admin go into the products page and click on synchronizing products we collect a unique list of keyids
which needs to be accepted. Keys which were already accepted can be skipped.

For every missing key show a popup and present the key data and the fingerprint and ask the admin if he trust the key
and it should be imported. When he answer with "yes", we can call a tool to import the key to the keyring and maybe
copy the key to the public webspace or salt filesystem to use it in states and bootstrap scripts.

We can also import the key in the DB as "Crypto Key" to be used during autoinstallation
(See Systems => Autoinstallation => GPG and SSL Keys)

In case of `mgr-sync` we need to do the same from the commandline. The information about missing GPG keys should be
provided via a XMLRPC API.


## How to trust keys when using spacewalk-common-channels?

In spacewalk-common-channels we can configure GPG key URLs. We can download the file and present it to the admin
similar to what we do in the UI.


# Drawbacks
[drawbacks]: #drawbacks


# Alternatives
[alternatives]: #alternatives


# Unresolved questions
[unresolved]: #unresolved-questions

- What does the security team say?
