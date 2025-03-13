- Feature Name: A Health Check tool for Uyuni
- Start Date: 2024-11-03


# Summary

[summary]: #summary

The Uyuni Health Check Tool is conceived as a solution aimed at optimizing the management of Uyuni environments by providing timely insights. Its goal is to enhance the proactive maintenance capabilities of administrators, ensuring high performance and stability across the Uyuni infrastructure. Simultaneously, the tool facilitates a more efficient troubleshooting process for engineers and support teams, enabling them to address and resolve any issues. By integrating into the Uyuni ecosystem, this tool seeks to improve the overall health and reliability of the system.

# Motivation

[motivation]: #motivation

Developing a Health Check Tool for Uyuni is becoming more critical with each passing day. We have an increasing number of bug reports and a bug report usually takes a lot more time due to the extensive communication overhead involved. We need a tool that helps identify issues quickly and present the state of Uyuni health to all the stakeholders on each level from users to support and engineering.


## Use cases

**User story 1**

As a system administrator using Uyuni, I want a comprehensive health check tool that can efficiently assess the overall health and performance of the Uyuni infrastructure and its components. This tool should provide valuable insights into the system's status, detect potential issues, and offer recommendations for improvements, enabling me to proactively maintain and optimize the Uyuni environment.

**User story 2**

As an engineer responsible for maintaining the Uyuni codebase, I want to efficiently investigate and fix reported bugs or performance issues within the Uyuni infrastructure. To expedite the debugging process and ensure a stable codebase, I would like to leverage the capabilities of the integrated health check tool, which will help me identify any underlying health-related problems that could be contributing to the reported bug. I also need this tool to consume the provided supportconfig and help me identify any potential issues before I dive into the huge amount of logs.


## Expected outcome

* Proactive Monitoring and Maintenance: Enable system administrators to proactively monitor the health and performance of the Uyuni infrastructure. By providing comprehensive insights into the system's status, the tool aims to help administrators detect and resolve potential issues before they escalate into significant problems.

* Streamlined Debugging Process for engineers: Assist engineers and developers in quickly identifying and addressing bugs or performance issues within the Uyuni codebase.

# Detailed design

[design]: #detailed-design


## Component Overview

### Health-Check

* Loki/Promtail: These two components are for log aggregation, indexing and querying. Loki acts as the centralized logging system, storing and managing logs, while Promtail is deployed on the Uyuni server to collect logs and forward them to Loki.

* Grafana: Utilized for visualization, with dashboards displaying metrics, logs, and alerts, facilitating an integrated view of system health and performance.

* Uyuni-Health-Exporter: A custom exporter to gather specific metrics related to Uyuni server health, including database, service status, and resource usage.

* Alerting System: Leveraging Loki and Prometheus alerting mechanism, configured to monitor critical metrics and log patterns, triggering alerts based on predefined thresholds. Using Alertmanager for sending notifications.

Proof-of-Concept: https://github.com/uyuni-project/poc-uyuni-health-check

### Saline

Saline is an addition for Salt used in Uyuni aimed to provide better control and visibility for states deployment in the large scale environments. It can provide metrics related to Salt events and `state.apply` process on the minions.

Proof-of-Concept: https://github.com/vzhestkov/saline

## Configuration and Deployment

This RFC proposes the following solutions:

### Integrated solution: extending existing monitoring stack

* Monitoring Formula Integration: Loki/Promtail and Uyuni-Health-Exporter configurations are managed via Uyuni's monitoring formula, ensuring seamless integration and ease of deployment. Making Saline and Health-Check a part of the current Monitoring formulas.

* Additional Monitoring Formulas: Similar to the previous approach, integration with current Monitoring stack but using a separated formulas.

![monitoring stack integration](images/health-check/integration-monitoring-stack.png)

### Standalone solution: containerized deployment including Loki, Promtail and Grafana

* Containerized Deployment: The Health-Check components, including Loki, Promtail, Grafana, and the Uyuni-Health-Exporter, are deployed as containers sharing the same network, allowing TCP communication between containers. Running all containers within the same POD would be also possible, but it would limit the deployment method on Kubernetes to be running all on the same cluster node.

![standalone diagram](images/health-check/standalone.png)

* Communication with Uyuni server: The approach to establishing communication with the Uyuni server lies in the underlying infrastructure setup. When deployed in a standalone environment, the system leverages Podman's networking capabilities to facilitate connectivity. This involves configuring Podman containers to ensure they can communicate effectively with the Uyuni server, using Podman's built-in networking features such as container-specific network configurations. Alternatively, in environments where Kubernetes is employed, communication with the Uyuni server is managed through Kubernetes networking principles.

