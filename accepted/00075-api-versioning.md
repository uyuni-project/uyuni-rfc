# Improve the usage of XMLRPC API

The primary goal of this RFC is to highlight the problems of writing
client applications or scripts compatible with multiple versions of
Uynui and SUSE Manager (SUMA) API and suggest an improvement in this
area.

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
   - `getVersion`: the API version, e.g. `25`. This integer grows with
   time, but there are no strict rules about it.
   - `systemVersion`: the Uyuni server version (e.g. `4.2.0 Beta1` for
   SUMA, `2021.05` for Uyuni)

2. Furthermore, the `api` namespace also exposes basic API
   introspection calls describing the structure of the call:
   - `getApiNamespaces`: all API namespaces
   - `getApiNamespaceCallList`: API methods of given namespace
     together with their parameter types, faults and return types
   - `getApiCallList`: all API methods grouped by namespace

3. Faults (retrospective): When the API consumers call a method in a
   wrong way (incorrect parameters, missing method or namespace), they
   get back an XMLRPC fault with code `-1`.
   For instance:
   ```python
   # Non-existing method/wrong method signature
   <Fault -1: 'redstone.xmlrpc.XmlRpcFault: Could not find method:
   test in class: com.redhat.rhn.frontend.xmlrpc.ansible.AnsibleHandler with params: []'>

   # Non-existing handler
   <Fault -1: 'The specified handler cannot be found'>
   ```
   Note: This fault code is
   not reserved solely to report the API calling mismatch cases, but
   is used in other cases (see the`CustomInfoHandler.java` file in
   Uyuni).

## Existing approach and problems

We must provide a sane way for users to write robust scripts that
target various Uyuni/SUMA versions.

In the `spacecmd` tool, this is done by API version check endpoint
(`api.getVersion` above). The logic simply checks the API version and
reacts accordingly (e.g. warns the user, that given operation is not
supported by the API version).

A similar approach is taken by the `errata-import.pl` script by Steve
Meier
[1](https://github.com/stevemeier/cefs/blob/master/errata-import.pl). The
script contains a list of supported versions and checks on runtime,
whether the API version of the Uyuni/SUMA server is contained in this
list.

This works well, until the user needs to target both Uyuni and SUSE
Manager in their scripts - the API version numbers are not consistent
(API version `25` in Uyuni is currently not the same as version `25`
in SUMA).

Second problem of this approach emerges, when the product developers
forget to bump the API version on breaking changes. In this case, even
a robust client application that thorougly checks the API version can
use an API method in a wrong way.

Tackling these problems has various solutions, described in the
[Solution proposals](#solution-proposals) section below.


## Note on breaking and non-breaking changes

The API mutates over time, in general there are 3 types of changes:

1. growing (not breaking): adding a new namespace, introducing a new
method in an existing namespace
2. shrinking (breaking): removing a namespace, removing a method from
an existing namespace
3. modifying (potentially breaking):
  1. breaking: changing a signature of an existing method
  2. breaking: changing a behavior of an existing method
  3. non breaking: adding a new field in a structure accepted /
  returned by a method
  4. breaking: removing a field in a structure accepted by a method /
  returned by a method


## Solution proposals

The following section contains a list of solutions to the problems
mentioned above. Some of the the suggestions are only hypothetical,
but are included anyway, for the sake of completeness.


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
- A CI job watches introducing of breaking changes (more details
  below)
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

Bump the major version with the product release, bump the minor one on
non-breaking changes.

The version bumping is described by this example:
- After SUMA 4.2 release (API version is `25`) Uyuni bumps the version
  to `26.01`
- On SUMA 4.3 release, the SUMA API version gets set to the current
  Uyuni API version at that time, e.g `26.10`
- Uyuni API version gets increased to 27.01
- On backporting features from Uyuni which change the API, SUMA 4.3
  increases the minor version `26.11`, `26.12`, etc...


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


### Solution 6: Enhance the reported exceptions

When the client calls a method in a wrong way, they should get back a
fault with an appropriate code (could vary for different cases like
wrong parameter type or non-existing method).


### (Very hypothetical) Solution 7: Discard Uyuni
Consider Uyuni a rolling software and only support the latest one.


## CI Job

In order to minimize the risk of missing the increase of the API
version, a CI job must be implemented, that reminds the PR author,
when there is a change in the API code:

- Introduce a new section in the Uyuni/SUMA Pull Request template with
  a checkbox with this text "XMLRPC changes do not require API
  version bump / Release engineer has been informed", unchecked by
  default
- If there are code changes in the `xmlrpc` java package and the
  checkbox is unchecked, the CI bot raises an alert. The author of the
  PR needs to:
  - either make sure their changes are not breaking the API
  - or inform interested people responsible for bumping the API version
  and check the checkbox.

When [Solution 4](#solution-4) is chosen, this needs to be adjusted to
cover the minor version bump as well.


## API usage guidelines

The documentation about consuming the API should be enhanced according
to chosen solution. The API users can choose the level of safety of
calling the API and consider the risks themselves:

TODO: adjust the following to the chosen solution. The following text
is just a skeleton that needs to be ehnanced.
TODO: mention also that levels are not mutually exclusive

### Level 0: No checking
API consumers do not check anything and call the method directly. In
case of failure, they process the xmlrpc fault with the code `-1` and
report an error in their script.


### Level 1: Check the signature
Prior to making an API call, the consumer needs to check, if the
method signature matches their expectation using one of the API
introspection methods described in the [XMLRPC
compatibility](#xmlrpc-compatibility) section.

This approach does not rule out backwards-incompatible changes
described in the point 3.4 in the note on [breaking and non-breaking
changes](#note-on-breaking-and-non-breaking-changes).


### Level 2: Check the version and flavor
The safest way is to use check the API version.



## Process for deprecation and removal API methods

TODO: Part of this RFC or not?
Additionally, a clear process for breaking the API in a controlled way
must be defined.


# Unresolved questions
- [ ] remove all TODO
- [ ] decide which solution to take, move other to "alternative solutions"
- [ ] decide if to write the guidelines (in the API > FAQ page or docs)
- [ ] make sure the links work
