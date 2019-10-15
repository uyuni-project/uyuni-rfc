- Feature Name: Saltclass as external pillar mechanism
- Start Date: 2019-08-20
- RFC PR:

# Summary
[summary]: #summary

Enhance/replace current custom external pillar mechanism with upstream provided Saltclass module.

# Motivation
[motivation]: #motivation

SUSE Manager needs a way how to export data about systems, groups, services etc. to the salt configuration management. In current implementation this is done by custom python script [suma_minion.py](https://github.com/uyuni-project/uyuni/blob/master/susemanager-utils/susemanager-sls/modules/pillar/suma_minion.py) used by salt master leveraging its external pillar mechanism. This worked so far very well, even allowing Uyuni some extra tricks like integration of Formulas with Forms mechanism. However the implementation has also some limitations preventing further growth.

This RFC proposes to, at first, enable yet another external pillar mechanism in the salt, but this time not a custom script, but salt's own [saltclass](https://docs.saltstack.com/en/latest/ref/pillar/all/salt.pillar.saltclass.html) mechanism.

Examples of limitations of our external pillar implementation:
- allows only static pillars (no jinja preparsing, no pillar dependencies on other pillars)
- problematic data merging
- made integration of formulas easy, but causes duplication of code where i.e. form.yml is parsed on both java and python level

# Detailed design
[design]: #detailed-design

There are three choices how to address the introduction of saltclass to the SUSE Manager:

A) Enable concurrent usage of both custom `suma_minion.py` and `saltclass` external pillars
B) Enable concurrent usage of both custom `suma_minion.py` and `saltclass` external pillars, but with the target to gradually migrate from `suma_minion.py` to `saltclass`.
C) Do the one time migration and switch from custom `suma_minion.py` to `saltclass`

## What means migrating from suma_minion.py to saltclass?

Even in its relative simplicity `suma_minion.py` does more then just loading `yaml` files and exporting to the `salt` ecosystem. `suma_minion.py` is also integral part of the Formulas with Forms enablement in the SUSE Manager/Uyuni.

`suma_minion.py` responsibilities regarding formulas are:
- read what formulas are enabled for given minion and prepare `formulas` grain which is then used by `mgr_tops`, respectively `formulas.sls` loader to apply formulas as part of highstate
- read formulas `json` data and `form.yml` and construct complete pillar information

Complete migration from `suma_minoni.py` to `saltclass` then means:
- implement Formulas with Forms enablement in other way then in external pillar, preferably in java code itself as the current implementation causes triplication of the formulas enablement code
- make current minion pillars accessible to `saltclass`
- make images pillars accessible to `saltclass`

## Are conflicts between existing suma_minion pillars and saltclass pillars possible?

Our external pillar implementation fortunately looks only for files with `pillar_` prefix and following minion id with `.yml` extension:
```python
# Including generated pillar data for this minion
data_filename = os.path.join(MANAGER_PILLAR_DATA_PATH, 'pillar_{minion_id}.yml'.format(minion_id=minion_id))
```
Saltclass on the other hand looks (recursively) for files with names matching minion id with `.yml` extension.

These two formats are thus living in separate namespaces and conflicts are then improbable for minions.

There is no mechanism how to provide group pillars except formulas and those currently live in different directory (`/srv/susemanager/formula_data/`).

> **NOTE**
> In the next sections I use term `existing pillar data` to refer to pillar data loaded by `suma_minion.py` and term `saltclass pillar data` to refer to pillar data loaded by saltclass.


## Step 1: Enablement of saltclass

