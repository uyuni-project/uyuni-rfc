- Feature Name: projects_graduation
- Start Date: 2026-10-30

# Summary
[summary]: #summary

This RFC describes a graduation process for Uyuni side projects.

# Motivation
[motivation]: #motivation

Many projects around Uyuni popped up in the past few months or years.
So far there is no place listing them and their status.
Users will want to be able to find those side projects and in which state their are in.
For instance, is this AI agent using Uyuni safe enough? Is it maintained?

# Detailed design
[design]: #detailed-design

A graduation process is already in place in several other open source organizations like The Document Foundation or [CNCF](https://contribute.cncf.io/projects/lifecycle/).
This process doesn't intent to reinvent the wheel, but take what works in them and simplify to tailor it to Uyuni's need.

The Document Foundation Engineering Steering Committee: [description](https://wiki.documentfoundation.org/CommunityBylaws#Engineering_Steering_Committee)
CNCF Technical Oversight Committee: [documentation](https://github.com/cncf/toc/tree/main/operations)

## Deliverables

This project deliverables are:

* A page on the Uyuni web site listing the projects and their status.
  This should ideally be easy to maintain in the long run.
  This will be the main outcome for users.

* A page documenting the graduation process.
  This aims at developers for them to get their project reviewed and listed on the page.

## The process

### States

The projects can be in one of the following states:

1. **Sandbox**: experimental phase, there was no due diligence process started to assess the project.
  It could change API and behavior at any time.
  Sandbox project can live in a different GitHub organization or even outside of GitHub.
  The Technical Committee will only ensure that sandbox projects are not offending or violating ethic and laws.

2. **Incubator**: The project is getting more adoption, has focus on stabilization.
  At this stage the project starts to be assessed by the Technical Committee.
  Incubator projects are moved under the uyuni-project GitHub organization.

3. **Mature**: The project is widely used, stable, maintained, and has been assessed by the Technical Committee.

4. **Archived**: Old, no longer maintained projects that could present a risk.

## Guiding principles

Every project must adhere to the [openSUSE Code of Conduct](https://en.opensuse.org/Code_of_Conduct).
Failure to do so would immediately reject the project.

Each project must be and use software that is not [banned by openSUSE](https://en.opensuse.org/openSUSE:Build_Service_application_blacklist).

As a reference, Uyuni as part of openSUSE, and thus any project under the Uyuni umbrella, adheres to its [guiding principles](https://en.opensuse.org/openSUSE:Guiding_principles).

openSUSE is creating an AI policy and Uyuni will align on it.
For reference, the state of the discussion can be found on the [AI Portal](https://en.opensuse.org/Portal:AI).

### Technical Committee

The Technical Committee would be composed of people from several backgrounds, representing the interests of the wider community.
This means, it would be composed by people from different affiliations and at least:

* one developer
* one power user
* one tester
* one release engineer
* one technical documentation writer
* one marketing / advocacy person

### Due diligence

The due diligence is the investigation of a project to assess if it can graduate to the **mature** state.
This needs to cover several aspects, like:

* Does it have security issues?
  This may be very hard to achieve, considering the average age of opened CVEs could be more realistic.
* Does it have processes to release, report issues, report CVEs?
* Does it have a reliable test framework?
  Evaluating what is tested, at which frequence, the status of the tests.
  This could even be used to archive a project if required.
* Is the documentation complete enough?
* Does it cover a general user need?
  How many adopters does the project have?
* Is the interface localized / localizable?
* Is the interface accessible?
  This may not apply to every project.

The requirements for moving from one stage to the other will be defined by the Technical Committee.

# Drawbacks
[drawbacks]: #drawbacks

This will require a committee to review the projects and evaluate their status.
This is a new task that is not covered by anyone at the moment.

# Alternatives
[alternatives]: #alternatives

This process could be simplified to a simple web page listing the projects we know about and a link to their home.
This would show off less interest and care in the projects.

# Unresolved questions
[unresolved]: #unresolved-questions

* Finalize the Technical Committee composition, election, mandate duration.
* Should we add affiliation quota on the Technical Committee?
  For example no more than one third of one affiliation.