* Storage and Persistence: Utilizing persistent storage solutions for logs and metrics data, ensuring data integrity and availability for historical analysis.

![exporter internal diagram](images/health-check/internals.png)

* Container Deployment Function: Design a generic container deployment function in Python that abstracts the container runtime interface. This function will initially support Podman but is designed to allow easy extension to other container orchestration platforms like Kubernetes. It should be standalone, allowing the tool to run disconnected environments but it will be also integrated into `mgradm`, keeping `mgradm` as the single entry point for the users to manage the containerized Uyuni server deployment.

* This solution is also suitable for smaller deployments, e.g., running all containers on a single node and deploying the Health-Check-Tool with a default configuration in a short time.

### Disconnected solution: containerized deployment without access to an Uyuni server (via supportconfig)

No access to an Uyuni server or existing monitoring stack, only access to a supportconfig. The Infinity Datasource Plugin is installed in Grafana. This Datasource pulls metrics data from the Supportconfig-Exporter endpoints.

![standalone disconnected diagram](images/health-check/standalone-disconnected.png)

## Components

### Component 1: Exporters

#### Uyuni-Health-Exporter

Goal: Configure the Uyuni-Health-Exporter to gather metrics from the Uyuni server and managed systems. The Uyuni-Health-Exporter uses Salt runners to gather metrics.

Steps:

  - Deploy the Uyuni-Health-Exporter as a containerized application.
  - Ensure the Uyuni-Health-Exporter is accessible for Prometheus to scrape metrics.
  - Ensure the Uyuni-Health-Exporter can run Salt runner commands targeting the server.

#### Supportconfig-Exporter (disconected solution)

Steps:

  - Deploy the Supportconfig-Exporter as a containerized application.
  - Ensure the Supportconfig-Exporter is accessible for the Infinity Datasource Plugin to scrape metrics.

### Component 2: Prometheus

Goal: Set up Prometheus to scrape metrics from the Uyuni-Health-Exporter and evaluate alerting rules.

Steps:

  - Scrape Configuration: Add the Uyuni-Health-Exporter endpoint to the Prometheus configuration.
  - Alerting Rules Definition: Create alerting rules to define conditions for triggering alerts based on metrics from the Uyuni-Health-Exporter.
  - Alertmanager Configuration: Set up Alertmanager to handle alerts generated by Prometheus, including notifications.

### Component 3: Grafana

Goal: Use Grafana to visualize metrics and alerts from Prometheus.

Steps:

  - Add Prometheus as a data source in Grafana.
  - Create dashboards to visualize metrics from the Uyuni-Health-Exporter.
  - Configure panels within dashboards to display alerts based on Prometheus data.

### Component 4: Loki and Promtail

#### Loki setup

Goal: Deploy and configure Loki to serve as the centralized log aggregation system for collecting, storing and querying logs from the Uyuni environment.

Steps:

  - Deployment: Install Loki on the Uyuni infrastructure as a container that is part of the Uyuni-Health-Check Pod or sharing the same network than the `uyuni-server` container.
  - Configuration: Customize the Loki configuration to define storage locations for logs, retention policies and other operational parameters.
  - Service Discovery: Configure Loki to discover targets for log collection, focusing on integration with the Uyuni-Health-Exporter and Uyuni components.

#### Promtail setup

Goal: Configure Promtail to collect logs from the Uyuni server and managed systems, forwarding them to Loki for aggregation and analysis.

Steps:

  - Deployment: Install Promtail on the Uyuni infrastructure as a container that is part of the Uyuni-Health-Check Pod.
  - Configuration:
    - Edit the Promtail configuration to define the paths of log files to monitor. In the containerized Uyuni environment, the Promtail container must be configured to have read access to mapped volumes that correspond to the log locations of the Uyuni server container.
    - Configure Promtail to forward logs to the Loki instance.


### Component 5: Supportconfig metrics gatherer

Stakeholders: Engineers and Supporters

Goal: Extract relevant metrics from supportconfig files.

Configuration: No extra configuration needed apart from the path to the supportconfig files.

### Component 6: Saline

Configuration: Deploy as a monitoring formula.


## Alerting and notifications

* Labels: Alerts are categorized by labels like severity (e.g., Critical, Warning, Info), allowing for a prioritized response and management.

* Notification Channels: Configured within Alertmanager to support various notification mechanisms.

