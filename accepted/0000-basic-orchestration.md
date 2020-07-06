- Feature Name: initial_salt_orchestration_support
- Start Date: 2020-07-03
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

Implement basic support for Salt Orchestration in Uyuni.

# Motivation
[motivation]: #motivation

The initial use case if for improving clustering support. Use cases requiring orchestration:
- Use temporary SSH keys on CaaSP cluster nodes: a SSH key must be generated, authorized on all the nodes on the cluster, then `skuba` is invoked to execute a cluster operation requiring the use of the temporary SSH key, then finally the key is removed from the nodes.
- Setup a new CaaSP cluster from on a group of machines managed by Uyuni. Some of the steps involved are: setting up a load balancer (optional), authorizing a SSH key on the target machines, changing the `sudoers` file, loading the SSH key in the `ssh-agent`, running `skuba init` and `skuba node bootstrap` on the management node, add any nodes to the cluster by running `skuba node join`.
- Protected sensitive cluster packages using locks. E.g. if locks are used to protected the CaaSP packages from accidental upgrade or remove ( from Uyuni, Salt or command line), the locks have to be removed before doing upgrade and then reinstated after the upgrade operation.

In the initial version, the scope of the orchestration support will be limited to clustering. In later iterations it can be expanded to support other uses cases.

# Detailed design
[design]: #detailed-design

The `salt-netapi` library already support calling Salt runner. 

The Uyuni actions must be enhanced to make Salt runner calls besides minions calls.

## Action enhancements.

A runner action won't need a collection of `ServerAction` objects because the action is not executed on a set of minions directly.

Salt supports asynchronous runner calls but it doesn't allow attaching metadata like `action-id`. Therefore the `jid` returned by Salt must be stored in the database in order to match the return event to the originating action. 

### Database and Hibernate changes

In order to store the `jid` and the executions outcome a new table is needed:

```sql
CREATE TABLE IF NOT EXISTS rhnActionSaltRunnerJob (

    action_id       NUMERIC NOT NULL
                            CONSTRAINT rhn_actsaltrunjob_aid_fk
                            REFERENCES rhnAction (id)
                            ON DELETE CASCADE,
    jid              VARCHAR(100) NOT NULL,
    status           NUMERIC NOT NULL
                         CONSTRAINT rhn_server_action_status_fk
                             REFERENCES rhnActionStatus (id),
    result_code      NUMERIC,
    result_msg       TEXT,
    pickup_time      TIMESTAMPTZ,
    completion_time  TIMESTAMPTZ,
    created         TIMESTAMPTZ
                        DEFAULT (current_timestamp) NOT NULL,
    primary key (action_id, jid)
);

```

A new collection will be added to the cluster actions (`ClusterJoinNodeAction`, `ClusterRemoveNodeAction`, etc):

```java
class ClusterJoinNodeAction {
  [...]
  private Set<ActionSaltRunnerJob> runnerJobs = new HashSet<>();
  [...]
}
```

The Hibernate mappings will need to be adapted:

```xml
<subclass name="com.redhat.rhn.domain.action.cluster.ClusterJoinNodeAction"
        lazy="true" discriminator-value="516">
    [...]
    <set name="runnerJobs" outer-join="false" cascade="all" lazy="true"
          inverse="true">
        <key column="action_id"/>
        <one-to-many
                class="com.redhat.rhn.domain.action.ActionSaltRunnerJob" />
    </set>
    <join table="rhnActionClusterJoinNode">
      [...]
    </join>
</subclass>

```

### Action result display

Actions executed on a system are shown in the Events tab of the system details. A similar approach should be used for orchestration results. They should be displayed in the details of the target entity or in a generic orchestration UI.

In the case of clusters, the UI should be enhanced to show a view similar to the system Events tab.

In later versions, if more complex orchestration will be implemented that doesn't target a particular entity like clusters, a generic UI should be implemented to show orchestration results.

### Cluster actions

The existing actions targeting clusters will be changed to use orchestration where it makes sense:
- `ClusterJoinNodeAction`
- `ClusterRemoveNodeAction`
- `ClusterUpgradeNodeAction`
- `ClusterGroupRefreshNodesAction`


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

- What are the unknowns?
- What can happen if Murphy's law holds true?
