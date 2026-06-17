- Feature Name: mqtt_event_publisher
- Start Date: 2026-06-11

# Summary
[summary]: #summary

Add an MQTT event publisher to the Uyuni reactor pipeline. When certain
Salt events come in (system registered, job finished, state applied, etc.),
we publish a JSON message to a local Mosquitto broker so that external
tools — Node-RED, Grafana, custom scripts — can subscribe and react
without polling the API.

The first version covers five event types: system registration, job
completion, state application, image deployment, and batch operations.

# Motivation
[motivation]: #motivation

Right now Uyuni keeps all Salt events inside the Java server. If an
external tool wants to know when a minion registers or a highstate fails,
the only option is polling the XML-RPC / HTTP API. That adds latency
and puts extra load on the server for no good reason.

MQTT is a lightweight publish/subscribe protocol that is already widely
adopted in infrastructure automation and IoT. Mosquitto, the reference
broker implementation, is packaged and available on openSUSE and SLES.
Publishing reactor events to MQTT gives us:

- Admins can see registration, job, and state events as they happen,
  no polling needed.
- Node-RED or similar tools can subscribe and trigger workflows
  (post to Slack on a failed highstate, open a ticket on new registration).
- Consumers subscribe to the broker, not to Uyuni directly. Adding or
  removing a consumer does not touch the server at all.
- Event streams can feed into Prometheus Alertmanager, Grafana, or
  anything that speaks MQTT.

### Current State vs. Proposed State

```mermaid
graph LR
    subgraph "Current: No External Access"
        SE1[Salt Event] --> SR1[SaltReactor]
        SR1 --> MQ1[MessageQueue]
        MQ1 --> HA1[Internal Handlers]
        HA1 -. "no external visibility" .-> X1["❌ External Tools"]
    end
```

```mermaid
graph LR
    subgraph "Proposed: MQTT Pub/Sub"
        SE2[Salt Event] --> SR2[SaltReactor]
        SR2 --> MQ2[MessageQueue]
        MQ2 --> HA2[Internal Handlers]
        MQ2 --> MA2[MqttEventAction]
        MA2 --> MB2[Mosquitto Broker]
        MB2 --> NR2["✅ Node-RED"]
        MB2 --> GR2["✅ Grafana"]
        MB2 --> CS2["✅ Custom Scripts"]
    end
```

## Why MQTT?

- MQTT is an OASIS standard with broad tooling support.
- Mosquitto is lightweight (< 1 MB RSS), runs as a single process,
  and is already available in openSUSE and SLES package repositories.
- The publish/subscribe model is a natural fit: Uyuni publishes events
  and any number of consumers can subscribe without coupling.
- QoS levels (0, 1, 2) allow consumers to choose their delivery
  guarantee. QoS 1 ("at least once") provides a good balance between
  reliability and performance for operational events.
- Eclipse Paho, the reference Java MQTT client, is mature, small, and
  has no transitive dependencies beyond the JDK.

## Why Not WebSockets, Server-Sent Events, or a REST Callback?

- **WebSockets / SSE** require the consumer to maintain a persistent
  HTTP connection to the Uyuni server itself, coupling availability
  and adding load. MQTT decouples the broker from the application.
- **REST callbacks (webhooks)** require consumers to expose an HTTP
  endpoint that Uyuni pushes to. This inverts the dependency: Uyuni
  must know about every consumer, handle retries, and manage
  authentication. With MQTT, consumers subscribe independently.

# Detailed design
[design]: #detailed-design

## Architecture Overview

![MQTT Event Publisher Architecture](images/mqtt-architecture.png)

![Event Type Mapping](images/mqtt-event-types.png)

```mermaid
flowchart TB
    subgraph uyuni["Uyuni Server (JVM)"]
        salt["Salt Event Stream"] --> reactor["SaltReactor"]
        reactor --> mq["MessageQueue"]
        mq --> existing["Existing Handlers<br/>(RegisterMinionAction, etc.)"]
        mq --> mqtt_action["MqttEventAction<br/><i>NEW - implements MessageAction</i>"]
        mqtt_action --> publisher["MqttPublisherService<br/><i>NEW - wraps MqttAsyncClient</i>"]
    end

    publisher -- "QoS 1 publish" --> broker["Mosquitto Broker<br/>tcp://mosquitto:1883"]

    subgraph consumers["External Consumers"]
        broker --> nodered["Node-RED<br/><i>Visual automation</i>"]
        broker --> cli["mosquitto_sub<br/><i>CLI debugging</i>"]
        broker --> grafana["Grafana / Alerting<br/><i>Dashboards</i>"]
        broker --> custom["Custom Scripts<br/><i>Python, Go, etc.</i>"]
    end

    style uyuni fill:#1a1a2e,stroke:#e94560,color:#fff
    style consumers fill:#0f3460,stroke:#16213e,color:#fff
    style broker fill:#e94560,stroke:#fff,color:#fff
    style mqtt_action fill:#533483,stroke:#fff,color:#fff
    style publisher fill:#533483,stroke:#fff,color:#fff
```