* Alerts and Recommendations via Loki:
    * Loki Querying: Utilize the Loki API to query log data for patterns indicative of issues or anomalies. This requires crafting LogQL queries tailored to the types of issues Uyuni Health-Check Tool aims to detect.
    * Alert Generation: Employ the Loki Ruler component to define alerting rules. These rules can be dynamically generated or updated based on the Uyuni Health-Check Tool configuration, allowing for customizable alert conditions.

* Implementing alerts and recommendations involve:
    * Defining LogQL Queries: Writing LogQL queries that match the relevant conditions.
    * Configuring Alert Rules: Using the Loki Ruler to define alert rules based on LogQL queries. These rules specify the conditions under which alerts should be triggered and the severity levels.
    * Setting Up Notification Channels: Configuring the notification channels in Alertmanager to send alerts.
    * Recommendation Logic: For recommendations, the alerting mechanism can be extended with additional logic to suggest actions.


## Metrics

* Server status and resource utilization

* Database health and integrity

* Status of relevant Uyuni services


## How is the Uyuni-Health-Exporter going to access to uyuni-server container? For example, to query the database.
As mentioned, the Uyuni-Health-Exporter needs to have access to the `uyuni-server` container. It does need to query the database and also execute some Salt runner jobs to gather metrics. If the Uyuni-Health-Exporter runs in a separated container than the Salt Master, then we can make the Uyuni-Health-Exporter container to run in the same network as the "uyuni-server", and only then TCP sockets are available to use.

There are some Salt runner jobs that requires access to Salt Master Event publisher, currently exposed via IPC sockets. This makes it tricky to access these sockets from a different container. Some metrics might not be available until we move to TCP sockets for the Salt Master Event publisher in this case.

Alternatively, we could make the "Uyuni-Health-Exporter as part of the server-image, even if not running by default. Then it is up to the Health Check Tool or Monitoring formula to start it. This would solve the current issue of not having access to the IPC sockets.


## Saline vs. Health Check Tool

We want to differentiate conceptually between "Saline" and the "Health Check Tool". In this regard, these are two different components with different purposes.

### Saline: Salt state application monitoring to be integrated into the product

Saline exposes Salt state metrics to Prometheus. It is a tool meant to attach to Salt Master sockets and analyze and extract Salt state/job metrics from a live and running Uyuni server.

Setting up Saline is done is two steps, and should be also driven by `mgradm`:

1. Install the `saline` RPM package on the Uyuni server (already pre-installed in the server image). This provides a "setup" script and new "Formulas with Forms".
2. Run `saline-setup run` to configure and enable the `salined` service that attaches to the Salt Master.
3. In the web UI under "Formulas with Forms", two new formulas will appear: "Saline Prometheus" and "Saline Grafana". These can be used to automatically configure your existing Prometheus and Grafana instances to get the metrics and dashboards from Saline.

Saline already provides an easy way to integrate with the current Monitoring Stack (Formulas with Forms).

The `salined` service must be able to attach to the Salt Master. At the moment this is done by connecting to Salt Master IPC sockets, which means `salined` needs to live in the same system/container as the Salt Master.

Saline should be configurable to use IPC or TCP sockets. Switching the Salt Master to use TCP sockets would enable Saline to run on a different container as the Salt Master.

The Saline engine running on the Uyuni server will provide data and metrics to feed Prometheus and Grafana instances and also a future UI with a live view of running actions. Eventually, this component should be integrated as part of the default Uyuni server stack.

For now, Saline would be part of the Uyuni server image.


### Health Check Tool: An standalone tool you can run on an Uyuni server or use in a disconnected setup (via supportconfig)

This tool is meant not only to provide a picture of the current health status of a live running Uyuni server, where the tool has access to it and can fetch data in real time, but also to help engineers and supporters to analyze and debug problems on disconnected setups, where the tool doesn't have access to an actual running Uyuni server, but only has a "supportconfig" as a source of data.

On disconnected setups, the tool cannot rely on existing Uyuni server components, neither existing Prometheus and Grafana instances, but it should be able to deploy its own instances to visualize the data coming from a "supportconfig".

When the tool has access to an Uyuni server, it can run either "standalone" or via `mgradm`, allowing to reuse existing Prometheus and Grafana instances.

- The Health Check Tool is not installed or running by default on an Uyuni server.
- As multiple components (containers) are deployed, resources on a live Uyuni server might be affected.
- It should be able to reuse existing Prometheus and Grafana instances, allowing integration with an existing Monitoring stack.


