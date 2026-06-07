# Infrastructure

## Cloud providers

OpenTTD runs in two clouds:
- AWS
- Oracle Cloud (OCI)

The reason is that OCI is vastly cheaper, and the idea was to migrate all from OCI to AWS, but that process never finished.
All the code in this repository is prepared for it; but it also needs careful doing.

Both clouds are set-up in a very similar way, and are created under the concept of self-healing.
This means that many problems tend to resolve itself after a bit of time (give or take an hour); but if that fails, a simple reboot (either of the node or the service) fixes the issue.

Additionally, the full infrastructure, everything, is defined in this repository.
There are no secrets or hidden paths: everything is in this repository.

This repository uses Pulumi, which is a wrapper around Terraform, which helps defining your infrastructure as code.
This make the language between AWS and OCI the same, and as readable as one can how things look.

## Instances

On both clouds, OpenTTD runs on "instance groups".
This is a definition in cloud providers where you say: I want 3 instances of this configuration running, and 2 instances of this configuration.
What ever happens, the cloud provider will really REALLY try to make that come true.

This means that if a node dies, a new node is created with the exact same configuration.
And also if you kill a node.
Self-healing.

There are two types of ndoes:
- `nomad`: this runs on a private segment in the cloud provider, and runs all OpenTTD's backend services.
- `nomad-public`: this runs on a public segment in the cloud provider, and bridges all TCP connectivity (except HTTP(S)) to/from `nomad`.
  Additionally, it runs `dibridge`, as that needs special access to an IPv6 range.

This private/public split is the most common thing in the world when working with cloud providers, and it is exactly what you expect.

The instances are all provided with a `cloud-init`, which executes a bunch of scripts (including the installation of all software) on first start.
It is designed to "just work".

See `aws-core` and `oci-core` for details.

## Nomad

To run all the services, OpenTTD uses hashicorp's Nomad.
Nomad is an orchestrator, similar to Kubernetes.
It is just vastly simpler to understand and maintain.

All `nomad` nodes run Nomad as client+server, and all `nomad-public` run Nomad as client.
The configuration provisioned by `cloud-init` makes sure they use the cloud provider to find the cluster via the instance group, making sure that on startup all nodes create a single cluster.

See `nomad-core` for details.

## Cloudflare

As described earlier, `nomad-public` is responsible for routing all TCP connectivity to the right place, with the exception of HTTP(S).
All HTTP(S) traffic is routed via Cloudflare.

The traffic-flow is something like this:
- Cloudflare accepts the HTTP request.
- Cloudflare routes it to Cloudflare Tunnel.
  A Tunnel runs on one end in the Cloudflare network, and on the other hand on all `nomad` nodes.
- Cloudflare Tunnel arrives on the `nomad` nodes, and routes it to `nginx-dc1` service.
- This nginx is configured to dynamically know where services are hosted, and it is finally routes to the actual instance of the service.

See `cloudflare-core` for details.

## Applications

Under `app` folder are all the applications OpenTTD runs in the backend.
They are all very different, but they should be self-explaining when looking into the code.
Additionally, the [README](https://github.com/OpenTTD/infra/blob/main/README.md#subfolders) shows a list of applications and what they are for.
