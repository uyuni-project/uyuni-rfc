- Feature Name: Detatch salt-master and salt-api from uyuni-server container
- Start Date: 2025-05-29

# Summary
[summary]: #summary

Move `salt-master` and `salt-api` services out of `uyuni-server` container to the separated ones.

# Motivation
[motivation]: #motivation

Currently we have huge `uyuni-server` container with almost all services running inside it, what is not a best practice with the containers.
It makes sense to split out `salt-master` and `salt-api` the same way as `saline` was originally separated.
That way we could achieve the following goals:

- Step further with splitting the services out from the single container.
- Make containerised deployment more native.
- Prepare for future possible scaling capabilities.
- Make `salt` services less dependant on the other components of the server.

# Detailed design
[design]: #detailed-design

Create separate `uyuni-salt-master` and `uyuni-salt-api` container images with `salt-master` and `salt-api` services.

Make `salt-master` service abailable for the minions with ports `4505` and `4506` by publishing these ports from `uyuni-salt-master` container.
The following storage volumes need to be mapped to the `uyuni-salt-master` container:

| Volume | Comment |
|--------|---------|
| etc-salt:/etc/salt | storing configuration of `salt-master`, `salt-api` and `saline` |
| run-salt-master:/run/salt/master | communication between `salt-master`, `salt-api` and `saline` |
| srv-salt:/srv/salt | storing custom salt states used by `salt-master` and `salt-api` (for salt ssh) |
| srv-pillar:/srv/pillar | storing custom pillar data used by `salt-master` and `salt-api` (for salt ssh) |
| var-salt:/var/lib/salt | storing ssh keys used by `salt-api` for salt ssh clients |

`salt-api` can communicate to `salt-master` the same way as `saline` does with shared volume `run-salt-master:/run/salt/master`.
Make `salt-api` service available with `uyuni` network using `uyuni-salt-api.mgr.internal` internal FQDN and `salt-api` network alias
to make it available for `tomcat` and `taskomatic`.

# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?

  * possible unknown use cases, which doesn't work with such setup
  * more complex setup of containers

# Alternatives
[alternatives]: #alternatives

- Keep everything as it is now with the one single big container.
- Split out `salt-master` and `salt-api` to one separate container running both services.

# Unresolved questions
[unresolved]: #unresolved-questions

- There could be some non-obvious external dependencies of `salt` services, like files or modules used in indirect way.
- Something more?
