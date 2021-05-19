# Improve the usage of XMLRPC API

The primary goal of this RFC is to highlight the compatibility
concerns of Uyuni and SUSE Manager (SUMA) API usage and to suggest an
improvement in this area.
When the consumers use the API, there must be a way for them to make
sure they call the endpoints correctly (they need to call an existing
method with correct parameters and they also need to make some
assumptions on the return value structure).

TODO keep here? :
The secondary goal is to provide better guidelines for writing scripts
that consume the API in the `API > FAQ` section of the Uyuni/SUMA Web
UI or in the documentation.


## XMLRPC compatibility

Uyuni/SUMA exposes the information about the API and its structure in
3 places:

1. Information about the versions via the `api` XMLRPC endpoint:
   - `getVersion`: the API version, e.g. `25`. This number grows with
   time, but there are no strict rules about it.
   - `systemVersion`: the Uyuni server version (e.g. `4.2.0 Beta1` for
   SUMA, `2021.05` for Uyuni)

2. Furthermore, the `api` namespace also exposes a basic API
   introspection calls describing the structure of the call:
   - `getApiNamespaces`: all API namespaces
   - `getApiNamespaceCallList`: API methods of given namespace
     together with their parameter types, faults and return types
   - `getApiCallList`: all API methods grouped by namespace

3. Faults (retrospective): When the API consumers call a method in a
   wrong way (incorrect parameters, missing method or namespace), they
   get back an XMLRPC fault with code `-1`.  Note: This fault code is
   not reserved solely to report the API calling mismatch cases, but
   is used in other cases (see the`CustomInfoHandler.java` file in
   Uyuni). For instance:
  ```python
  # Non-existing method/wrong method signature
  <Fault -1: 'redstone.xmlrpc.XmlRpcFault: Could not find method: test in class: com.redhat.rhn.frontend.xmlrpc.ansible.AnsibleHandler with params: []'>

  # Non-existing handler
  <Fault -1: 'The specified handler cannot be found'>
  ```


## Existing approach and problems

We must provide a sane way for users to write robust scripts that
target various Uyuni/SUMA versions.

In the `spacecmd` tool, this is done by API version check endpoint
(`api.getVersion` above). The logic simply checks the API version and
reacts accordingly (e.g. warns the user, that given operation is not
supported by the API version).

A similar approach is taken by the `errata-import.pl` script by Steve
Meier [1]. The script contains a list of supported versions and checks
on runtime, whether the API version of the Uyuni/SUMA server is
contained in this list.

This works well, until the user needs to target both Uyuni and SUSE
Manager in their scripts - the API version numbers are not consistent
(API version `25` in Uyuni is currently not the same as version `25`
in SUMA).

Second problem of this approach emerges, when the product developers
forget to bump the API version on breaking changes. In this case, even
a robust client application that thorougly checks the API version can
use an API method in a wrong way.

