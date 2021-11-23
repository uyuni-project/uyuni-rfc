- Feature Name: Hub Reporting
- Start Date: 2021-11-23

# Summary
[summary]: #summary

Brief (one-paragraph) explanation of the feature.

# Motivation
[motivation]: #motivation

- Why are we doing this?
- What use cases does it support?
- What is the expected outcome?

Describe the problem you are trying to solve, and its constraints, without coupling them too closely to the solution you have in mind. If this RFC is not accepted, the motivation can be used to develop alternative solutions.


# Detailed design
[design]: #detailed-design


- Database? => yes
- SQL or NoSQL DB ? => research (Michele)
  * usable in reporting tools
  * how does nosql work
  * pros / cons list
  * available software available in SLES or in openSUSE?
    * if not check license
    * how does the maintenace?
  * effort to implement

- by default use an "internal" DB, but design also for an external DB
- tools to setup and configure the DB. incl. to create accounts (rw and ro)

- taskomatic job to write data into the DB on a Single Server
  - central place to manage the queries used to select/insert data into the reporting table



2 ways to put data into the reporting DB

1. write directly the select queries and write them in tables ready for the report
2. export existing tables 1:1 with a little de-normalize and for the real reporting create views which are used for reports


- Data transfer from Servers to the Hub
  - DB replication or taskomatic job?
  - handle schema differences?


# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?

  * obscure corner cases
  * will it impact performance?
  * what other parts of the product will be affected?
  * will the solution be hard to maintain in the future?

# Alternatives
[alternatives]: #alternatives

- What other designs/options have been considered?
- What is the impact of not doing this?

# Unresolved questions
[unresolved]: #unresolved-questions

- localization for reporting data?