The design introduces two new classes in a new `com.suse.manager.reactor.mqtt`
package and a small registration block in the existing `SaltReactor`.

## Event Flow Sequence

```mermaid
sequenceDiagram
    participant Salt as Salt Master
    participant SR as SaltReactor
    participant MQ as MessageQueue
    participant EA as MqttEventAction
    participant PS as MqttPublisherService
    participant Broker as Mosquitto
    participant Sub as Subscriber

    Salt->>SR: Salt event (e.g. minion/register)
    SR->>MQ: dispatch(RegisterMinionEventMessage)

    par Existing handlers
        MQ->>MQ: RegisterMinionEventMessageAction.execute()
    and MQTT publisher (new)
        MQ->>EA: execute(RegisterMinionEventMessage)
        EA->>EA: instanceof check → handleRegisterMinion()
        EA->>EA: Extract minionId, machineId, etc.
        EA->>PS: publish("uyuni/events/systems/registered", data)
        PS->>PS: Wrap in envelope (eventId, timestamp)
        PS->>PS: Serialize to JSON
        PS-->>Broker: PUBLISH (QoS 1, async)
        Broker-->>PS: PUBACK
        Broker->>Sub: Forward message
    end
```

## Class Diagram

```mermaid
classDiagram
    class MessageAction {
        <<interface>>
        +execute(EventMessage msg)
        +canRunConcurrently() boolean
    }

    class MqttEventAction {
        -MqttPublisherService mqttPublisherService
        +execute(EventMessage msg)
        +canRunConcurrently() boolean
        -handleRegisterMinion(RegisterMinionEventMessage)
        -handleJobReturn(JobReturnEventMessage)
        -handleApplyStates(ApplyStatesEventMessage)
        -handleImageDeployed(ImageDeployedEventMessage)
        -handleBatchStarted(BatchStartedEventMessage)
    }

    class MqttPublisherService {
        -String brokerUrl
        -String clientId
        -Gson gson
        -ExecutorService executorService
        -MqttAsyncClient client
        +MqttPublisherService()
        +MqttPublisherService(String brokerUrl)
        +publish(String topic, Object payload)
        +shutdown()
        -connectAsync()
    }

    class SaltReactor {
        -MqttPublisherService mqttPublisherService
        +start()
        +stop()
    }

    MessageAction <|.. MqttEventAction : implements
    MqttEventAction --> MqttPublisherService : uses
    SaltReactor --> MqttPublisherService : owns lifecycle
    SaltReactor --> MqttEventAction : creates and registers
```

## New Dependency

The Eclipse Paho MQTT v3 client library is added as a Maven dependency:

- **Group:** `org.eclipse.paho`
- **Artifact:** `org.eclipse.paho.client.mqttv3`
- **Version:** `1.2.5`

The version is declared in the parent `java/pom.xml` BOM and consumed
without version in `java/core/pom.xml`, following the existing convention.

MQTT is chosen because the Mosquitto broker shipped with openSUSE and SLES
is lightweight and the feature does not require complex capabilities.

## MqttPublisherService

`MqttPublisherService` handles all communication with the MQTT broker.

**Responsibilities:**

- Establish and maintain an asynchronous connection to the MQTT broker
  using `MqttAsyncClient`.
- Serialize event payloads to JSON using Gson.
- Wrap each payload in a standard envelope containing `eventId`,
  `timestamp`, `topic`, and `data`.
- Publish messages at QoS 1 (at least once delivery).
- Handle reconnection automatically via the Paho `automaticReconnect`
  option.
- Provide a clean `shutdown()` method for graceful teardown.

**Key design decisions:**

