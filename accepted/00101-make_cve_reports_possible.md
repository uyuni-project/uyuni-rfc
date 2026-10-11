- Feature Name: make_cve_reports_possible
- Start Date: 2024-04-12 

# Summary
[summary]: #summary

Create a meaninful CVE Audit that would ran as a report and it would be sorted per CVE-Number

# Motivation
[motivation]: #motivation

- Why are we doing this? The CVE Audit is static and does not provide an overview from the hosts affected by a CVE.
- What use cases does it support? Produce real-time reports sorted by CVE-Number for the auditors and security teams
- What is the expected outcome? Have a table with the CVE Numbers and what hosts are affected. Have a report that could be called via REST-API and also could be integrated on every CI/CD workflows from operational teams.

We have a static and not a understable overview from the hosts affected by a CVE. As today, one should open the CVE Audit option on the menu, search for a CVE number, add to the form and expect a list from hosts affected by only this CVE. If there is a higher number from CVEs would be a lot of working doing a manual search per CVE Number. This makes the life from infrastructure managers so difficult -it is not possible to have an overview that is always updated and showed in the dashboard -
and it is also not possible to have a generated report per PDF from the hosts affected by a CVE(a report sorted per CVE-Number. It should be also provided a way to generate this reports per REST-API and make it possible to have it integrated in a CI/CD Workflow.

# Detailed design
[design]: #detailed-design

Steps for the implementation:
- Create a stored procedure/function on the reporting DB making it call on demand by the frontend/backend code.
- Get some space on the main overview to place the results from this query
- Create a view using the function and make possible via configs to setup the timeout and how often it would be called
- Place the view results on the overview dashboard

    Visual examples:

    CVE-Number         How to fix                      Report Date: 12.04.2024 03:19PM
    ----------------------------------------------------------------------------------
    CVE-123456         
       host1           Install update-123
       host2           Install the latest fix
       host3           Fixes are not delivered anymore 
                                                                  Download cve-report-12.04.2024-03:19pm.pdf



# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?

  * If the timeout is not set it could case some data issues as congestion
  * If the CVE Database is not updated(network issues, disk space, permissions) it could cause false positives
  * Database
  * No, because I would like to have develop it as a module - independent of other components and documented on how to remove it if needed

# Alternatives
[alternatives]: #alternatives

 - What other designs/options have been considered? Use the same code as Neuvector do for the CVE Databases updates and also reporting
 - What is the impact of not doing this? If we do not implement this would not be possible to have a audit overview for the linux infrastructure

# Unresolved questions
[unresolved]: #unresolved-questions

- What are the unknowns? Do we have enough space on the overview page
- What can happen if Murphy's law holds true? The worst thing that could happen: if that does not work we can disable it via enable_cve_audit: true|false 
