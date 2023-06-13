- Feature Name: Proxy for Salt Minions
- Start Date: 2016-06-15
- RFC PR:

# Summary
[summary]: #summary

Define a Proxy design for Salt Minions

# Motivation
[motivation]: #motivation

There are customer enviroments in which network design does not allow direct connection from Minions to Salt Master. Also scalability suggests a way to take load away from the Master.

On these enviroments, we need to provide a solution that allow Salt Minions reach the Salt Master, and also to ensure the functionality of SUSE Manager custom repositories.

Ideally without loosing Salt functionality.

## Problems to solve:
- Get information (states, pillar, jobs, etc) from Salt Master
- Access to SUSE Manager custom repositories
- Take load away from the Salt Master
- Preserve Salt realtime capabilities

# Detailed design
[design]: #detailed-design

## A ZeroMQ proxy to Salt Master (broker)

One of the cleanest way seems to be a [ZeroMQ proxy](http://zguide.zeromq.org/page:all#Intermediaries-and-Proxies).
This proxy works as a connection broker for the ZeroMQ connections (PUB channel in 4505 port, REQ channel in 4506 port) coming from the Minions behind the Proxy:

```
     -------------
    | Salt Master |----------
     -------------          |          ----------
          |                 ----------| Minion 1 |
          |                            ----------
          |
          |          --------------
          ----------| ZeroMQ Proxy |
                     --------------
                      |     |    |
                -------     |     ---------
                |           |             |
                |           |             |
           ----------       |         ----------
          | Minion 2 |      |        | Minion 4 |
           ----------       |         ----------
                            |
                        ----------
                       | Minion 3 |
                        ----------
```

- The Minion outside the Proxy (Minion 1) is directly connected to Salt Master (PUB/REQ connections). No issues here.

- ZeroMQ Proxy supports only one pair of connections (PUB/REQ channels) with the Salt Master. It opens 4505 and 4506 ports in order to accepts the connections from the Minions behind the Proxy and works as a connection broker.

- The Minions behind the proxy (Minion 2,3,4) have the ZeroMQ Proxy as Salt Master. When `salt-minion` process is started, ZMQ connections are created against the ZeroMQ Proxy.

### Issues:
- Minion 1: `salt-minion` connects directly to the Salt Master.
- Minion 2,3,4: `salt-minion` connects to ZeroMQ Proxy and is receiving/posting messages from/to Salt Master without problems.
- ZeroMQ Proxy: Is acting as connection broker between Minions 2,3,4 and Salt Master. It support the ZMQ connections from Minions behind proxy and only one SUB/DEALER sockets with Salt Master ZMQ.
- Salt Master: Only support 2 clients connections to ZMQ instead of the total 4 clients.
- Connections are balanced between Salt Master and ZeroMQ Proxy.
- Preserves Salt functionality: states, pillar, jobs, etc.
- ZeroMQ Proxy would not interfere with the traditional proxy implementation. This would mean we could easily run all on the same machine. No seperate "traditional" vs. "salt" proxies needed.
- Easy to implement. We can start with very simple broker (that simply forwards messages) and evolve it later in a caching proxy more similar to the XMLRPC one we have for traditional client only where it makes sense from a performance perspective.
- Allows Minions behind multiple Proxies (chain of Proxies)
- Third-party sample with pyzmq: [salt-broker](https://github.com/pengyao/salt-broker)


## RPM Packages cache:
SUSE Manager creates custom repositories for the Minions but these repositories are pointed to SUSE Manager Server. We need a solution for the Minions behind the Proxy.

The ways which tell us if a Minion is behind a Proxy or not could be multiple:

- config attribute (e.g. `master`) in the minion.
- custom grain stored in the minion. we need to provide a custom grain.
- pillar information stored in the server based on custom grain.
- user provides this information during the onboarding.
- inspect ZMQ messages in order to include metadata in a special `proxy-detection` message.

Asking the Minion for some config attribute, e.g. `master` is a simple way to know if Minion is connected to Salt Master or a Proxy.

If the Minion returns a `master` which is not the SUSE Manager Server, then we know that this Minion is behind a proxy and also what is the hostname for the Proxy. We can now provide a suitable repository address for the Minion behind the Proxy, and also check if the Proxy behind another Proxy and so on.

In fact, `master` is always pointing where ZMQ is connected, so it always tells us fresh information:

```
suma3pg:~ # salt '*' config.get master
minionsles12sp1-suma3pg.vagrant.local
    suma3pg.vagrant.local
clisles12-suma3pg.vagrant.local:
    testproxy.vagrant.local
clisles12sp1-suma3pg.vagrant.local:
    testproxy.vagrant.local
minionsles12-suma3pg.vagrant.local
    suma3pg.vagrant.local
```

We could also use a custom grain based on the `master` config value, then after onboarding, the Minion could download the custom grain and load it. Users doesn't need to provide information during onboarding in any cases.

If we use a fixed pillar/grain value without refreshing it, maybe it's not reflecting the trust about where the Minion is really connected if changes are applied in the Minions.

Inspecting ZMQ messages is not so simple as they are usually encrypted by the Minion while passing through the Proxy. So in this case, we would need to somehow store keys in order to decode and add some metadata into a special `proxy-detection` message. A special `proxy-detection` message without encryption would be easy to catch for the Proxies, but `salt-master` would need to react to this special message.


In addition, Proxy must handle the repositories auth token.
[mc branch from CSM Workshop 2016](https://github.com/SUSE/spacewalk/commits/Manager-3.0-proxy-handle-authtoken)

### Issues:
- All Minions have access to SUSE Manager custom repositories.
- Proxy acts as Web Proxy and also handle the auth token.
- Proxy creates a RPM cache.


## Onboarding a Minion behind a Proxy with ZeroMQ Proxy:
When `salt-minion` is started in the Minion:
- Minion connect to ZeroMQ Proxy
- ZeroMQ acts like a connection broker
- Salt Master received the messages from the Minion behind a Proxy

At this point, SUSE Manager will show the Minion in the "onboarding" page waiting for key acception. We still don't have control of the Minion and cannot use Salt functionality. SUSE Manager doesn't know if the Minion is behind a Proxy.

We continue with the onboarding:
- After accepting the key of the Minion on the onboarding page, the Salt Master can ask the Minion for e.g. `master` config or get the custom grains containing real information from the Minion telling us if it's behind a proxy or not.
- The information about Proxy should be stored in the SUSE Manager DB maybe using the existing db tables used with traditional clients.
- Highstate is applied and then custom RPM repositories are fixed using grain/config information and referred to the RPM Proxy Repository.
- Minion system is now registered in SUSE Manager and fully operational.


## Migrate a Minion from proxied to non-proxied and vice versa using ZeroMQ Proxy:
If we use ZeroMQ Proxy approach and want to migrate a Minion behind a Proxy to a non-proxy enviroment or vice versa, we need to:
- Change the salt `master` setting value to Salt Master hostname and restart `salt-minion`.
- SUSE Manager DB should be updated in order to change or remove the proxy information for the Minion.
- Apply state in order to change the custom repositories for the Minion.


# Drawbacks
[drawbacks]: #drawbacks

### The ZeroMQ limitation:
The ZeroMQ approach has the limitation of working only with [Salt ZeroMQ transport](https://docs.saltstack.com/en/latest/topics/transports/zeromq.html).
This should not be a problem, but Saltstack plan to make [TCP transport](https://docs.saltstack.com/en/latest/topics/transports/tcp.html) as default in future releases.
It might be easy to resolve if we create also a connection proxy for the new transport.

### Salt Master workload:
While the Salt commands sent back and forth are probably lightweight, state distribution and pillar refresh may load the server quite a bit, as Salt Master is doing all this work for the Minions regardless if they are behind a Proxy or not.
It should be taken as consideration in terms of scalability.


# Alternatives
[alternatives]: #alternatives

### salt-syndic [info](https://docs.saltstack.com/en/latest/topics/topology/syndic.html)
1. channels for minions are generated using the hostname of the Server/Master in the URL.
The grains contains the master of the minion which point to the Proxy/Syndic. We should store this during the onboarding and the code which generate the channel files need to adapt the URLs.
2. minion keys have to be accepted on the syndic.
Enable salt-api on the syndic and call it from the high level master to manage the keys (list, accept, delete, etc). A special flag will be needed for the syndic to be able to call all the registered syndics. Maybe reuse existing proxy code ?
3. custom states and modules must be present on the syndic machine before onboarding it with the high level master.
Find a way to sync the files from the high level master to the syndic:
    - GitFS
    - shared storage, e.g. NFS
4. Unknown future: There seem to be discussions upstream about dropping syndic.
5. More complex solution.

NOTE: [salt-users ML: salt syndic vs broker](https://groups.google.com/forum/#!topic/salt-users/RO0Fz2q_1KU)

### Forwarding ZMQ using iptables
1. ZeroMQ Proxy is prefered because otherwise Salt Master must support the ZMQ connections for all the minions and it doesn't help to scalability.

Others alternatives was explored in last [CSM Workshop 2016](https://github.com/SUSE/spacewalk/wiki/Features%3A-Proxy-for-Minions).

# Unresolved questions
[unresolved]: #unresolved-questions

What parts of the design are still TBD?
