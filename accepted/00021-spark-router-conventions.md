- Feature Name: spark-router-conventions
- Start Date: 2016-06-03
- RFC PR:

# Spark router conventions
[summary]: #summary

Introduce code conventions to be applied in the spark router class
(`com.suse.manager.webui.Router`) in the java codebase.

# Motivation
[motivation]: #motivation

The state of current `Router` class is not consistent and deserves clean up and
unification.

Expected outcome of this RFC is to bring this document to a state so that it
can provide guidelines for the developer who will unify the code.

# Detailed design
[design]: #detailed-design

The following paragraphs describe the problems which needs to be tackled.

## Decide whether to use underscores vs. hyphens in the route names:
Currently we are not consistent, for instance in these routes:
```
/manager/subscription-matching/data
```
vs.
```
/manager/state_catalog/state

```

We should use only one way to make things clean. 

Note: Unifying this breaks existing bookmarks in the clients' browsers. This change should be somehow documented/communicated to customers.

### Proposal:
**Use hyphens.**

In the end, this is just a matter of taste. Not that significant, but [this
non-technical guidelines](https://support.google.com/webmasters/answer/76329?hl=en) from
Google favours the hyphen syntax over the underscore one.

(Just for completeness: Another alternative would be to use camel case (as in
the legacy code - e.g. `/rhn/errata/RelevantErrata.do`)).

## Separate the API routes from the 'web' ones
Currently we have 2 kinds of routes:
 1. Routes for serving webpages (e.g. `GET /manager/minions/cmd`)
 2. Routes for the data (API) (e.g. `POST /manager/api/minions/cmd`)

In some cases (like the 'minions command' routes mentioned above) we
differentiate the routes by type by having the `/api` part in the URL. In some
cases (`subscription-counting`), we don't make this difference.

We should use only one way to make things clean.

### Proposal:
**Differentiate the API routes from the website ones (by putting the API ones in
the `/api` path).**

We can also make use of this separation to define different behavior for the
different route type (next point).

## Agree on the behavior of the API routes when session expires
Currently, when the login session expires and user sends a new request to the
server, they are redirected to the login page. This doesn't play so well with
the "API routes" (e.g. when an AJAX request is sent to retrieve some JSON
content, the `AuthFilter` will kick in and instructs the client to do the
redirect to the login page. After the client follows the redirect, it gets the
HTML data of the login page instead of the meaningful HTTP error code).

At this moment, this problem is partially solved by surpressing the redirect
and setting HTTP code `403` for the `application/json` content type.

We should consider changing the behavior, here are possible reasons:

* Foremost: Is there any good reason for content type defining such behavior?
* If we want to serve a new content type (XML, YAML), we'd need to
  adjust the `AuthFilter`.
* Extreme corner case: What about serving HTML over API? Then the current logic
  in the `AuthFilter` would incorrectly redirect the request even though the
  consumer was expecting `403` on the session expire.

### Proposal:
Surpress redirect and send status code `403` on unauthorized when the request
is performed to API routes (contains `/api/` in the path).

This will also allow to implement our react components in an uniform way so
that they'll react to the 403 code and will redirect to the login page on the
client side (e.g. setting `window.location.href`).

Note that this proposal depends on the previous one.


