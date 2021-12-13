- Feature Name: Hub Reporting
- Start Date: 2021-11-23

# Summary
[summary]: #summary

Brief (one-paragraph) explanation of the feature.

# Motivation
[motivation]: #motivation

In a Uyuni Hub scenario we have the Hub to prepare and provide content for multiple other Uyuni Servers.
The goal is now to get data from these Servers back and have combined reporting data available on the Hub.

The data should be made available for external Reporting Tools.

If possible, the data should also be usable on a single Uyuni Server with the same mechanism.


# Detailed design
[design]: #detailed-design

The data should be made available in a PostgreSQL database. We considered using other database types,
but the increased maintenance effort for new packages and limited knowledge about NoSQL databases
let us stay with the good well known PostgreSQL database.
Also PostgreSQL seems to be accepted in most Reporting tools as data source, while NoSQL databases
are not supported, or only via standard DBMS modules. Native support was rarely available.

### The Database
The main database is a PostgresDB in the hub system (but in the future it will be possible to 
use also an external db): it stores all the information collected from all the server, and eventually
aggregates them. Other databases with the same schema are also present in all the server, to collect 
information for that system.
The hub database needs to be made available on the network to either connect in a secure way (using the SSL
certificates provided by Uyuni Server) with the reporting tool or with the Hub to gather the data. 
If possible the connection to the main Uyuni DB from the outside should be forbidden.

### The Database Schema

The schema should export the most important tables from the main Uyuni Database as a slightly de-normalized
variant containing only data which are relevant for a report.

A ready-to-use report can be provided with views doing joins over multiple tables.
No foreign keys should be used to make data update and refreshing easier and independent from the order
of the tables.

Every table gets an extra column for the Uyuni server id of server which provide the data. On a single
Uyuni Server this is a standard value `1` which represent "localhost". On the Hub it will be replaced
with the real server id the managed server has in the hub database.

Indexes should be set on the typical columns which might be searched for.

Every row should get a report timestamp column which is set to the time when the data were exported
from the main Uyuni Server database.

Data which belong to the traditional stack only (like osad status) should not be made available in the
reporting database as the traditional stack will be deprecated soon.

## Installation
The reporting tools will be installed by default; all the upgrade to a newer version, will install the 
reporting tools as well.

We provide a new package installed in the hub system:
- to setup the reporting DB schema,
- to setup and manage the reporting database,
- to setup and manage DBs in all Uyuni Server.

The package will also setup a taskomatic job to retrieve informations from all the other SUSE Manager Server
database.
All the other information required (e.g. Uyuni Server info) will be retrieved by already existing configuration.

### Database management: setup and account

#### Uyuni Hub
On the hub side, the management tools should support:
- Database setup and schema initialization
- Database schema migration
- Simple User management. The default setup will create a Read/Write user, to manage the database and write the data from into the Reporting DB. This user and the DB connection parameters are written into `/etc/rhn/rhn.conf` similar to the default DB options.

#### Uyuni Server
On the server side, during installation, hub should create its own read-only user on the Reporting Databases of the single Servers. 
This user is used by the hub to read data from the Uyuni Server DB.
As the Servers are managed with salt, we will write a state to create an account.
The username and password are generated on the Hub and provided as pillar data.
On the server the state take care of the existance of the account and the Hub can store the parameters
in its database under the system entry. 

## Workflow

#### Uyuni Server: retrieve and organize Data

On an Uyuni Server a taskomatic job is responsible to fetch and prepare the data from the main Uyuni
Database and insert them into the Reporting Database. The infomation will be stored in a local DB and
collected by Uyuni Hub.
The job should be written in a way, that Uyuni Hub and Reporting Database could be on different Hosts.

Keeping the code which insert the data into the reporting DB in sync with the Reporting Database Schema
is a requirement.

Implementing a taskomatic simple java job should be sufficient as we need only one task which run at a
certain point in time.

#### Uyuni Hub: Collecting Data on the Hub

On the Uyuni Hub we have an additional taskomatic job which collect the data from all the managed
Uyuni Server and insert them into the Hub Reporting Database which could be again an external DB.
We must parallelize the jobs to be able to gather the data from all Servers even in a large environment.
The goal is to get the data from 1000 Servers in maximal 3 hours.

### Consistency during upgrade
The database schema on the Hub and the Uyuni Servers might differ as not all server might be updated
at the same point in time. To support schema differences we should:

- query tables on the Uyuni Server and compare them with the tables available on the hub. 
  Only tables, which exists on both ends, will be synchronized
- query columns of the table in the Uyuni Server and compare them with the columns available on the Hub table.
  Only columns which are available on both sides will be synchronized. Columns available only on the Hub will
  stay empty. Columns only available on the Uyuni Server will not be exported.

Implementing this as a taskomatic QueueJob could be an option. The Queue Job is started and collect a list
of candidates. A number of parallel workers can be specified to connect to every single server instance.

### Show data on reporting tool
In order to use the data stored in the hub and/or in the servers as a datasource for external reporting tools,
the admin should create a read-only user to query information from DBs.

## Documentation
Documentation will cover:
- reporting tool architecture
- user creation/management
- ...

# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?

  * obscure corner cases
  * will it impact performance?
  * what other parts of the product will be affected?
  * will the solution be hard to maintain in the future?

# Alternatives
[alternatives]: #alternatives

- SQL or NoSQL DB?
  - Reporting tools often support PostgreSQL directly why we could not find a similar good support
    for NoSQL databases
  - very limited knowledge in NoSQL makes it hard to decide for a technology we do not know
  - use case seems better to fit of SQL (based on a very limited knowledge about NoSQL databases)
  - no obvious killer features provided by NoSQL which we want to use


# Unresolved questions
[unresolved]: #unresolved-questions

- Is implementation in Java with Hibernate possible and fast enough for
  * filling the report table in a single Server?
  * to collect the data from multiple single Servers and insert them into the Hub DB?

- should we use the same tooling for the DB schema as we use for the main Uyuni Schema?

- where and how to configure the connection parameters for the reporting database
  * on a single Server ?
    - The R/W account should be in `/etc/rhn/rhn.conf` like the other DB account
  * on the Hub for every managed single Server?
    - As the Hub "manages" the single Servers, it should create an own Read-only account
      and store it in its DB under the system item.



