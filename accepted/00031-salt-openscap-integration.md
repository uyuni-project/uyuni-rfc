- Feature Name: Openscap integration for Suse Manager Salt clients
- Start Date: 2017-01-30
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

Verify SCAP security policy compliance for Suse Manager salt clients

# Motivation
[motivation]: #motivation

At the moment, it is possible to do a policy scan only for traditional clients.
The goal of this RFC is to leverage Salt and seamlesly bring the same functionality to Salt clients.
It should be possible to use the existing UI with no modifications.

# Detailed design
[design]: #detailed-design

## Workflow Example

1. go to Systems > [ click on a Salt client System ] > Audit > Schedule
2. in `Command-line Arguments` box put: `--profile Default`
3. in `Path to XCCDF document *` box put: `/usr/share/openscap/scap-yast2sec-xccdf.xml`
4. the `Schedule no sooner than` box should already have default values
5. click Schedule
6. `List Scans` page should be shown
7. the task should be shown in the `Schedule` page while pending
8. once completed:
  - the task should be shown in `Systems` > [ click on the same Salt client System ] > `Audit` > `List Scans` once complete
  - The results should also be saved to Suse Manager's DB

9. clicking on a job in the list should show:
  - fetch the results from the DB
  - show:

    - the meta info of the scan
    - the `XCCDF Rule Results`
    - link to `scap-yast2sec-oval.xml.result.xml` **this can't be generated from xccdf-results.xml**
    - link to `xccdf-report.html` **this file can be generated from xccdf-results.xml using oscap**
    - link to `%2Fusr%2Fshare%2Fopenscap%2Fcpe%2Fopenscap-cpe-oval.xml.result.xml` **this link appears to be broken**
    - link to `xccdf-results.xml`

## Implementation

Note: the limitations imposed below are only there because the scope of the RFC is OpenSCAP feature parity with traditional Suse Manager clients.

1. A Salt execution module should be implemented as a wrapper for `/usr/bin/oscap`
2. The salt module should be named `openscap`
3. For the purpose of this RFC, the module should only have a wrapper function for `oscap xccdf` and should only be capable of performing `oscap xccdf eval` operations (to be expanded later when required)
4. This function should accept only the parameters that are used for `oscap xccdf eval` with the traditional clients (to be expanded later).
  - `--profile`
  - input xml file

5. Running oscap evaluation on a minion should work like this: `salt <minion-id> openscap.xccdf eval profile=Default /usr/share/openscap/scap-yast2sec-xccdf.xml`

    Note: `/usr/share/openscap/scap-yast2sec-xccdf.xml` is a file located on the minion

6. Return, store and display: [**a similar approach is used for traditional clients**]

  - Push the generated files (results.xml, report.html, oval.results.xml) to salt-master - `cp.push` could be useful here
  - Include in the returned dict the path where the files will be pushed (they would need to have a unique id - maybe the id of the job)
  - Extract the data from results.xml and store it in the Suse Manager's DB

    We need to extract the data from xml because we need to save it in Suse Manager's DB.
    Suse Manager knows best what it needs to be extracted so I think this should be extracted by Suse Manager.

  - Use the results from DB and the uploaded files to generate the page in **Step 9**

## Integration

According to workflow:

  - **Steps 1** to **Step 4** from the `Workflow Example` above are already in place.
  - **Step 5** would require some adaptation in order to use the `openscap` module when targeting a Salt client.
  - **Step 6**:

    - adapt Suse Manager to the new way salt uploads the generated files
    - process xml files in the java code to insert the results in DB

      see https://github.com/SUSE/spacewalk/blob/Manager/backend/server/action_extra_data/scap.py)

  - **Step 7** should require only minor or no adaptation, the salt jobs should be already shown there.
  - **Step 8** might require some adaptations in order to list the completed salt minion oscap scans.
  - **Step 9** the UI is already in place, expecting minon adaptations

# Drawbacks
[drawbacks]: #drawbacks

Implementation - Step 6:

  - the results.xml file needs to be transferred in order to extract the data on the server side
  - the oval.results.xml file needs to be transferred to master
  - the minion has to name the file with an unique name and inform master

Implementation - Step 6 - Alternative 1:

  - because `oscap` can only generate the results as an xml file, the data needs to be extracted from that file and returned from the salt module function (on the minion side)
  - additional effort needed to implement a way to generate the xml and html report from the results data stored in the DB

Implementation - Step 6 - Alternative 2:

  - the results.xml file needs to be transferred in order to extract the data on the server side
  - the oval.results.xml file needs to be transferred to master
  - the minion has to name the file with an unique name and inform master
  - the master would download the file at a later time and maybe the minion would not even be there by that time

# Alternatives
[alternatives]: #alternatives

Implementation - Step 6 - Alternative 1

  - Extract the results data from the result.xml file generated by `oscap`
  - The function should return the extracted data as a dict (that would be formatted according salt's config)
  - Store the results in the Suse Manager's DB
  - Suse Manager should generate the **Step 9** page and files in **Step 10** using the results from DB (to be determined how much effort this would need)

Implementation - Step 6 - Alternative 2:

  - Generate an event that would be picked up by the salt-master
  - Return the path to the results.xml file generated by `oscap` in the job output (or embedded in the event)
  - Fetch the results file from the minion and save it on master (it would need to have a unique id - maybe the id of the job)
  - Extract the results data from the pushed results file
  - Store the results in the Suse Manager's DB
  - Use the results from DB to generate the page in **Step 9**
  - Use `oscap xccdf generate --format html report --output /tmp/report.html /tmp/results.xml` to generate the html report from the pushed results file
  - Show link to the pushed results file

# Unresolved questions
[unresolved]: #unresolved-questions