# Security considerations
In the current design, we are exposing metrics via Prometheus and making them available in Grafana, and more importantly we are exposing log messages via Loki to CLI and Grafana users. It is important to notice that after running this tool, and until related containers are destroyed, the Grafana Dashboards (and other components like Prometheus and Loki) are exposing metrics and log messages that may contain sensitive data and information to any non-root user on the system or to anyone that have access to this host in the network.

The Promtail pipeline definition can be enhanced to use the [replace](https://grafana.com/docs/loki/latest/send-data/promtail/stages/replace/) stage in order to hide sensitive data from log files. Users must have a configuration file to define the different filters to apply to the Promtail pipeline. Filters must be also configurable via the Monitoring Formula.

TLS must be enabled for Promtail, Prometheus and Loki to ensure a secure transport.

An authentication backend for Prometheus and Loki is usually delegated to an authentication reverse proxy. This must be included in the documentation and probably be considered in the Formula.


# Learning Curve and Documentation

System administrators and developers may need to familiarize themselves with Loki/Promtail's log querying language (LogQL) and Grafana's alerting mechanisms. The learning curve associated with these tools could slow down initial adoption and efficiency gains.

In this sense, we must provide a good documentation with tutorials, use cases and examples to help the users to early and smoothly adopt the new monitoring capabilities.


# Implementation steps

### Phase 0: Disconnected Setup

Available to engineers and supporters. Only access to a supportconfig.

#### Uyuni Health Check

- Create RPM packages in OBS/IBS.
- Use container images building in OBS/IBS for the different components.
- Use alerting rules to detect potential issues.
- Gathers opinions from engineers about possible improvements of metrics, dashboards and alerts.

#### Saline

- Research about using TCP instead of IPC sockets for Salt Master internal sockets.

### Phase 1: Integrated Solution

Integrated with the Monitoring Stack.

#### Uyuni Health Check

- Integration with the Monitoring Stack. Enhance the monitoring formula to enable Health Check monitoring.
- Enhance metrics, dashboards and alerts.
- Allow users to enhance the Promtail pipeline to add filters and/or replace patterns to be able to replace sensitive information.
- Use the alert system to detect potential issues and provide recommendations.

#### Saline

- Build Saline in OBS/IBS and make it part of the Uyuni Server image
- Saline runs inside the `uyuni-server` container.

### Phase 2: Standalone Solution

Decoupled from the Monitoring Stack. Available via an Uyuni Server channel.

#### Uyuni Health Check

- Provide a "standalone" version only (no integration with the Monitoring stack) via an Uyuni server channel (or others so it is available for engineers or supporters).
- Reuse configuration from the "integrated" version.
- Integrate a _one button_ simplified deployment in the Uyuni UI.

#### Saline

- Provide "Saline" inside a separated container that attaches to Salt Master TCP sockets from the `uyuni-server` container.
- Alternatively, explore sharing Salt Master IPC sockets between containers.

# Drawbacks

[drawbacks]: #drawbacks

* Resource Usage: Running additional services for log aggregation, analysis, and enhanced alerting could increase the resource demands on the server, including CPU, memory, and storage. This might necessitate upgrades to existing hardware or reevaluation of resource allocation in cloud environments to ensure optimal performance.

* Security Considerations: With the introduction of new components for logging and alerting, there might be additional security considerations to address, including access controls, data encryption, and secure communication channels between services.

* Alert Noise: Fine-tuning alert rules to balance sensitivity and specificity is critical. Without careful configuration, there's a risk of alert fatigue due to a high volume of non-critical alerts, potentially causing important alerts to be overlooked.


# Alternatives

[alternatives]: #alternatives

### What other designs/options have been considered?

1. Running the Uyuni Health-Check-Tool along with the `uyuni-server` container on the same pod. This could lead to a resource problem on the node running the pod.
2. Integration with the current Monitoring stack. This has been considered in this RFC as an complementary integration for the standalone Health Check Tool.

### What is the impact of not doing this?

1. Not having a Health Check Tool to monitor the health of an Uyuni server. Poor monitoring when it comes to internal metrics, overall Uyuni server health, and particularly around Salt jobs and actions.


# Unresolved questions

[unresolved]: #unresolved-questions

### What are the unknowns?

Has Saline to be part of the current Uyuni Monitoring stack? As mentioned above, it does make sense to integrate Saline in the current Monitoring stack, probably as an "opt-in".

### What can happen if Murphy's law holds true?

- The tool will just not be able to provide insights.
- Security issues.
- The tool might also exhaust resources on the server (computing/memory/disk).
