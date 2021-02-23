- Feature Name: Prometheus TLS support
- Start Date: 2021-02-11
- RFC PR:

# Summary

[summary]: #summary

Add optional support for TLS encrypted and authenticated connection to
Prometheus server and exporters.

# Motivation

[motivation]: #motivation

## Prometheus

In the default configuration it is presumed that untrusted users have access to
the Prometheus HTTP endpoint. They have access to all time series information
contained in the database, plus a variety of operational/debugging
information [[1]](#1).

Applications needing access to Prometheus API:

* _Grafana_

Users needing access to Prometheus API/UI:

* monitoring administrator

## Exporters

Exporters generally only talk to one configured client instance with a preset
set of commands/requests, which cannot be expanded via their HTTP endpoint.
Still, all exposed metrics are available to untrusted users.

> Uyuni should optionally support and automate setting up secure
> configuration of Prometheus and exporters.

# Detailed design

[design]: #detailed-design

## Prometheus

Prometheus 2.24.0 has introduced TLS encryption as well as basic and
client-certificate authentication [[2]](#2). All available configuration options are
described in official documentation [[3]](#3). Basic authentication credentials are
stored in the configuration file. Passwords are hashed with _bcrypt_.

To follow current SUSE Manager security model [[4]](#4) we should consider
implementing following default configuration:

* Upgrade Prometheus to version >= 2.24.1.
* [Optional] Create intermediate certificate authority (CA) dedicated for monitoring.
* [Optional] Create and deploy Prometheus server certificate signed by this CA.
* Configure `tls_server_config` using this certificate.
* Configure basic authentication accounts to map SUSE Manager credentials.

All these steps should be implemented in Salt prometheus-formula. Alternatively
certificate generation and deployment could be moved to a new dedicated
certificates formula.

## Node exporter

Node exporter supports the same configuration options as Prometheus server in
terms of encryption and authentication [[5]](#5). All available options are
described in exporter-toolkit documentation [[6]](#6).

To follow current SUSE Manager security model we should consider encrypting all
the communication between node exporters and Prometheus server. Regarding
authentication, client certificate authentication seems to be the preferred
approach as the certificate will be anyway available on the Prometheus server.
It would involve following configuration steps:

* [Optional] Create and deploy CA signed server certificates for all monitored minions.
* Configure `tls_server_config` in node exporter using these certificates.
* Configure `tls_config.ca_file` in Prometheus job configuration to use server
  certificate [[7]](#7).
* Configure `tls_config` in Prometheus job configuration to use Prometheus
  server certificate and key files for client cert authentication.

Alternatively to last point basic authentication can be configured. Please note
that credentials are stored in Prometheus configuration in clear text. Password
is marked as secret and not exposed via API.

Prometheus service discovery will have to provide information about the
connection scheme http or https of the endpoint.

Implementation affects following components:

* prometheus-formula
* prometheus-exporters-formula
* Prometheus Uyuni SD
* certificates-formula (new optional formula)

## Other components

The intent is to roll over this kind of HTTPS support across all the official
Prometheus exporters in the coming months and the other projects, such as
Prometheus, Alertmanager, Pushgateway [[5]](#5). The functionality is implemented as
part of Prometheus Exporter Toolkit [[11]](#11) and can be added to other exporters.

The state of TLS support for SUSE Manager distributed unofficial exporters at
the time of writing:

### TLS support provided

* Exporter Exporter

### No TLS support

* Apache exporter
* PostgreSQL exporter

Exporter Exporter can be placed in front of insecure exporters and expose
their metrics on the encrypted endpoint. The goal should be though to
provide native TLS support in upstream components.

### Alertmanager

Similarly to Prometheus server also Alertmanager exposes API and UI for monitoring
administrators. Upstream developers plan to add TLS support for Alertmanager in the next
months. Secure configuration of this service should also be considered when
implementation is ready.

Uyuni supports deploying Alertmanager on the same host as Prometheus server. It alows to
use the same server/client certificates as for Prometheus server.

## Certificates generation

### Prometheus server

#### Generate a Prometheus server key and request for signing (CSR)

```
openssl genrsa -out prometheus-server.key 2048
openssl req -sha256 -text -config server/rhn-prometheus-server-openssl.cnf
    -new -key prometheus-server.key -out prometheus-server.csr
```

#### Sign a certificate with CA

```
openssl ca -extensions req_server_x509_extensions -outdir ./
    -config rhn-ca-openssl.cnf -in prometheus-server.csr -batch
    -cert RHN-ORG-TRUSTED-SSL-CERT -keyfile RHN-ORG-PRIVATE-SSL-KEY
    -days 365 -md sha256 -out prometheus-server.crt
```

> By setting `x509_extensions.extendedKeyUsage = serverAuth, clientAuth` in
> openSSL configuration file, the certificate can be used both as the server
> certificate and as client certificate (for authenticating scraping requests).

### Minions (Exporter nodes)

The procedure for generating certificates and private keys for minions is the
same as for the Prometheus server. During onboarding and hostname change the
generated certificates should be distributed to affected minions.

Recreating CA certificate requires updating all server certificates. This could
be avoided if we decide to use basic auth with self-signed certificates (not CA
signed).

## Example configuration
### Prometheus server

`prometheus.yml`
```yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    scheme: https
    basic_auth:
      username: witek
      password: bedyk
    tls_config:
      ca_file: prometheus-server.crt
    static_configs:
      - targets: ['minion-1.tf.local:9090']

  - job_name: 'node'
    scheme: https
    tls_config:
      ca_file: /etc/pki/trust/anchors/RHN-ORG-TRUSTED-SSL-CERT  # CA certificate
      cert_file: prometheus-server.crt                          # client certificate
      key_file: prometheus-server.key                           # client private key
    static_configs:
      - targets: ['minion-2.tf.local:8080']
```

`web.yml`
```yml
tls_server_config:
  cert_file: prometheus-server.crt    # server certificate
  key_file: prometheus-server.key     # server private key
basic_auth_users:
  witek: $2y$10$vMoFFaIhSWxSBYQSAtaUReypiaovz2Gb.UWhYL1BSv58Vfdxn55jG
```

### Node exporter

`web.yml`

```yml
tls_server_config:
  cert_file: minion.crt                   # server certificate
  key_file: minion.key                    # server private key
  client_ca_file: /etc/pki/trust/anchors/RHN-ORG-TRUSTED-SSL-CERT # CA used for signing client/server certificate on Prometheus server
  client_auth_type: RequireClientCert     # require client certificate for authentication
```


# Drawbacks

[drawbacks]: #drawbacks

One important drawback is the increased complexity of deployment. In
particular changing client hostnames or renewing CA certificate will require
updating the certificates on clients.

# Alternatives

[alternatives]: #alternatives

One alternative would be to outsource certificates generation and let users
manage them. Then we would only need to provide configuration options to
point to user generated certificates.

As client/server certificates could also be useful for other purposes, e.g.
OpenVPN formula, it might be preferable to create a new formula for
certificates generation and deployment. Existing implementations
[[12]](#12), [[13]](#13) could be used for inspiration.

# Unresolved questions

[unresolved]: #unresolved-questions

- Which users should be configured on Prometheus server?

There is no PAM based authentication support in Prometheus and thus no simple
way to automatically sync all user accounts between Uyuni server and Prometheus.
To provide that we'd need to put a proxy in front of Prometheus server.

The simplest approach seems to be to statically define a dedicated
administrative user in the Salt formula.

# References

<a name="1">[1]</a>: https://prometheus.io/docs/operating/security  
<a name="2">[2]</a>: https://inuits.eu/blog/prometheus-server-tls  
<a name="3">[3]</a>: https://prometheus.io/docs/prometheus/latest/configuration/https  
<a name="4">[4]</a>: https://documentation.suse.com/external-tree/en-us/suma/4.1/suse-manager/administration/ssl-certs.html  
<a name="5">[5]</a>: https://inuits.eu/blog/prometheus-tls  
<a name="6">[6]</a>: https://github.com/prometheus/exporter-toolkit/blob/master/docs/web-configuration.md  
<a name="7">[7]</a>: https://prometheus.io/docs/prometheus/latest/configuration/configuration/#scrape_config  
<a name="8">[8]</a>: https://www.golinuxcloud.com/create-certificate-authority-root-ca-linux  
<a name="9">[9]</a>: https://www.golinuxcloud.com/openssl-create-client-server-certificate  
<a name="10">[10]</a>: https://github.com/uyuni-project/uyuni/blob/master/spacewalk/certs-tools/rhn_ssl_tool.py  
<a name="11">[11]</a>: https://github.com/prometheus/exporter-toolkit  
<a name="12">[12]</a>: https://github.com/ssplatt/sslcert-formula  
<a name="13">[13]</a>: https://github.com/saltstack-formulas/cert-formula
