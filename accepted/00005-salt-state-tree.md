- Feature Name: Salt State Tree
- Start Date: 2015-11-11
- RFC PR:

# Summary
[summary]: #summary

This RFC specifies

* How SUSE Manager specifies state data to Salt
* How Salt interacts with states defined via SUSE Manager

# Motivation
[motivation]: #motivation

As SUSE Manager integrates more with Salt, it will need to make state data available to the Salt master.

In order to fullfil the following requirements:

* Allow a non Salt user to just use the SUSE Manager user interface, but still have Salt
  do the work.
* Allow an advanced user to utilize the full power of Salt.
* Make easy to implement versioning of state.
* Scalability and being able to offload Salt specific load to a different host.
* Keep the door open to use more advanced features of Salt.

We need to design an specify the interaction between SUSE Manager and Salt regarding State data.

# Detailed design
[design]: #detailed-design

## Static vs Dynamic states

States could be completely dynamic, in the sense that a channels.sls file could be a python script ([see python renderer](https://docs.saltstack.com/en/latest/topics/tutorials/starting_states.html#it-is-all-just-data)) that connects to the database and return the "dictionary" to salt.

This would prevent having the states away from SUSE Manager when creating topologies that help scalability, so it is desired that generated and shipped state data does not need SUSE Manager up and running to be understood by salt. This means any data or file that is needed by the state definition should also be generated to the state tree and not be queried on demand to SUSE Manager.

## Layout

### Location of state data

* *Packaged states*: If SUSE Manager needs to ship state data that does not change unless the product is updated, it will be placed in `/usr/share/susemanager/salt`
* *Generated states*: If SUSE Manager needs to generate state data, it will go to `/srv/susemanager/salt`
* *User states*: States done directly in Salt will be placed in `/srv/salt` or where the vanilla package specifies.

### Layering

In order to "merge" the different sources of state data, a layering based in multiple [file roots](https://docs.saltstack.com/en/develop/ref/file_server/file_roots.html) per environment will be used:

```
file_roots:
  base:
    - /usr/share/susemanager/salt
    - /srv/susemanager/salt
    - /srv/salt
  dev:
    - /usr/share/susemanager/salt
    - /srv/susemanager/salt
    - /srv/salt
    - /srv/salt-dev
```

If the user wants to use multiple environments, they have to include the SUSE Manager file roots. SUSE Manager for now only operates in a single environment.

The layering order means SUSE Manager generated states win over user states. SUSE Manager packaged states win over all the rest.

### Versioning

* *Packaged states* (`/usr/share/susemanager/salt`): those should not be edited manually by users (if they do, they get classic `.rpmnew` behavior and will get no support). Versioning will be standard RPM versioning. We want to keep those to a minimum anyway to avoid making states too Manager-y
* *Generated states* (`/srv/susemanager/salt`): those should not be edited manually by users (if they do, Manager can overwrite any changes at next generation). For technical reasons this directory will be a `git` repo and will be updated by Manager with appropriate commit messages and tags (this allows to refer to specific versions, diff, etc.). Version data comes from the database.
* *User states*: (`/srv/salt`): totally up to users to manage and version those

# Drawbacks
[drawbacks]: #drawbacks

Master version data is in the database, copied to git repos during generation. This means we are replicating some `git` functionality ourselves, OTOH it allows us to keep all of our data in the DB. Alternative would be to have some data in the DB and some in `git` repos.

# Alternatives
[alternatives]: #alternatives

What other designs have been considered? What is the impact of not doing this?

# Unresolved questions
[unresolved]: #unresolved-questions

* How to handle environments and how those fit into SUSE Manager with older concepts like channel assignment?
* How does the file_roots work with other types of state data (eg. reactor sls files?)
