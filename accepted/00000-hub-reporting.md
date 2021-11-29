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

The data should be made available in a postgresql database. We considered using other database types,
but the increased maintenance effort for new packages and limited knowledge about NoSQL databases
let us stay with the good well known postresql database.
Also postgresql seems to be accepted in most Reporting tools as datasource, while NoSQL databases
are not supported, or only via standard DBMS modules. Native support was rarely available.

## The Database
We design for the possibility to use an external DB for the reporting, while in the default setup
we consider to use the available postgresql server on Uyuni. We will use a different database name
and login data.
The database needs to be made available on the network to either connect with the reporting tool
or with the Hub to gather the data.
The connection should be secured with SSL using the certficiates we configure anyway for Uyuni Server.
If possible the connection to the main Uyuni DB from the outside should be forbidden.

The database schema on the Uyuni Server and the Hub should be the same.
We provide a new package to setup the reporting DB schema and tools to setup and manage the reporting
database. The management tools should support
- Database setup and schema initialization
- Database schema migration
- Simple User management

The default setup create a Read/Write Admin User to manage the database and write the data from the
main Uyuni Database into the Reporting DB.
A User created for a reporting tool or for Uyuni Hub to gather the data should be a Read-Only user.

## The Database Schema

The schema should export the most important tables from the main Uyuni Database as a slightly de-normalized
variant containing only data which are relevant for a report.

A ready-to-use report can be provided with views doing joins over multiple tables.
No foreign keys should be used to make data update and refreshing easier and independent from the order
of the tables.

Every table gets an extra column for the uyuni server id of server which provide the data. On a single
Uyuni Server this is a standard value `1` which represent "localhost". On the Hub it will be replaced
with the real server id the managed server has in the hub database.

Indexes should be set on the typical columns which might be searched for.

Every row should get a report timestamp column which is set to the time when the data were exported
from the main Uyuni Server database.

Data which belong to the traditional stack only (like osad status) should not be made available in the
reporting database as the traditional stack will be deprecated soon.


## Adding Data to the Reporting DB

On an Uyuni Server a taskomatic job is responsible to fetch and prepare the data from the main Uyuni
Database and insert them into the Reporting Database.
The job should be written that Uyuni and Reporting Database could be on different Hosts.

Keeping the code which insert the data into the reporting DB in sync with the Reporting Database Schema
is a requirement.

## Collecting Data on the Hub

On the Uyuni Hub we have an additional taskomatic job which collect the data from all the managed
Uyuni Server and insert them into the Hub Reporting Database which could be again an external DB.
We must parallelize the jobs to be able to gather the data from all Servers even in a large environemnt.
The goal is to get the data from 1000 Servers in maximal 3 hours.

The database schema on the Hub and the Uyuni Servers might differ as not all server might be updated
at the same point in time. To support schema differences we should:

- query tables on the Uyuni Server and compare them with the tables available on the hub. 
  Only tables, which exists on both ends, will be synchronized
- query columns of the table in the Uyuni Server and compare them with the columns available on the Hub table.
  Only columns which are available on both sides will be synchronized. Columns available only on the Hub will
  stay empty. Columns only available on the Uyuni Server will not be exported.



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
  - Reporting tools often support postgresql directly why we could not find a similar good support
    for NoSQL databases
  - very limited knowledge in NoSQL makes it hard to decide for a technology we do not know
  - use case seems better to fit of SQL (based on a very limted knowledge about NoSQL databases)
  - no obvious killerfeatures provided by NoSQL which we want to use


# Unresolved questions
[unresolved]: #unresolved-questions

- localization for reporting data?