Our external pillar implementation consist of [suma_minion.py](https://github.com/uyuni-project/uyuni/blob/master/susemanager-utils/susemanager-sls/modules/pillar/suma_minion.py) and its enablement in [susemanager.conf](https://github.com/uyuni-project/uyuni/blob/master/spacewalk/setup/salt/susemanager.conf#L58).
Similiar mechanism will be used to enable `saltclass` in salt master as specified in [saltclass documentation](https://docs.saltstack.com/en/latest/ref/pillar/all/salt.pillar.saltclass.html). As a saltclass root path I propose to continue with using `/srv/susemanager/pillar_data/`.

Configuration snipped for concurrent usage of `suma_minion.py` and `saltclass`:
```yaml
ext_pillar:
  - suma_minion: True
  - saltclass:
    - path: /srv/susemanager/pillar_data
```

Notice that `saltclass` root path is the same ( `/srv/susemanager/pillar_data/` ) as used in `suma_minion.py`.

## Step 2: Switching necessary parts to use saltclass

As a necessary parts are considered image pillars and Formulas with Forms integration.
Image pillars because of https://github.com/SUSE/spacewalk/issues/8337 and Formulas with Forms integration because of need to remove code duplication, solve some corner cases when data merging did not provide correct values ( https://github.com/SUSE/spacewalk/issues/8367 ), yomi enablement if implemented ( https://github.com/SUSE/spacewalk/issues/8367 ) and can lead to simplification of saltboot mechanism as well.

The major motivator in these cases is the jinja preparsing of the pillar data.

### Changes in Formulas with Forms implementation

1) Make FormulaFactory.java to store not just raw `json` data, but complete pillar structure as `saltclass pillar data`
   This formula pillar will be stored as a `saltclass` `class` data and then included from `saltclass pillar data `of minion (this step may conflict with below mentioned Step 2b about migrating `existing pillar data`)
2) If `saltclass` is also enabled as a tops module, minion `saltclass pillar data` can contain a list of state names to be included in the highstate. If `saltclass` is not enabled as a tops module then I recommend to keep this functionality in the `suma_minion.py` for this round of implementation.

> **NOTE**
>Choosing `saltclass` to be also enabled as a tops module and using it to load formulas can make implementation of https://github.com/SUSE/spacewalk/issues/9490 and https://github.com/SUSE/spacewalk/issues/2714 considerably harder.

3) Adapt FormulaFactory.java to load data for formula directly from pillars instead of using custom `json` file.

### Changes for image pillars are

1) Adapt SaltStateGeneratorService.java to store pillar data as a `saltclass` `class` and enable it for all minions
2) Migrate existing image pillars to saltclass classes

## Step 3: Migrating existing pillar data to use satlclass

Migrating existing pillar data will require two steps:
1) Modification of java code storing minion pillars:
  - drop `pillar_` prefix from pillar files
  - store pillar data under `pillar` key
2) Rename existing pillar files from `pillar_{minion_id}.yml` to `{minion_id}.yml`

# Drawbacks
[drawbacks]: #drawbacks

## Big refactoring underway, but stalled

There is an upstream pull request about major `saltclass` refactoring - https://github.com/saltstack/salt/pull/52407 - however this PR seems to be stalled. This PR meant to fix several issues and fulfil couple of feature requests.
The unknown is if the PR will be ever finished or if we can invest and try to finalize it ourselves. It is possible that the work stopped only temporarily due to changes in salt releases, or that the author being external contributor chose to abandon the effort.

## Performance impact

Including another pillar engine can have a negative performance impact. (#TODO measure)

## More complexity means more break points

Generally when running more complex code, there is bigger room for bugs. SaltClass it maintained by the Salt upstream and as of now have 19 issues opened against saltclass (counting both saltclass tops and pillar modules)

## Modifying core functionality

Pillar system is core functionality everything else depends on. Bugs within SaltClass can affect whole product. However proposed granular introduction of SaltClass instead of ```suma_minion``` should limit impact to only specific areas, hopefully providing enough time to catch and debug issues.

## Upstream breakages, abandonment

There is always some risk that upstream may decide to abandon SaltClass. So far maintaining SaltClass should be cheap, due to upstream involvement, but if the upstream decides for any reason to abandon SaltClass the cost of maintenance can increase dramatically (up to impossible if upstream decides to abandon it for some deep design reasons). As a mitigation there is a possibility to use [reclass](https://reclass.pantsfullofunix.net/) upon which SaltClass is based and shares storage details (see below).

# Alternatives
[alternatives]: #alternatives

## Implement custom jinja processing of pillars

The major driver for `saltclass` is the ability to preparse pillars with jinja and also to reference pillars between each other. This can be implemented within existing `suma_minion.py` external pillar as well. Using `saltclass` saves us the development time in exchange for development time on integration, but given `saltclass` is an upstream project it in theory can help with maintenance.

## Use original reclass instead

Instead of salt native implementation there is an option to use the original [reclass](https://reclass.pantsfullofunix.net/) with the [reclass](https://docs.saltstack.com/en/latest/ref/pillar/all/salt.pillar.reclass_adapter.html) adapter. This can be used again as just external pillar or external tops as well.
Drawback is need of another python package and that `reclass` itself seems to be abandoned (last commit is from 2015). There is newer fork in salt-formula git repository - https://github.com/salt-formulas/reclass (last commit from January, 2019), however from the issue list this one seems to have a problem with Python 3.6 and newer.

# Unresolved questions
[unresolved]: #unresolved-questions

* performance impact
* status of the upstream refactoring
