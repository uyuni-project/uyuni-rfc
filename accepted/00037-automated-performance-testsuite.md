- Feature Name: performance_testsuite
- Start Date: 2018-01-30
- RFC PR: #64

# Summary
[summary]: #summary

We want to create an automated non-regression testsuite specifically to track performance.

Main objective is to spot performance regression bugs and, to a lesser extent, identify new problematic areas via load generation.

# Motivation
[motivation]: #motivation

We do not have any systematic performance assessment of the product.

We also want to take the chance to enhance our tools and expertise about:
 - load generation
 - cloud computing in general and SUSE Openstack Cloud in particular
 - dashboards and time series databases

# Detailed design
[design]: #detailed-design

High level, the testsuite will configure a SUSE Manager Server, start load generators, collect performance data and push it to a dashboard for storage and analysis.

## Choice of the deployment platform

Options are team hardware (via libvirt), AWS or the ECP Cloud.

We chose the ECP Cloud because:
  - it has plenty of resources available right now (50 vCPUs, 80 GiB of RAM, 150GB storage space compund)
  - it is free
  - it should not suffer from noisy-neighbor problems short-term, as it is underutilized. Should those problems appear, Cloud people offered to isolate our project via a "separate host group" if we prove such problems exist
  - we need to develop sumaform support for OpenStack anyway

## Choice of the main tools
  - Jenkins for automation (already widely used)
  - sumaform for deployment (any other choice would cost more development time)
  - evil-minions for salt minion simulation (in order to keep running costs manageable with thousands of minions)

## Choice of an HTTP load generator

Requirements:
  - necessary protocols: http, https, XMLRPC
  - nice-to-have protocols: WebSockets, others
  - scriptability
  - text-only mode (for CI)
  - abilty to export results at least in one machine-processable format, for visualisation in dashboards

Discarded alternatives:
  - Apachebench: not scriptable
  - wrk: not scriptable
  - Tsung: Erlang, hardly scriptable (complex XML)
  - Artillery: not scriptable
  - Vegeta: request rate is fixed (instead of virtual user number)
  - Siege: not scriptable
  - Hey (formerly known as Boom): not scriptable
  - k6.io: no way to add XMLRPC at the moment

