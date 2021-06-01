- Feature Name: Improve the 3rd party usage of XMLRPC API
- Start Date: 2021-05-20
- RFC PR:

# Summary and motivation

The main goal of this RFC is to highlight the problems of writing client
applications or scripts compatible with multiple versions of Uynui and SUSE
Manager (SUMA) API and suggest an improvement in this area. When the consumers
use the API, there must be a way for them to make sure they call the endpoints
correctly (they need to call an existing method with correct parameters and they
also need to make some assumptions on the return value structure).


## Note on XMLRPC structure exposition

Before describing the main problem, it is important to understand how the
information about API is exposed to clients.  Uyuni/SUMA exposes the information
about the API and its structure in 3 places:

1. Information about the versions via the `api` XMLRPC endpoint:
   - `getVersion`: the API version, e.g. `25`. This integer grows with time, but
   there are no strict rules about it.
   - `systemVersion`: the server version (e.g. `4.2.0 Beta1` for SUMA, `2021.05`
   for Uyuni)

2. Furthermore, the `api` namespace also exposes basic API introspection calls
   describing the structure of the call:
   - `getApiNamespaces`: all API namespaces
   - `getApiNamespaceCallList`: API methods of given namespace together with
     their parameter types, faults and return types
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


## The problem

The main problem is the difficulty of writing the API consuming applications
that:

- can be agnostic to the server product flavor (they can target both Uyuni and
  SUMA)
- can target multiple versions of the product (e.g. SUMA 4.0, 4.1 and 4.2)
- can use the features introduced in maintenance updates of SUMA (a feature was
  not present in 4.1, but was introduced in a 4.1 maintenance update)
- handle exceptional cases gracefully (e.g. display a meaningful warning to the
  user, in case the feature does not exist in the API).

### Existing approach

Some applications already try to address the problem:

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

This method has 2 problems:
1. targetting both Uyuni and SUSE is hard (the API version numbers are not
consistent (API version `25` in Uyuni does not need to be the identical to the
version `25` in SUMA)).
2. currently, there is no defined rule to increase the API version. Sometimes
the API is modified, but the version stays unchanged, which makes it impossible
to track a feature presence.


## Solution

The proposed solution is
- to enhance the documentation with the guidelines of writing the API consuming
  scripts that target multiple product versions
- to improve the API introspection calls
- to exactly define the semantics of the API version number and the rules for
  its increasing

These steps are described in the further sections in greater detail.

### Enhancing the documentation

Following sections of the documentation must be enhanced.

#### API > FAQ

We should introduce 3 ways of consuming the API:
1. (relaxed) check errors post-mortem
2. (stricter) check the method existence via introspection
3. (strictest) check the method existence via introspection and check exact
   product flavor/version

This should give the users the possibility of choosing the balance between the
total correctness and ease of writing the script.

##### 1. Check errors post-mortem
Do not perform any checks before calling the API. Only handle the error code,
when calling a method fails and notify the user about the error. The error code
signaling the absence of given method/signature must be enhanced (see below).

Checking errors after call is a good practice for the client applications and
should be used in the following methods too.

##### 2. Check the method existence via introspection
Before making a call, check if the desired API method-signature combination
exists. This check can be done using the [existing
methods](#note-on-xmlrpc-structure-exposition) or with the new [single method
introspection](#introduce-a-single-method-introspection-method).

The advantage of this method is that it can warn the user before making the
actual call (one possible use case would be UI apps built on top of the API).

##### 3. Check the method existence via introspection and check exact product flavor/version
This is the safest and the most complicated way. In addition to the checks made
in the previous section, also check the the flavor and the API version. All
these checks make sure that the API call is present and has the desired
semantics defined in the product flavor and version.

#### API > Script Examples
Examples showing usage of the 3 ways of consuming the API described above should
be added to this section.


### Improving the API introspection

These areas of the introspection must be addressed:

#### Error code for non-existing method/signature
Currently, when calling a non-existing method/signature combination, the API
reports a fault with code `-1`. As of time of writing this document, this error
code is used to signal other faults too (see the the `CustomInfoHandler.java`
file).

This needs to be solved by:
- visiting the current occurences of `-1` fault code in the existing handlers
  containing "business methods" (e.g. `CustomInfoHandler.java`) and make them
  use meaningful codes (see the `exception_ranges.txt` document in the codebase)
- reserving a new code for the absence of method/signature combination and
  making the existing XMLRPC code use it

#### Introduce a single method introspection method
In addition to
[existing introspection methods](#note-on-xmlrpc-structure-exposition),
implement a call in the `api` namespace for checking, whether a method with
signature exists in a namespace:
`apiCallExists(namespace, method, parameters_varargs)`.

The same can already be achieved (although in a bit more complicated way) with
already-existing introspection methods, but this method is more convenient.

#### Introduce the API flavor endpoint
Introduce a new method under the `api` namespace returning the product flavor
(Uyuni/SUMA).


### Bumping the API version
The version of the API is bumped when a breaking change is introduced that
cannot tracked by introspection, which involves the following:
- changing a behavior of an existing method
- removing or adding a field in a structure accepted by a method / returned by a
  method
- changing the fault thrown by a method (changing a fault code, throwing new
  faults or removing a fault)

All other changes shall be tracked by the introspection methods.

A CI automation job shall be written to ease tracking of such changes.


## Unresolved questions

Q: Shall we document the process for deprecation and removal API methods?
Additionally, a clear process for breaking the API in a controlled way
must be defined. A deprecation warning should be added to the xmlrpc
doc. Additionally, we could add an annotation to the java method in the handler
and print a warning in the server logs, in case a `@Deprecated` method is
called (TODO very questionable).


## Appendix: CI automation job

In order to minimize the risk of missing the increase of the API
version, a CI job must be implemented, that reminds the PR author,
when there is a change in the API code:

- Introduce a new section in the Uyuni/SUMA Pull Request template with
  a checkbox with this text "XMLRPC changes do not require API
  version bump or release engineer has been informed", unchecked by
  default
- If there are code changes in the `xmlrpc` java package and the
  checkbox is unchecked, the CI bot raises an alert. The author of the
  PR needs to:
  - either make sure their changes are not breaking the API
  - or inform interested people responsible for bumping the API version
  and check the checkbox.