1. **Asynchronous client.** The reactor sits on a hot path — we cannot
   block it waiting for a broker ACK. `MqttAsyncClient` returns right
   away and deals with delivery in the background.

2. **Single-thread executor.** All publish operations are submitted to a
   single-thread executor. This guarantees message ordering and avoids
   contention on the Paho client. The thread is created as a daemon
   thread so it does not prevent JVM shutdown.

3. **Configurable broker URL.** The default broker URL is
   `tcp://mosquitto:1883`, matching the container name in the Uyuni
   containerized deployment. It can be overridden via the JVM system
   property `uyuni.mqtt.broker.url`.

4. **Broker down? Keep going.** If the broker is not reachable at startup
   or drops mid-run, we log a warning and skip publishing. The reactor
   keeps working as usual. Once the broker is back, Paho reconnects on
   its own and events start flowing again.

5. **Envelope pattern.** Every published message includes a UUID
   `eventId` for deduplication (relevant at QoS 1, which may redeliver)
   and an ISO-8601 `timestamp` indicating when the event was published.

### Connection Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Disconnected: SaltReactor.start()
    Disconnected --> Connecting: connectAsync()
    Connecting --> Connected: CONNACK received
    Connecting --> Disconnected: Connection failed (retry)
    Connected --> Publishing: publish() called
    Publishing --> Connected: PUBACK received
    Connected --> Disconnected: Broker goes down
    Disconnected --> Connecting: automaticReconnect
    Connected --> [*]: SaltReactor.stop()
```

## MqttEventAction

`MqttEventAction` implements the existing `MessageAction` interface.
It maps each internal event message to the right MQTT topic and
builds the JSON payload to publish.

**Supported event types and topics:**

| Internal Event Class            | MQTT Topic                        | Trigger                    |
|---------------------------------|-----------------------------------|----------------------------|
| `RegisterMinionEventMessage`    | `uyuni/events/systems/registered` | New minion bootstrapped    |
| `JobReturnEventMessage`         | `uyuni/events/jobs/returned`      | Salt job completed         |
| `ApplyStatesEventMessage`       | `uyuni/events/states/applied`     | Highstate / state.apply    |
| `ImageDeployedEventMessage`     | `uyuni/events/images/deployed`    | OS image deployed          |
| `BatchStartedEventMessage`      | `uyuni/events/batches/started`    | Batch operation started    |

**Payload extraction:** Each handler picks out only the fields that
make sense for external consumers. For example, `handleRegisterMinion`
publishes `minionId`, `machineId`, `saltbootInitrd`, and
`managementKey` — we do not dump the entire event message object.

**Concurrency:** `canRunConcurrently()` returns `true` because the
action delegates all work to the publisher service's executor thread.
There is no shared mutable state in the action itself.

**Error handling:** All exceptions thrown during event processing are
caught and logged. A failure to publish one event does not affect the
processing of subsequent events and does not impact other registered
`MessageAction` handlers.

### Event Routing Logic

```mermaid
flowchart TD
    msg["EventMessage received"] --> null_check{"msg == null?"}
    null_check -- Yes --> discard["Return (no-op)"]
    null_check -- No --> reg{"instanceof<br/>RegisterMinionEventMessage?"}
    reg -- Yes --> handle_reg["Extract: minionId, machineId,<br/>saltbootInitrd, managementKey<br/>→ uyuni/events/systems/registered"]
    reg -- No --> job{"instanceof<br/>JobReturnEventMessage?"}
    job -- Yes --> handle_job["Extract: minionId, jid,<br/>fun, success, retcode<br/>→ uyuni/events/jobs/returned"]
    job -- No --> apply{"instanceof<br/>ApplyStatesEventMessage?"}
    apply -- Yes --> handle_apply["Extract: serverId, userId,<br/>stateNames, forcePackageListRefresh<br/>→ uyuni/events/states/applied"]
    apply -- No --> image{"instanceof<br/>ImageDeployedEventMessage?"}
    image -- Yes --> handle_image["Extract: machineId, grains<br/>→ uyuni/events/images/deployed"]
    image -- No --> batch{"instanceof<br/>BatchStartedEventMessage?"}
    batch -- Yes --> handle_batch["Extract: jid, availableMinions,<br/>downMinions, timestamp<br/>→ uyuni/events/batches/started"]
    batch -- No --> log_debug["LOG.debug: Unhandled event type"]

    handle_reg --> publish["MqttPublisherService.publish()"]
    handle_job --> publish
    handle_apply --> publish
    handle_image --> publish
    handle_batch --> publish
