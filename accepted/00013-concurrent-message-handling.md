* Feature Name: Concurrent Message Handling
* Start Date: 2016-05-02

---
* Johannes Renner <jrenner@suse.com>

# Summary
[summary]: #summary

The message queue implementation that is used in the Salt reactor part of SUSE Manager should not block on long running operations. Instead those should be processed in the background using a pool of threads to unblock the message queue dispatcher thread.

# Motivation
[motivation]: #motivation

The *Salt reactor* is a central part of SUSE Manager nowadays: a component that is listening for events on the Salt event bus, filtering out the interesting ones and triggers reactions accordingly. In order to not block on the parsing of incoming events, a message queue is used to trigger reactions on incoming events to happen asynchronously.

The message queue that is currently used is a rather simple custom implementation (done by upstream Spacewalk) where only a single thread is used for dispatching all messages, one after another. Therefore whenever message processing involves time consuming computations or communications, the message queue is blocked and no message will be processed until that computation or communication is done! This should be fixed in a way that the message queue main dispatcher thread will not be blocked in case a long running task is triggered by a message.

# Detailed design
[design]: #detailed-design

The proposed solution is based on patching the existing implementation in order to add in support for running message handlers in parallel using a thread pool of configurable size. A flag is therefore introduced on the `MessageAction` interface (all message handlers implement this) to signalize if a specific handler is able to run concurrently or not. Whenever the dispatcher receives a message handler that *can* be run concurrently, it would submit it into a thread pool (using `ExecutorService`) instead of executing its `run()` method directly in the dispatcher thread. This way it is possible that even during a long running task (e.g. inserting a list of packages as received from a minion into the database) the message queue can process incoming messages without being blocked: long running tasks will simply be submitted into the thread pool while the queue itself can continue to process more incoming messages.

The number of threads in the used pool should be configurable for users (via the `rhn.conf` file, default value chosen for the prototype is 5), so that customers can adjust this value due to their capacities and needs. In case all threads are busy, additionally submitted tasks will be queued by the `ExecutorService` (`Executors.newFixedThreadPool(NO_OF_THREADS)` is used).

It is not trivial to figure out for a certain message handler class if it actually can run concurrently or not. The patch in the pull request initially enables only two types of message handlers to run in parallel, that is `JobReturnEventMessageAction` and `CheckinEventMessageAction`. Job return events come in very frequently and often concurrently from different minions, processing generally takes a rather long time, e.g. inserting a minion's list of packages into the database (~ 10 sec.) or similar. Checkin events further happen after every job return event and are responsible for updating the checkin date of respective minions.

Please see [the proposed patch] (https://github.com/SUSE/spacewalk/pull/638).

# Drawbacks
[drawbacks]: #drawbacks

Why should we *not* do this? There is no reason to not do this. Blocking the message queue on every long running task is not an option, so we need to improve the situation. The proposed patch is small and easy to understand and review.

# Alternatives
[alternatives]: #alternatives

## Replace the message queue with a reactive library

We could go away from the custom message queue implementation completely while using a third party *reactive* library for java that supports asynchronous event-driven programming, like e.g. [akka] (http://akka.io/), [reactiveX] (http://reactivex.io/) or [jumi actors] (http://jumi.fi/actors.html). This is a valid option, but it does not solve the problem by itself, we would still need to design our messages and handlers with the concurrency topic in mind.

Some of these *frameworks* further seem to be overkill for the problem and a bit overengineered while they also tend to require a lot of additional dependencies, like the complete scala runtime in case of akka. Apart from that the patch to do a complete rewrite would be much bigger than the patch proposed in the [pull request] (https://github.com/SUSE/spacewalk/pull/638) and eventually this would come with an increased risk of regressions, since actually **all** the Salt based backend operations would need to be ported.

## Use Taskomatic for long running stuff

Taskomatic does not offer a good solution for the described problem. It was designed to run jobs in regular intervals defined by a `cron`-like schedule. Every job definition consists of various classes and DB tables that need to be populated, multithreaded jobs are a hack on top of that and single runs are barely supported. Whenever a single job run is scheduled via taskomatic this would actually define all the infrastructure for a repeating run and it will on top of that never be cleaned up. If that sounds a lot like the `schedule` module in Salt then maybe there actually is similarity! Further every run is again persisted in the database which is also somethind we do not need or want in this case.

# Unresolved questions
[unresolved]: #unresolved-questions

- Q: Does it help to improve the performance in large installations (many clients), where are the numbers?
- A: It still needs to be tested which is not trivial. It would be nice if we could repeat scalability tests with e.g. 1000 servers.
