* Feature Name: Salt Configuration Management
* Start Date: 2016.01.25

---
# Summary
[summary]: #summary

This RFC proposes how to expose the configuration management functionalities of Salt inside SUSE Manager and viceversa.

# Motivation
[motivation]: #motivation

Salt provides you with very advanced configuration management capabilities that can match systems in very powerful ways, even using attributes at dynamically at the time of the matching.

SUSE Manager already exposes a rich model based on organization and groups to organize systems. Existing customer should be able to see the SUSE Manager semantics in Salt, and use the more powerful capabilities only if necessary.

# Detailed design
[design]: #detailed-design

## The .sls state "catalog"

* Each organization will have in the `Salt` section a link to a state catalog where `sls` files can be defined.
* These files will be then be referenced from other places.
* Goal is to avoid duplication, copy-paste and to incentive reuse vs eg. using a textbox everywhere.
* Each state is stored in the Salt state tree (generated layer).

## The 3 levels of configuration

SUSE Manager will allow to specify state data at 3 different levels:

* Organization
  * In the "My organization" menu section.
* Group
  * In the groups detail page.
* Minion
  * In the minion system page.
 
The order of precedence is (High to Low) `Minion >= Group >= Organization`. States with higher precedence override the effects of states with lower precedence.
Additionally suma builtin states have higher precedence then any custom state to ensure the DB reflects the desired state of a minion.

### Example

* `Org1` wants `vim version 1`
* `Group1` wants `vim version 2`
* `Group2` wants `-`

* `Minion1[Org1, Group1]` wants `vim removed` gets `vim removed`
* `Minion2[Org1, Group1]` wants `vim version 3` gets `vim version 3`
* `Minion3[Org1, Group1]` wants `-` gets `vim version 2`
* `Minion4[Org1, Group2]` wants `-` gets `vim version 1`

## States storage
The sls files created by the user will be saved on disk on the salt-master server.
In `/srv/susemanager/salt/` there will be a directory for each organization:
```
├── manager_org_<id>
│   ├── files
│   │    ... files needed by states (uploaded by users)...   
│   └── <state>.sls
         ... other sls files (created by users)...
```

E.g.:
```
├── manager_org_1
│   ├── files
│   │   └── motd     # user created
│   │    ... other files needed by states ...
│   └── motd.sls     # user created
            ... other sls files ...
```

## Suse manager specific pillars
### org-files-dir
To avoid hardcoding organization id's in sls files, a pillar entry will be added for each organization:
`org-files-dir: <relative path to files>`
This will be available to all minions in that organization.

E.g.:
`org-files-dir: catalog_org_1/files`

Pillar usage example:
```
/etc/motd:
  file.managed:
    - source: salt://{{ pillar['org-files-dir']}}/motd
    - user: root
    - group: root
    - mode: 644
```

## top.sls and group/org pillar generation

Given time contraints for development, the solution will be to use an ext_pillar and tops system.

* An [ext_pillar](https://docs.saltstack.com/en/latest/topics/development/external_pillars.html) module, asked for the pillar data for a specific minion will fetch groups and organizations for that minion in SUSE Manager database and return the data.
* A [tops module](https://docs.saltstack.com/en/latest/topics/master_tops/index.html) which asked for the tops will return the right states given the assignments at the org/group and minion level.

File generation may be an option later if the solution above can't be made work with proxy/syndic.

## Future enhancements

Once the basics are worked on, the following items can be added

* We can add the package state user interface at the group and organization level as well but this leaves some open questions.
  * The proposal is to do it afterwards and just autocomplete from all packages and not offer any checking over the minion level.
* Uploading of sls files to the catalog
* Have some functionality to see `state.show_top` or `state.show_highstate` at minion level. Could be a tab under system -> states.


# Drawbacks
[drawbacks]: #drawbacks

Why should we *not* do this?

# Alternatives
[alternatives]: #alternatives

What other designs have been considered? What is the impact of not doing this?

# Unresolved questions
[unresolved]: #unresolved-questions

* For channels and others, we generate state from the database into the `/srv/susemanager/salt` generated tree.
  * For custom states, we don't have those in the database, so they are not really "generated". Should they go into `/srv/salt` instead?
 * How does org and group map into the generated `top.sls`?
 
