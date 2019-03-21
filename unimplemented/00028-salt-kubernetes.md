- Feature Name: Salt and Kubernetes integration
- Start Date: 2016-11-29

# Unimplemented note

This RFC was not ultimately implemented due to time constraints. It might be revived in future.

# Summary
[summary]: #summary

This RFC proposes a way to leverage Salt as the automation platform for admins using Kubernetes for container orchestration and app deployment.

This RFC walks one step forward in closing the loop with containers in the Salt story: building, creating, deploying and auditing.

![Kubernetes Story](images/k8s.png)

# Motivation
[motivation]: #motivation

If you are using Salt to manage your servers, you already invested in having your states stored somewhere (git, SUSE Manager), your pillar data, integrations, etc.

Kubernetes offers a declarative approach to application deployment that fits very well lot of use-cases.

Now, if you decide to use Kubernetes you will face still two challenges:

1. You need to have containers to run, eg. create Dockerfiles, manage and store them somewhere.
2. You need to create Kubernetes deployment manifests, manage them and store them somewhere.

We already addressed 1. by allowing to [create images with Salt states](https://duncan.codes/2016/07/11/building-docker-images-with-plain-salt.html), integrating this content seamsly into the Salt infrastructure, and allowing eg. integration with pillar data, script and templates that are already managed by Salt.

This RFC addresses the second part. Allowing the admin to manage deployments just as Salt states, and integrate with the rest of the Salt ecosystem.

Additionally, extending the `dockerng.image_present` state to integrate with the upstreamed `dockerng.sls_build` so that one could ask for a image present from states and not only from a `Dockerfile`, would allow for a deployment to "require" a Docker image to be there. providing full automation from git, to container, to deployment, all integrating with pillar data, SUSE Manager formulas, etc.

(a side-motivation is that this is what I expected to find in the Salt k8s module, but I found something completely different).

The idea/design has received positive feedback from:

* Thomas Hatch (SaltStack)
* Flavio Castelli (Containers team)
* Joachim Werner (Product Management)

# Detailed design
[design]: #detailed-design

Kubernetes is a declarative system. You create a description of how your app should look like in term of containers, networking and exposed ports and Kubernetes makes it happen. Interestingly, you do this in yaml format.

If a Kubernetes deployment looks like this (http://kubernetes.io/docs/user-guide/deploying-applications/):

```yaml
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: my-nginx
spec:
  replicas: 2
  template:
    metadata:
      labels:
        run: my-nginx
    spec:
      containers:
      - name: my-nginx
        image: nginx
        ports:
        - containerPort: 80
```

And it is applied like this:

```console
$ kubectl create -f ./run-my-nginx.yaml
deployment "my-nginx" created
```

Why not have the k8s execution module provide: `k8s.create`, `k8s.apply`, etc (all imperative functions), and the `k8s` state module to allow for something like:

```yaml
my-nginx:
  k8s.present:
    spec:
      replicas: 2
      template:
        metadata:
        labels:
          run: my-nginx
        spec:
          containers:
          - name: my-nginx
            image: nginx
            ports:
            - containerPort: 80
```

A `k8s.present` state module would create the deployment if it does not exists, or "apply" the changes (all complexity is handled by kubernetes, the module has just to pass it down).

Salt `state.apply` with `test=True` could translate into kubernetes `--dry-run`, which is kind of ["in-progress"](https://github.com/kubernetes/kubernetes/issues/11488) on the kubernetes side.

# Drawbacks
[drawbacks]: #drawbacks

Why should we *not* do this?

# Alternatives
[alternatives]: #alternatives

What other designs have been considered? What is the impact of not doing this?

# Unresolved questions
[unresolved]: #unresolved-questions

Some details are still not explored.

* which k8s api-server to use
  (could be easily handled with default pillar data, overrides at the state level, etc.)
