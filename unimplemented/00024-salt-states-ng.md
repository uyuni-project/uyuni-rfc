- Feature Name: SUSE Manager Salt States/Pillar, Next
- Start Date: 21.07.2016
- RFC PR: (leave this empty)

# Unimplemented note

This RFC was not ultimately implemented due to time constraints. It might be revived in future.

# Summary
[summary]: #summary

SUSE Manager integrates its engine into the Salt state/pillar system. This RFC proposes a next iteration to make it simpler, more scalable and robust.

# Motivation
[motivation]: #motivation

The current design has various issues:

* Files are generated.
* It is hard to proxy, cache and scale.
* It suffers from consistency challenges (files are generated from the database).
* The structure of the states is confusing and vulnerable to name clashing.
* We shadow the tops with a static one.

The expected outcome should be:

* Consistent with SUSE Manager data.
* Easy to proxy, cache and no need to trigger "updates".
* Easy to document.

The changes to pillar and tops could be implemented independently of the state files changes and already see some improvements. As the state files changes require more design and there may be more alternative designs, it may make sense to split it out in a separate RFC. They are presented together for inspiration reasons.

The changes to the state files structure could even be implemented in the current file-generation scheme. But this would not add much value, therefore it is only advised if the full proposal is implemented.

# Detailed design
[design]: #detailed-design

## HTTP and Authentication

The basis of the design would be to use standard HTTP end-points everywhere. We know how to cache, proxy and query them.

We want to prevent unauthorized access to the end-points. However, the `salt-master` needs access to them without having a specific user.

### Server-wide authentication

The idea is that the requestor has access to the Spacewalk `server.secret_key` of rhn.conf. A `JWT` token is constructed using this key and the end-point, also having access to it, can verify it.

This restricts end-point access to either a `salt-master` running on the same machine, or the key was explicitly shared (eg. a Proxy setup), or a `JWT` token was shared (with longer expiration).

The end-point receives the token in a HTTP header `X-Mgr-Auth`. For end-points that retrieve data about a specific minion, the JWT also has claims that make it usable to retrieve data for that particular minion only.

## Pillar system

The current pillar system works well, as we use a `ext_pillar` that does not shadow `/srv/pillar/top.sls`.

