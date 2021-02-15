- Feature Name: (SUSE Manager Proxy as a container)
- Start Date: (2018-04-23)
- RFC PR: (leave this empty)

# Unimplemented note

This RFC was not ultimately implemented due to time limitations. It is still archived here for historical purposes.


# Summary
[summary]: #summary

Provide a way to run a SUSE Manager proxy as a container.

# Motivation
[motivation]: #motivation

There is only one specific customer who requests this feature. They do not
have any specific technical reasons, it is only driven by internal organizational
reasons of the customer.

Containerizing our product(s) is a long-term goal. Containerizing the Proxy is a first step to gain knowledge in this regard.

# Detailed design
[design]: #detailed-design

## Providing an image with SUSE Manager Proxy

Based on official base container images of the underlying operating system
we provide a container that has all the SUSE Manager Proxy packages installed.
This step is already more or less done; all the needed infrastructure in the
build service is available meanwhile.

## Preparing deployment of the container

A Proxy running in a container should not require anybody logging in and doing
the setup. Also the container needs persistent data so a reboot of the host
running the container is possible without the need to re-setup the proxy.

So we need to provide a script that sets up the required infrastructure (mainly
a device tree that provides everything that is needed for the proxy to get set up
and run). This includes stuff like the certificates from the server, an answer file
for the configure-proxy.sh script, a bootstrap.sh script ready to run and some
other things.

## Deploying the proxy container

Ideally the customer would just need to pull the image from registry.suse.com and
run a script.

This script would do the following:

* create the required directory hierarchy outlined in the previous paragraph and populate it
* run a container with the proxy image provided by us and running a specific script in there
* the script needs to set proper ownership and permissions of the persistent volumes set up before. This cannot be done from the host providing the container because UIDs differ
* the script needs to check if the proxy is already configured; if yes, it would mean the container (or host) was just restarted and proxy services just need to get started
* if the proxy is not yet set up, the container needs to register to its server and run the configure-proxy.sh script using the provided answer file; after that, start proxy services

# Drawbacks
[drawbacks]: #drawbacks

Currently this is mainly a research project. While we were able to get a containerized proxy
up and running (tested both with traditional clients as well as salt minions registered through it working fine),
we ran into all sorts of problems.

## We are abusing containers

A container is intended to run just one single service. A SUSE Manager proxy however needs to run
several services like apache, squid, jabberd and so on. While the customer apparently would not mind,
a clean way would be to use kybernetes. However this would mean a massive increase in complexity. Also
so far probably nobody ever tried to run the various services on different machines/containers so chances
are very high we will run into all sorts of new problems. So far it is not even clear if this is possible
at all (which container would need to be registered to the server?). So abusing a container by running
several services still seems to be the best way to go. At least we have just proven that it is working
technically.

There is an ongoing debate on the granularity of containers. There's no "silver bullet". Separating daemons makes sense when you can start multiple containers to scale out. This is not applicable in Manager Proxy.

Also customer clearly stated two requirements

* single (big) container only
* no Kubernetes (or any other 'orchestration')

## Configuration of the proxy

Simply running the existing configure-proxy.sh script runs fine, but produces quite some ugly error
messages due to systemd not being present (the script tries to restart services and so on). They can be ignored
and starting of all the services needs to be done in a new script anyway.

The alternative would be to provide a special script (configure-proxy-container.sh) that is tailored for this
specific use case. Drawback is obvious: We would have redundant code and every change or fix needs to be
done on both of them.

Documenting these problems is sufficient for now. In case we go with systemd this will not be an issue anyway.

## System logging

As a container does not run systemd, we do not have any system logs. Luckily rsyslog still is available and
works just fine. The default configuration is already acceptable, so no additional setup is necessary. The
log files should go to some of the persistent volumes described earlier, so they can be checked without the need
to log into the container itself. Also this will ensure correct ownership of the logfiles (some services refuse
to start if they cannot write their logfiles).

## Things might be working only by accident right now

One of the biggest problems is the start of services. In a container we do not have systemd, so services need
to be started directly. Problem here is that most services do not run with the user ID of root, but are using
their own, specific user ID. This is not a problem for apache, squid and salt, as they are just doing the
necessary system calls on their own, which just works.

But for jabberd, the situation is quite different: On a regular proxy, the service is started by the tool
runuser which does the change of the user ID and then starts the actual service. Unfortunately runuser does
not work because it tries to do PAM authentication which is not available due to systemd not being available
Same is true for directly using su. Luckily this can be worked around by using sudo instead. While sudo also
tries to contact the PAM service, it will also print an error message, but unlike runuser and su it decides that
it can do its job nevertheless and will switch user ID and start the service.

There is some risk that this behaviour might be considered a security flaw in the future and could be changed.
This risk probably is not very high (in fact the behaviour of runuser and su is questionable), but it exists. In
case sudo changes behaviour we would need a different way to run services under a different user. Disabling PAM
is not an option.

## Container sharing ressources with host it is run on

A typical container is sharing several ressources with the host it is running on. This is especially
true for the network configuration. Since the proxy needs to be reachable on several ports and these
are the same ones as on a SUSE Manager server (ports 80, 443, 4505, 4506, 5222, 5269, 5347), the container must not run on the SUSE Manager server
itself. It might be possible to workaround this issue by some specific network setup inside of the
container, but again this is more about mimicing a virtual machine than using a container as it is designed.

## Managing and updating the container

A SUSE Manager Proxy needs to be a traditionally registered client of its server. Even when run as a
container, it will show up as a regular client in the SUSE Manager server. While it is possible to schedule
package/patch updates on such a container, all these changes will be lost when the container is stopped.

So the question arises how such a container should receive its updates. Apparently there are several ways
how this can be achieved (regular updates and storing new layers, providing updated images via registry or
maybe even using some of the tools used by other teams such as transactional-update). This still needs a
lot of discussion and thinking about this should only start if and when a decision has been made if this
feature really should be implemented.

Decisions:

* the feature will be implemented
* with every update of the proxy or the underlying operating system, a new image will be provided on registry.suse.com
* updates should work as follows:
** stop the container
** pull a new image
** start the container

