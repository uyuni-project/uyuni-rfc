- Feature Name: (minion as a proxy)
- Start Date: (2018-07-31)
- RFC PR: (TBD)

# Summary
[summary]: #summary

Allow a salt minion to act as a proxy

# Motivation
[motivation]: #motivation

Long term goal is to get rid of traditional clients and use salt only. Currently a proxy needs to be a traditional client. In order not to lose functionality we need salt minions to be able to act as proxies.

# Detailed design
[design]: #detailed-design

Main work for this feature turned out to be research. The proxy code is very complex, as it needs to transform https connections from the clients to regular internal http connections (so squid is able to cache) and then back to https connections to the actual server. There are quite some checks in the code that require a client to be traditionally registered to be allowed to become a proxy. Also the proxy needs to have a certificate in order to be able to authenticate to the server (the systemid file) which does not exist for salt minions.

We hacked the conditions that allow a system to become a proxy and created a faked certificate; hardest part here is to get the checksum/secret right. We also found out that traditional systems are using some special system ID (the so-called "physical-server-id") that needs to have some well defined format; salt minions just use the machine_id which cannot be used here. It seems this physical-server-id of salt minions is not used for anything; it just has been provided because it must not be empty. Using the same format as for traditional clients turned out to work just fine. No functionality was lost on the minion that is supposed to become proxy.

After getting all these conditions right, we ended up with some fully functional proxy. As added bonus it would not only work as salt proxy, but continued to work for traditional clients as well.

So the following implementation steps are needed:

- do not require management entitlement for a client to become proxy; allow salt minions as well. One-liner. Already done.
- steal the system-id generation code from traditional registration code and expose it, so it can be used by minions as well. This is the main work that is currently in progress.
- fix proxy tab in the web UI. Chances are high this might be a one-liner as well, but has not yet been researched because this is secondary.
- do not use machine_id as physical-server-id for minions. One-liner as well.

Advanced steps for the future: Using the approach outlined above, it might even become easy to transform existing proxies to minions!

# Drawbacks
[drawbacks]: #drawbacks

We are going to re-use existing code from traditional clients. Not the cleanup that was wished for. But this is mainly an academic issue because rewriting all of this code will be a lot of work. And while the proxy-broker code is extremely complex, it works very well and stable. Apparently it took at lot of iterations for the initial author to come up with it.

Cuurently we are not aware of any impact on other parts of the product.

# Alternatives
[alternatives]: #alternatives

Alternatives would imply more or less rewriting the proxy code. LOTS of work. Current approach is extremely sexy: Not very intrusive, ability to re-use existing, tested and proven stable code. And we even get proxy support for existing traditional clients for free which makes it easier for customers to migrate.

# Unresolved questions
[unresolved]: #unresolved-questions

- investigate proxy tab in UI
- think about helper scripts to transform traditional proxies to minion proxies