Evaluated alternatives:
  - [locust.io](http://locust.io/)
    - Pros:
      - Scripts are in Python, many people know the language
      - Horizontally scalable
      - XMLRPC example available
      - [WebSockets is also doable](https://gist.github.com/reallistic/dae87055210af82ea6aa4851a60fde11)
      - coroutine based architecture (via [gevent](http://www.gevent.org/))
    - Cons:
      - pre-1.0 version
      - Debated: low performance
        - This article says it's good: [https://www.blazemeter.com/blog/open-source-load-testing-tools-which-one-should-you-use](https://www.blazemeter.com/blog/open-source-load-testing-tools-which-one-should-you-use)
        - This article says it's bad: [http://blog.loadimpact.com/open-source-load-testing-tool-benchmarks](http://blog.loadimpact.com/open-source-load-testing-tool-benchmarks) (even considering numbers there are 4x lower than fair, as they are not normalizing for core usage)
      - Export format is only CSV
  - [Gatling](https://gatling.io/)
    - Pros:
      - WebSocket is supported
      - Debated: high performance
        - This article says it's good: [http://blog.loadimpact.com/open-source-load-testing-tool-benchmarks](http://blog.loadimpact.com/open-source-load-testing-tool-benchmarks)
        - This article says it's bad: [https://www.blazemeter.com/blog/open-source-load-testing-tools-which-one-should-you-use](https://www.blazemeter.com/blog/open-source-load-testing-tools-which-one-should-you-use)
    - Cons:
      - Scripts are in a Scala-based DSL, few people know the language, needs an IDE
      - Not horizontally scalable
      - No XMLRPC support ([can be done manually, but it's tedious)](https://stackoverflow.com/questions/36620768/how-to-invoke-a-soap-web-service-using-gatling-2-2-0))
      - Debated: documentation is not really good
        - We found it lacking
        - This article says it's good: [http://blog.loadimpact.com/open-source-load-testing-tool-review](http://blog.loadimpact.com/open-source-load-testing-tool-review)
      - Export format is only CSV
  - JMeter: [http://jmeter.apache.org/](http://jmeter.apache.org/):
    - Pros:
      - Stable, professional and maintained since 20 years
      - Huge, active community even today
      - Documentation is good
      - XMLRPC is supported
      - WebSocket is supported
      - Export format is somewhat standard (JTL: [https://wiki.apache.org/jmeter/JtlFiles)](https://wiki.apache.org/jmeter/JtlFiles)), CSV possible as well
    - Cons:
      - Scripts are in XML
      - [They could be generated in Ruby via a gem](https://github.com/flood-io/ruby-jmeter)
  - [The Grinder](http://grinder.sourceforge.net/)
    - Pros:
      - Scripts are in Python (albeit executed on the JVM via Jython, meaning only some modules are available)
      - XMLRPC example available
      - Scriptable output format
      - Debated: high performance
        - This article says it's good: [http://blog.loadimpact.com/open-source-load-testing-tool-benchmarks](http://blog.loadimpact.com/open-source-load-testing-tool-benchmarks)
        - This article says it's bad: [https://www.blazemeter.com/blog/open-source-load-testing-tools-which-one-should-you-use](https://www.blazemeter.com/blog/open-source-load-testing-tools-which-one-should-you-use)
      - Documentation is good
    - Cons:
      - Looks unmaintained, or at least stagnant (last version 3.11 is from 2012)
      - No WebSocket support possible
      - Not horizontally scalable

Final reasoning:
 - locust.io seems like the simplest solution to fit the needs, both implementation and maintenance wise. It is not fully-featured
 - JMeter can do everything, but we fear maintaining XML files to be tedious and hard to understand. Adding ruby-jmeter on top would make the result more readable, but it is one extra moving piece
 - Gatling is interesting, but we do not want to force people to install a Scala compiler or IDE in order to contribute. At least initially the script codebase will be small and easy
 - Grinder is too stagnant, we fear painting ourselves in a corner for a new project like this

Moreover, only JMeter and locust.io support horizontal scaling, which will be useful in future scalability tests, so:
  - we choose locust.io *for now*
  - if anything goes wrong and it turns out it does not fulfill our needs, we can always turn to JMeter quickly (because initial investment in locust.io is expected to be small)

## High level workflow
  - a permanent host running Prometheus and Grafana will be created
  - a Jenkins pipeline (stored here: [https://github.com/SUSE/susemanager-ci](https://github.com/SUSE/susemanager-ci), eg. in a new directory called performance) will:
    - get the testsuite `main.tf` sumaform configuration file from [https://gitlab.suse.de/galaxy/sumaform-test-runner](https://gitlab.suse.de/galaxy/sumaform-test-runner)
    - run sumaform to deploy needed VMs (server, load generators...)
    - execute the tests:
      - one or more [locust.io] runs, which will perform load tests on specific URLs (pages/Javascript APIs/download endpoints...) defined in locustfiles
      - one or more Python script runs, which will test functionality of SUSE Manager through the XMLRPC API
  - meanwhile, the permanent Prometheus server will scrape data from the system under test and aggregate it in a local database
  - Grafana will be used for result visualization, analysis, thresholding, alerting extracting data from the Prometheus server

## Choice of frameworks
  - we do not expect to need a real browser, so we are not considering to use Capybara at this time
  - we do not expect to need BDD, so we are not considering using Cucumber at this time

Note: we expect most tests to be implementable via XMLRPC API plus very light scripting of the HTTP load generator (eg. login + visit a page or call a frontend API), and plan with this assumption in mind.

# Drawbacks
[drawbacks]: #drawbacks

 - we get another independent testsuite and we will need to maintain it

# Alternatives
[alternatives]: #alternatives

  - deployment to dedicated libvirt servers instead of ECP Cloud
    - pro: no noisy neighbor problems
    - con: capacity and capacity planning
  - base the testsuite on top of the existing one, or as an extension of the existing one
    - pro: easier to simulate complex UI interactions
    - con: a browser is a big extra moving piece that will inevitably disturb measurements
  - use JMeter instead of locust.io
    - pro: more stable, feature complete
    - con: harder to implement and maintain tests (Turing-complete XML instead of Python)

# Unresolved questions
[unresolved]: #unresolved-questions

 - how to import data from locust.io to Prometheus
 - how to store data in Prometheus long-term