The proposal is to add a `/rhn/manager/pillar/:id` endpoint that would retrieve the pillar data for a given minion. ([prototype](https://github.com/SUSE/spacewalk/blob/dmacvicar-Manager-3.0-pillar/java/code/src/com/suse/manager/webui/controllers/PillarAPI.java)).

The `ext_pillar` would be rewritten to access this endpoint with the proper authentication. ([Prototype](https://github.com/SUSE/spacewalk/blob/dmacvicar-Manager-3.0-pillar/susemanager-utils/susemanager-sls/modules/pillar/suma_minion.py)).

## Top file

The current static top file has the problem of shadowing the `/srv/salt/top.sls`. This can [be fixed](https://github.com/SUSE/spacewalk/pull/713#issuecomment-233966800) by using a `master_tops` (similar to `ext_pillar`).

However the next step also is to use a endpoint [prototype](https://github.com/SUSE/spacewalk/blob/dmacvicar-Manager-3.0-pillar/java/code/src/com/suse/manager/webui/controllers/TopsAPI.java)), with an appropiate `master_tops` module ([Prototype](https://github.com/SUSE/spacewalk/blob/dmacvicar-Manager-3.0-pillar/susemanager-utils/susemanager-sls/modules/tops/suma_tops.py)).

## States

### Structure

Current model for states is a bit confusing in the sense that it pollutes the tops namespace.

```yaml
base:
  - channels
  - custom_groups
  - certs
  - dummy
  - packages
  - custom_org
  - custom
  - web
```
This comes from the sls structure:

```
/usr/share/susemanager/salt/custom_groups
/usr/share/susemanager/salt/custom_groups/init.sls
/usr/share/susemanager/salt/certs/SLES11_4.sls
/usr/share/susemanager/salt/certs/..
/usr/share/susemanager/salt/certs/RHN-ORG-TRUSTED-SSL-CERT
/usr/share/susemanager/salt/certs/init.sls
/usr/share/susemanager/salt/channels
/usr/share/susemanager/salt/channels/disablelocalrepos.sls
/usr/share/susemanager/salt/channels/init.sls
/usr/share/susemanager/salt/channels/channels.repo
/usr/share/susemanager/salt/custom_org
/usr/share/susemanager/salt/custom_org/init.sls
/usr/share/susemanager/salt/packages/...
/usr/share/susemanager/salt/packages/init.sls
/usr/share/susemanager/salt/custom/init.sls
...
```

```
/srv/susemanager/salt/
/srv/susemanager/salt/manager_org_1
/srv/susemanager/salt/manager_org_1/sumatest.sls
/srv/susemanager/salt/packages
/srv/susemanager/salt/packages/packages_70b1efad220b4fd238867bb2578de1e8.sls
/srv/susemanager/salt/custom
/srv/susemanager/salt/custom/org_1.sls
/srv/susemanager/salt/custom/custom_70b1efad220b4fd238867bb2578de1e8.sls
```

Here it is not clear what states come from SUSE Manager, and the names are pretty generic. However, Salt supports subdirectories. The proposal is to move everything into folders:

```
/usr/share/susemanager/salt/mgr/certs/SLES11_4.sls
/usr/share/susemanager/salt/mgr/certs/init.sls
/usr/share/susemanager/salt/mgr/certs/..
/usr/share/susemanager/salt/mgr/channels/init.sls
/usr/share/susemanager/salt/mgr/channels/...
/usr/share/susemanager/salt/mgr/packages/init.sls
/usr/share/susemanager/salt/mgr/packages/...
/usr/share/susemanager/salt/mgr/group/init.sls
/usr/share/susemanager/salt/mgr/org/init.sls
/usr/share/susemanager/salt/mgr/minion/init.sls
...
```

And the generated part would be:

```
/srv/susemanager/salt/
/srv/susemanager/salt/mgr/orgs/1/init.sls
/srv/susemanager/salt/mgr/orgs/1/foo.sls
/srv/susemanager/salt/mgr/groups/1/init.sls
/srv/susemanager/salt/mgr/minions/70b1efad220b4fd238867bb2578de1e8/init.sls
/srv/susemanager/salt/mgr/minions/70b1efad220b4fd238867bb2578de1e8/packages.sls
```

The new top data merged with the one generated by SUSE Manager would be:

```yaml
base:
  - mgr.certs
  - mgr.channels
  - mgr.packages
  - mgr.org
  - mgr.group
  - mgr.minion
  - dummy
  - web
```

The `mgr.minion` (init.sls) would be (if it has a state from the catalog `foo` assigned)

```
include:
  - mgr.minions.70b1efad220b4fd238867bb2578de1e8
```

The `mgr.minion.$id` would be (if it has a state from the catalog `foo` assigned)

```
include:
  - mgr.orgs.1.foo
```

Another proposal is to remove the "custom" keyword for being to generic, confusing and also confused with '/srv/salt`. The states that are written in the textbox are just state that happens to be in raw form. A possible solution to avoid this ambuiguity given that `mgr.packages` and `mgr.channels` are also `mgr.minion` would be to have `mgr.minion` as the only entry point and include them from there.

So instead of the above tops, to have instead:

```yaml
base:
  - mgr.org
  - mgr.group
  - mgr.minion
  - dummy
  - web
```

The `mgr.minion` would be:

```yaml
include:
  - mgr.channels
  - mgr.packages
  - mgr.minions.70b1efad220b4fd238867bb2578de1e8
```

and `mgr.minion.70b1efad220b4fd238867bb2578de1e8` would be:

```yaml
include:
  - mgr.orgs.1.foo
```

### Retrieving states

Similar to the proposal of pillar and tops, the idea would be to have SUSE Manager access the states via an end-point. A corresponding `salt.fileserver` module would be implemented.

Also, if a popular protocol is implemented (eg. S3), then the plain `s3` module could be used.

#### Technical limitations

`file_backends` support multiple backends, but the order is first defined by the backend type, then for the roots inside the backend, so it is not possible to have this order:

* file_root /usr/share/susemanager/salt
* manager endpoint (from database)
* file_root /srv/slat

Some hack would need to be there. Eg. copy/link the `roots` module into another backend (eg `roots2`) and then use it in the backend priority list.


# Drawbacks
[drawbacks]: #drawbacks

* For smaller loads, this may be a slower

# Alternatives
[alternatives]: #alternatives

What other designs have been considered? What is the impact of not doing this?

# Unresolved questions
[unresolved]: #unresolved-questions

What parts of the design are still TBD?