```

## SaltReactor Integration

The `SaltReactor.start()` method is extended to:

1. Instantiate `MqttPublisherService`.
2. Create an `MqttEventAction` with a reference to the publisher.
3. Register the action for each of the five event classes using
   `MessageQueue.registerAction()`.

The `SaltReactor.stop()` method calls `mqttPublisherService.shutdown()`
to close the broker connection and shut down the executor thread.

This is the same pattern every other handler in `SaltReactor` uses.
The MQTT action runs alongside the existing handlers — nothing
changes for current event processing.

## Topic Hierarchy

```mermaid
graph TD
    root["uyuni/"] --> events["events/"]
    events --> systems["systems/"]
    events --> jobs["jobs/"]
    events --> states["states/"]
    events --> images["images/"]
    events --> batches["batches/"]
    systems --> registered["registered"]
    jobs --> returned["returned"]
    states --> applied["applied"]
    images --> deployed["deployed"]
    batches --> started["started"]

    style root fill:#e94560,stroke:#fff,color:#fff
    style events fill:#533483,stroke:#fff,color:#fff
    style systems fill:#0f3460,stroke:#fff,color:#fff
    style jobs fill:#0f3460,stroke:#fff,color:#fff
    style states fill:#0f3460,stroke:#fff,color:#fff
    style images fill:#0f3460,stroke:#fff,color:#fff
    style batches fill:#0f3460,stroke:#fff,color:#fff
```

This hierarchy allows consumers to subscribe at different granularity
levels using MQTT wildcards:

- `uyuni/events/#` — all events
- `uyuni/events/systems/#` — only system lifecycle events
- `uyuni/events/jobs/#` — only job events

## Message Envelope Format

Every message published to the broker has a consistent JSON envelope:

```json
{
  "eventId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2026-06-11T10:30:00.000Z",
  "topic": "uyuni/events/systems/registered",
  "data": {
    "minionId": "web-server-01.example.com",
    "machineId": "550e8400-e29b-41d4-a716-446655440000",
    "saltbootInitrd": false,
    "managementKey": "1-default"
  }
}
```

### Payload Fields per Event Type

**`uyuni/events/systems/registered`**

| Field            | Type    | Description                                  |
|------------------|---------|----------------------------------------------|
| `minionId`       | String  | Salt minion ID                               |
| `machineId`      | String  | Hardware machine ID (from grains, if present) |
| `saltbootInitrd` | Boolean | Whether this is a Saltboot PXE registration   |
| `managementKey`  | String  | Activation key used (if any)                  |

**`uyuni/events/jobs/returned`**

| Field       | Type    | Description                      |
|-------------|---------|----------------------------------|
| `minionId`  | String  | Minion that ran the job          |
| `jid`       | String  | Salt job ID                      |
| `fun`       | String  | Salt function executed           |
| `success`   | Boolean | Whether the job succeeded        |
| `retcode`   | Integer | Return code                      |
| `timestamp` | String  | When the job completed           |

**`uyuni/events/states/applied`**

| Field                     | Type     | Description                        |
|---------------------------|----------|------------------------------------|
| `serverId`                | Long     | Uyuni server ID of the target      |
| `userId`                  | Long     | User who triggered the apply       |
| `stateNames`              | String[] | Names of states applied            |
| `forcePackageListRefresh` | Boolean  | Whether package list refresh forced |
| `directCall`              | Boolean  | Whether this was a direct call      |

**`uyuni/events/images/deployed`**

| Field       | Type   | Description                        |
|-------------|--------|------------------------------------|
| `machineId` | String | Target machine ID                  |
| `grains`    | Object | Salt grains from the deployed host |

**`uyuni/events/batches/started`**

| Field              | Type     | Description                    |
|--------------------|----------|--------------------------------|
| `jid`              | String   | Batch job ID                   |
| `availableMinions` | String[] | Minions available for the batch |
| `downMinions`      | String[] | Minions reported as down       |
| `timestamp`        | String   | When the batch started         |

## Configuration

| Property                    | Default                  | Description                  |
|-----------------------------|--------------------------|------------------------------|
| `uyuni.mqtt.broker.url`     | `tcp://mosquitto:1883`   | MQTT broker connection URL   |

