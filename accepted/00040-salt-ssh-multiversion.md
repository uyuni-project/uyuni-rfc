- Feature Name: Support multiple major versions of Python for Salt SSH
- Start Date: 2018-03-07
- RFC PR:

# Summary
[summary]: #summary

Support multiple major Python versionsfor Salt SSH.

# Motivation
[motivation]: #motivation

SaltSSH does not support multiple major Python versions. If client is
runing another major version, then such SaltSSH call will fail.

There are several cases where the environment is using different
Python major version, as such:

- SUSE Manager, built on top of SLE12 still running Python 2.
- Any remote client that is still running Python 2
- Older distributions still running upstream-EOL Python 2.6
- Future possible clash between Python 3.4 and less and Python 3.5+

So the requirements would be not just to cover major versions, but
also have a mechanism to carry alternative implementations of the same
libraries that would be able to run older versions that are
incompatible with the "default version".

# Detailed design
[design]: #detailed-design

SaltSSH works the way it packages a subset of the Salt with included
modules and dependencies, called "thin package". The same tarball is also
includes all needed dependencies that can run on vanilla Python. Upon the SSH
connection call, the tarball with the Salt subset is copied to the
client machine and executed. It still persists there in `/tmp`
directory for caching purposes, unless updated or naturally purged by
the OS.

Problem is, however, that the tarball currently carries only the
libraries for the specific Python version on the target machine. And
so if there is another major version found (say, Python3), the
Python2-prepared tarball will not work and an exception will be
raised.

The solution is quite obvious: the carried "thin package" should just
carry libraries for all possibly supported major versions and
construct the modules tree upon the call.

In order to keep "thin package" thin, the crafting algorithm should do
the following:

- Find all modules that are compatible in all supported major
  versions, and so put them together into a common area.

- All major version-specific modules should be in a separate
  directories in the "thin package". This includes binaries too.

The rest of the SaltSSH command line interface should remain intact.

## "Problem 26"

Python 2.6 is very dead. Almost. The code syntax and libraries has some
differences with its successor of 2.7 and it is subject to fail. And
since Salt community _no longer_ supports 2.6 version, this is a
problem. Essentially, Python 2.7 running Salt SSH when "talking" to
Python 2.7-based machine has high chances to fail. However there are
many machines running Python 2.6 out there, and getting rid of them
isn't going to happen anytime soon.

Conditions:

- Upstream "killed" 2.6 support and this is not a subject to change
- SUSE does not want to support 2.6 code regressions on its own either

As the design of the multiversion support should be able to pack
different versions, yet we cannot have fully functional Python 2.6 and
2.7 on the same machine. However, we can have installed Salt _library_
of the Salt version YYYY.MM.VV that is compatible with certain major
and minor Python version.

One of the option is to install Salt in
`/usr/lib/python2.6/site-packages/salt` just as a library and thus
take required bits from there. This path might be also installed
elsewhere. Then SaltSSH should have more complex configuration, or
more specifically, SaltSSH's "The Thin Builder" must be permanently
configured which version of Python to use.

For example, there could be a following configuration in
`/etc/salt/master` (or drop-in for `/etc/salt/master.d`):

```
ssh_ext_alternatives:
  <namespace>
    py-version: [major, minor]
    path: [main path to the salt]
    dependencies:
	  <key>: <value>
```

The "namespace" here would be an arbitrary string/label of whatever
Salt version is used. Typically it is targeted last version that
officially still supported Python 2.6, which is 2016.11.4 version.

The "py-version" directive is the designator which Python major/minor
version is going to be selected by this namespace.

The "path" is just a path to the main Salt installation or just a
code, where it will be loaded further.

The "dependencies" key/value hash is a "name/path" pairs of the Python
dependencies.

An example configuration would be as following:

```
ssh_ext_alternatives:
  2016.11.4:
    py-version: [2, 6]
    path: /opt/salt/2016114
    dependencies:
	  jinja2: /opt/salt/jinja2
	  yaml: /opt/salt/yaml
      tornado: /opt/salt/tornado
	  ...
```

The example above is not completed, but it serves the purpose.

The configuration above would _additionally_ include places where the
sources are picked from. And so there shuld be made just a package of
a carry-over code with the pre-defined configuration like so. Simply
installing this package should enable transparent support for 2.6
version of Python on the client machines.

## TAR layout

As earlier mentioned, right now the TARball contains only modules for
the corresponding major Python version. With the examples and
conditions above, the thin TARball supposed to have three namespaces for
this:

- Common area (modules that work for 2.7+ and 3.x+ versions of
  Python), called 'pyall'.
- Python 2.7 area, called 'py2'.
- Python 3.x area, called 'py3'.

...or even more spaces, if there are couple of more specific
namespaces configured. The difference that configured namespace in the
configuration for `ssh_ext_alternatives` is taking all module
again. That said, even e.g. YAML dependency would perfectly work under
the `py2` namespace, it will still be copied to the namespace, defined
by that configuration option.

Apart from the namespaces, this would allow to have a concept of
"carryover" modules that would be available to a standard Python
version and thus there would be no need to replicate the module for
each version separately, as long as the module is bi-directionally
compatible.

Not all modules can be done that way, especially if they are C/C++
bindings to a specific API. But even if they aren't, in some cases a
straight Python module might be not Python major version
compatible. An example of this is a YAML module.


# Alternatives
[alternatives]: #alternatives

Upstream, based on their planned fix to this problem in version
Fluorine, wants just put both libraries together into "think package"
(which unlikely will be thin after that) and so figure out on the
client machine which python is there, and then execute accordingly.

Upstream approach is essentially the same as described in this RFC,
except they aren't considering footprint optimisation.

# Unresolved questions
[unresolved]: #unresolved-questions

N/A