Tackling these problems has various solutions, described in the
[Solutions](#solutions) section below.


## Note on breaking and non-breaking changes

The API mutates over time, in general there are 3 types of changes:

1. not breaking - growing: adding a new namespace, introducing a new
method in an existing namespace
2. breaking - shrinking: removing a namespace, removing a method from
an existing namespace
3. potentially breaking - modifying:
  3.1 breaking: changing a signature of an existing method
  3.2 breaking: changing a behavior of an existing method
  3.3 non breaking: adding a new field in a structure accepted /
  returned by a method
  3.4 breaking: removing a field in a structure accepted by a method /
  returned by a method


## Solutions

The following section contains a list of solutions to the problems
mentioned above. Some of the the suggestions are only hypothetical,
but they are included anyway, for the sake of completeness.
Choosing an ultimate solution has a direct effect on the API consumers
and we should choose the one, that minimizes the burden (TODO rephrase
this horrible thing).


### Solution 1

- Treat the API versions independent in Uyuni and SUSE Manager. These
  are 2 different projects and version `X` has a different contents
  and compatibility in Uyuni and in SUMA.
- Introduce an API "flavor" under a new `api.getFlavor` method, which
  returns the project name (e.g. `uyuni`/`suse-manager`) read from a
  config file.
- Only "bump" the API versions on breaking changes.
- Increasing API versions within a minor SUMA release is forbidden
  (e.g. SUMA 4.2 API is always backwards-compatible, otherwise it's
  a bug)!
- A CI job watches introducing of breaking changes (it detects and
  report back any changes in the `xmlrpc` java package, unless a "API
  changes in this PR are non-breaking" checkbox is checked by the PR
  author)
- Minor note: Uyuni would typically have higher version number than
  SUMA as the changes there are more frequent, but in some cases (a
  SUMA maintenance update gets released before a new Uyuni release),
  this doesn't need to be true.
- API Consumers would need to introduce a check for the flavor in
  their scripts.

#### Pros
- Trivial implementation on server side

#### Cons
- Tracking non-breaking changes between various SUMA maintenance
  updates is a bit more complex (need to use the API introspection
  calls, e.g. `getApiCallList`).
- Brings complexity to the API consumers and `spacecmd`. The scripts
  would need to check the flavor and the API version.

#### Usage instructions


### Solution 2: No flavor, use `systemVersion` instead

Based on the [Solution 1](#solution-1)

In this case, the API must be stable within a Uyuni/SUMA minor
version. (TODO @hustodemon: ask @moio/@mc, but i think this should be
the case already).

The user scripts could then use the `api.systemVersion` instead of
checking the flavor and API version.

#### Pros
- No implementation needed on the server side

#### Cons
- Version format: the scripts need to consider various corner cases
  (`4.2.0 RC2`, `2021.05`) and would need to make sure they are
  handled correctly by implementing various, possibly error-prone
  comparators in their code.
- Same problem with tracking non-breaking changes like in the
  Solution 1.


### Solution 3: Bump API version on any change in the API

Based on the [Solution 1](#solution-1)

- Same as Solution 1, but the version gets bumped on any (even
non-breaking) change within a product release or a maintenance update.
- Brekaing API within a SUMA maintenance update is still forbidden.

#### Pros & Cons
- Trivial implementation on the server side
- Does not suffer from the first "Cons" of the Solution 1

#### Cons
- Brings complexity to the API consumers and `spacecmd`. The scripts
  would need to check the flavor and the API version.


### Solution 4: Use a `major.minor` versioning scheme

Currently, the API version is an integer. This solution uses 2
integers (or a list of integers in general). The first number
describes the major version, the second one describes the minor
version.

TODO START HERE
Bump the major version on breaking changes (or alternatively with the
product release), break the minor one on non-breaking changes.

For the version we could use increase the major number just with every
SUMA release and the minor number with every change to the API.

After 4.2 release Uyuni would go to 26.01, 26.02, ....
When we release SUMA 4.3 it would inherit the current Uyuni version at that time. Let's say 26.10.
Uyuni would go to 27.01
When we backport features which change the API, SUMA 4.3 would increase the minor version 26.11, 26.12, etc...


TODO: enhance according to mc's comment! Uyuni vs. SUMA backports
CI job with 3 checkboxes, exactly one must be crossed

Sol 1 + introspection has the same advantages.

#### Pros
- Consumers able to track non-breaking changes too

#### Cons
- Frequent changes in minor version
- Does it solve the problem?


### (Hypothetical) Solution 5: Enhance the introspection calls

They would provide complete info about the parameters and the
structure. For each Map or Serializer in params and we would need to
do our best to keep the documentation consintent and the client should
be able to verify if the structure is the expected one prior to the
call.


### (Hypothetical) Solution 6: Enhance the reported exceptions

When the client calls a method in a wrong way, they should get back a
fault with an appropriate code (could vary for different cases like
wrong parameter type or non-existing method).


### (Very hypothetical) Solution 7: Discard Uyuni
Consider Uyuni a rolling software and only support the latest one.


[1]: https://github.com/stevemeier/cefs/blob/master/errata-import.pl



-------------------------------------------------------------------------
WIP AREA BELOW

### Guidelines for writing API consuming applications
- TODO: write a guide for external ppl about the recommended ways to use the api?
  - super safe mode: use introspection + version check
    - should be case for spacecmd -> TODO: guide for devels?
  - pretty safe mode: use introspection
  - cowboy mode: don't use anything, just call it and catch exception

- algorithm
  - -1 handling
    - + introspection
      - + api version


## Process for deprecation and removal API methods
- also breaking changes?

# Unresolved questions
- [ ] remove all TODO
- [ ] decide which solution to take
  - [ ] decide if to implement the CI job
- [ ] decide if to write the guidelines in th API > FAQ page
