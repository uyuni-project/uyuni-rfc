- Feature Name: Monitoring with Prometheus and Grafana
- Start Date: 2018-11-21
- RFC PR: https://github.com/SUSE/susemanager-rfc/pull/82

# Summary
[summary]: #summary

This document describes the integration of monitoring in SUSE Manager based on
[Prometheus](https://prometheus.io) and [Grafana](https://grafana.com) as it was
interlocked for SUSE Manager 4.0. The general vision of the feature: **SUSE
Manager can provision and automate the configuration of monitoring
infrastructure**.

On its first version, the integration of monitoring in SUSE Manager will enable
the following use cases:

* Enable / disable exporting of metrics on SUSE Manager Server itself.
* Enable / disable exporting of metrics on clients that SUSE Manager manages.
* Enable / disable exporting of metrics on SUSE Manager Proxy (a special type of
managed client).
* Add / remove scrape targets in Prometheus configuration automatically.

# Motivation
[motivation]: #motivation

We are selling monitoring together with SUSE Manager since the very first
release of SUSE Manager 1.2 in 2011. The additional monitoring subscription was
always based on the monitoring features of Spacewalk that were removed from the
Spacewalk and SUSE Manager codebases in 2015 for the release of SUSE Manager
3.0. The scope of this document is to describe the first steps of an integration
with the open-source monitoring toolkit
[Prometheus](https://prometheus.io/docs/introduction/overview/) plus an outlook
of what can be implemented and shipped after SUSE Manager 4.0 FCS.

## Why Prometheus?

* The Prometheus Query Language (PromQL) allows to slice and dice dimensional
  data for ad-hoc exploration, graphing, and alerting. Nagios-based competing
  solutions do not have a native query language.
* There are several exporters available for Prometheus that already cover many
  use cases. Moreover, it is fairly simple to write new metrics exporters for
  custom scenarios.
* Prometheus has great support for service discovery.
* Alerting is powerful: It is possible to send alerts to Email, Webhooks,
  popular incident management tools, and the altering rules are scriptable.
* A single Prometheus server can handle millions of time series.
* It is already shipped with SUSE Linux Enterprise and openSUSE.

# Detailed Design
[design]: #detailed-design

## Packaging and Shipping Required Packages

This is a prerequisite for all the planned efforts: we need to package and ship
the server and client side monitoring software that this feature is based on in
terms of provisioning and automation of configuration. We are going to use the
Prometheus and Grafana packages as they are provided by the SES team and partly
available in the SLE15 channels.

Server side packages:

- [`golang-github-prometheus-prometheus`](https://build.suse.de/package/show/SUSE:SLE-15:GA/golang-github-prometheus-prometheus)
- [`golang-github-prometheus-alertmanager`](https://build.suse.de/package/show/SUSE:SLE-15:GA/golang-github-prometheus-alertmanager) (for future support of alerting)
- [`grafana`](https://build.suse.de/package/show/SUSE:SLE-15-SP1:Update:Products:SES6/grafana)
- [Blackbox exporter](https://github.com/prometheus/blackbox_exporter) (no package available yet)

Client side packages:

- [`golang-github-prometheus-node_exporter`](https://build.suse.de/package/show/SUSE:SLE-15:GA/golang-github-prometheus-node_exporter)
- [`prometheus-client-java`](https://build.suse.de/package/show/Devel:Galaxy:Manager:Head:Other/prometheus-client-java)

Relevant client side data exporters that are still pending to be packaged (maybe
incomplete):

- [PostgreSQL exporter](https://github.com/wrouesnel/postgres_exporter)
([packaged in OBS](https://build.opensuse.org/package/show/systemsmanagement:sumaform:tools/golang-github-wrouesnel-postgres_exporter))
- [Apache exporter](https://github.com/Lusitaniae/apache_exporter)
- [Squid exporter](https://github.com/boynux/squid-exporter)
- [Libvirt exporter](https://github.com/kumina/libvirt_exporter)
- [JMX exporter](https://github.com/prometheus/jmx_exporter)

The main server side packages should eventually be shipped with the SUSE Manager
client tools channels as we encourage customers to run the Prometheus server on
a managed client. Client packages specific to certain software or other SUSE
products should be included with each product and would be shipped from the
respective product channels, for example: A SUSE Manager specific exporter
should be released via the SUSE Manager client tools, SAP HANA exporter should
be shipped with the SLES for SAP channels, Apache exporter should be in the same
SLE module as the `apache` package itself.

Maintenance of already released and commonly used packages should be shared
between `prometheus-maintainers` (SES, CaaSP and CAP teams). Version upgrades
should generally be preferred over backporting patches.

## Exporting Metrics about SUSE Manager Server

Exporting metrics about the SUSE Manager Server itself should always be optional
as it requires several open ports for scraping the data. Customers who already
have a Prometheus server should be enabled to easily set up monitoring of their
SUSE Manager Server from the configuration UI (`Admin` -> `Manager
Configuration`) as well as via the API or configuration file. Data exporter
packages should be installed together with the other SUSE Manager packages while
being disabled by default. The activation of monitoring would not require the
installation of new packages, but only the start and enablement of the default
[Node Exporter](https://github.com/prometheus/node_exporter) and additional SUSE
Manager specific node exporters (JMX exporter, PostgreSQL exporter). Disabling
the monitoring option should disable the respective services and hence close the
listening ports.

As part of the SUSE Manager Server monitoring - since there are metrics provided
by different exporters exposed on different ports - we plan to include a reverse
proxy that will receive all metric scrape requests on a single port and
multiplex them to the relevant exporters running on the server. In this way,
only a single firewall port needs to be opened.

## Monitoring Managed Hosts

Apart from monitoring the SUSE Manager Server we would like to allow users to
easily enable monitoring for systems that are managed with SUSE Manager. This
feature will be available only for systems that are managed with Salt as the
implementation will be based on Salt states. There is generally two components
of this:

1. Installing and running data exporters on the machine, especially the Node
Exporter.
2. Configuring the Prometheus server to scrape the data from that machine.

The SUSE Manager UI and API should offer an option to enable or disable
monitoring for Salt managed systems. In the UI this option should be added in
the system properties page (`Details` -> `Properties`) as another "Add-On System
Type" and as such it should also be listed in `Activation Key Details`.

### Provisioning the Node Exporter

A system that is enabled for monitoring needs provisioning of at least the basic
Node Exporter. This should be achieved with a Salt formula that can be shipped
as a separate package offering UI support for all the monitoring configuration
of a system in one place, including which of the available data exporters should
be enabled and the configuration of those if available or needed.

This monitoring formula can be assigned to a system with a default configuration
(with only the basic Node Exporter enabled) and highstate application can be
scheduled when monitoring is enabled. When disabling monitoring for a managed
system the respective pillar data should be removed and we would need to take
care that respective data exporter services are disabled accordingly. This could
be done by synchronous application of a static state (or dynamic based on the
pillar data) or by scheduling the application of this state, similar to the
remote cleanup that we do when deleting system entries. A generic way of
providing a *cleanup state* for formulas would be desirable that can be applied
once on disablement or removal of a formula.

With the availability of this formula monitoring can be enabled for a system
group using the already existing feature of assigning Salt formulas to system
groups. This makes it easy to group together systems to provide them with the
same monitoring configuration, for example to provision all web servers with the
Apache exporter.

### Updating the Prometheus Configuration

Keeping the Prometheus configuration up-to-date with the server side pillar data
can be achieved by using the
[file-based interface](https://prometheus.io/docs/guides/file-sd/)
that is offered for allowing the implementation of custom discovery mechanisms.
See also this
[blog post](https://prometheus.io/blog/2015/06/01/advanced-service-discovery/)
for examples. Whenever pillar data is changed (when for example monitoring is
enabled for a managed system) or monitoring is enabled / disabled for the SUSE
Manager server itself, the server can write out a JSON or YAML file that should
be watched by Prometheus. We would recommend users to manage the Prometheus
server in SUSE Manager and sync the configuration as a managed file. This will
need to be documented as a best practice.

### Monitoring SUSE Manager Proxy

Enabling monitoring of the SUSE Manager Proxy works in the same way as for any
other managed host as described before (every SUSE Manager Proxy needs to be
registered as a managed system). The previously listed
[Apache exporter](https://github.com/Lusitaniae/apache_exporter) and
[Squid exporter](https://github.com/boynux/squid-exporter) could be especially
useful and should be enabled per default in case of SUSE Manager Proxy.

## Counting Monitoring Subscriptions

The new monitoring features should not be a free offering. We would like to
charge customers for each system that is enabled for monitoring. This could be
either the SUSE Manager Server, a Proxy, or any of the managed systems. Counting
the needed subscriptions should be straight forward when the implementation is
based on the so called "Add-On System Types", as with the "Virtualization Host
Entitled Servers" for example. Every system that has monitoring enabled should
therefore be granted the respective add-on system type of "Monitoring Entitled
Servers". The subscription matcher might then need to be adapted in order to
count the subscriptions correctly, but in case we will be shipping the first
iteration as a technology preview this can be done for a later iteration.

## Documentation

The monitoring MVP will include, together with the new features in SUSE Manager,
two documents that will help getting started:

1. A White Paper about monitoring best practices, that will cover:
  - Metrics vs Event Logging.
  - What resources to monitor and how often monitor them.
  - How to configure meaningful alerts.
  - The golden signals for monitoring distributed systems.
  - Metrics visualization.

2. A Getting Started Guide for Prometheus and Grafana, that will include:
  - Setup and configuration of Prometheus and Grafana.
  - Exporters.
  - Automation.
  - Example dashboards.

## Outlook
[outlook]: #outlook

The following is a list of possible next steps to be taken after the above is
achieved, but needing further clarification through separate RFCs:

- Enable SUSE Manager to automatically provision and configure the Prometheus
server.
- Enable SUSE Manager to deploy and configure the Grafana visualization tool and
possibly provide some pre-built dashboards.
- Enable support for alerting based on monitoring metrics using the
[Alertmanager](https://prometheus.io/docs/alerting/alertmanager/). Allow users
to define alerts from the SUSE Manager UI and possibly ship some pre-built alert
templates.
- Enable optional encryption and authentication on the metrics endpoints exposed
by the client systems.

# Drawbacks
[drawbacks]: #drawbacks

Customers might not really like to open additional ports on their SUSE Manager
Server, Proxy or managed systems due to security reasons. Those machines can be
running in a DMZ and therefore opening the respective ports might not be an
option at all.

# Alternatives
[alternatives]: #alternatives

- As an alternative to the pull based default approach of Prometheus servers and
node exporters we could consider to offer
[Prometheus Pushgateway](https://github.com/prometheus/pushgateway)
for customers who have concerns about opening a port for each data exporter. The
*Pushgateway* though can become a bottleneck and single point of failure if it
is used exclusively, read more
[here](https://prometheus.io/docs/practices/pushing/). There is also an
[existing package](https://build.suse.de/package/show/home:jcavalheiro:monitoring/golang-github-prometheus-pushgateway).
- Instead of extending the SUSE Manager Server's configuration UI we could
investigate to run a minion on the same machine and register the server to
itself. This would enable us to handle the activation and deactivation of
monitoring in the same way as for the proxy and other managed systems.
- Instead of shipping data exporters together with the corresponding software or
products in the same channels it could be considered to group them all together
to a *monitoring module* for SLE.
- As an alternative to
[updating the Prometheus configuration](#updating-the-prometheus-configuration)
via files generated from SUSE Manager, we could consider running a daemon on the
same machine were Prometheus is running that would query the SUSE Manager API
and generate the JSON or YAML scrape config accordingly.

# Unresolved Questions
[unresolved]: #unresolved-questions