The property is read via `System.getProperty()` and can be set in the
Tomcat startup configuration or via JVM arguments.

## Failure Modes

```mermaid
flowchart LR
    subgraph "Failure Scenario"
        A["Broker down<br/>at startup"] --> B["Events skipped<br/>(logged at WARN)"]
        B --> C["Paho auto-reconnects<br/>when broker returns"]
        C --> D["Events resume<br/>normally"]
    end

    subgraph "Reactor Impact"
        E["Exception in<br/>MqttEventAction"] --> F["Caught and logged"]
        F --> G["Other handlers<br/>unaffected"]
        G --> H["Reactor pipeline<br/>continues"]
    end
```

| Scenario                     | Behavior                                        |
|------------------------------|-------------------------------------------------|
| Broker not running at start  | Logged as error. Reactor starts normally.        |
| Broker goes down at runtime  | Events skipped with warning. Auto-reconnect.     |
| Broker comes back up         | Paho reconnects automatically. Events resume.    |
| Malformed event data         | Caught, logged. Other events unaffected.         |
| Paho library throws          | Caught, logged. Reactor pipeline unaffected.     |

## Files Changed

```mermaid
graph LR
    subgraph "Modified (existing files)"
        pom_parent["java/pom.xml<br/><i>+5 lines: Paho BOM entry</i>"]
        pom_core["java/core/pom.xml<br/><i>+4 lines: Paho dependency</i>"]
        reactor["SaltReactor.java<br/><i>+20 lines: init, register, shutdown</i>"]
    end

    subgraph "New files"
        publisher["MqttPublisherService.java<br/><i>186 lines</i>"]
        action["MqttEventAction.java<br/><i>169 lines</i>"]
        test["MqttEventActionTest.java<br/><i>117 lines</i>"]
    end

    style pom_parent fill:#0f3460,stroke:#fff,color:#fff
    style pom_core fill:#0f3460,stroke:#fff,color:#fff
    style reactor fill:#0f3460,stroke:#fff,color:#fff
    style publisher fill:#533483,stroke:#fff,color:#fff
    style action fill:#533483,stroke:#fff,color:#fff
    style test fill:#533483,stroke:#fff,color:#fff
```

## Testing

Unit tests for `MqttEventAction` use a test spy subclass of
`MqttPublisherService` that captures the topic and payload instead of
connecting to a real broker. This verifies:

- Correct topic mapping for each event type.
- Correct payload field extraction.
- Null safety and error handling.

Integration testing against a running Mosquitto instance can be done
with `mosquitto_sub` or by connecting a Node-RED flow to the broker.

# Drawbacks
[drawbacks]: #drawbacks

- Adds a new external dependency (Eclipse Paho). However, Paho is a
  small library (< 300 KB) with no transitive dependencies.
- Requires a Mosquitto broker to be deployed alongside Uyuni. In the
  containerized deployment this is straightforward (sidecar container).
  On traditional installations it requires installing and enabling the
  `mosquitto` package.
- Events published before the broker connects are dropped (not buffered
  indefinitely). This is a deliberate choice to avoid unbounded memory
  usage, but means the first few seconds after startup may have gaps.

# Alternatives
[alternatives]: #alternatives

- **Salt's own event bus** — Salt already has a ZeroMQ-based event bus,
  but it requires a Salt API listener, uses a different wire format,
  and is not accessible to tools that do not speak the Salt protocol.
- **WebSocket endpoint in Uyuni** — Would couple consumers to the Uyuni
  web application lifecycle. A broker provides better decoupling.
- **Database triggers + polling** — Higher latency, more complexity,
  and adds load to the database.
- **Apache Kafka** — Much heavier infrastructure requirement. MQTT is
  sufficient for the expected event throughput and is simpler to deploy.

# Unresolved questions
[unresolved]: #unresolved-questions

- Should the set of published event types be configurable (e.g. via a
  system property or database setting), or is the hardcoded set of five
  sufficient for the initial release?
- Should the publisher buffer a bounded number of events when the broker
  is temporarily unavailable, or is the current skip-and-log behavior
  acceptable?
- Should the MQTT topic prefix (`uyuni/events/`) be configurable to
  support multi-server environments where each Uyuni instance publishes
  to a shared broker?
- Authentication and TLS: should the first version support
  username/password or TLS client certificates for broker connections,
  or is unauthenticated localhost-only access sufficient initially?
