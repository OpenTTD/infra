# Infrastructure maintenance

(read [infrastructure](./infrastructure.md) first)

OpenTTD's infra is mostly self-healing.
But sometimes things break.
It is software after all, written by a human.
For most part, anyway.

When things break, it is important where to look for a solution.

## Isolating the problem

If one user reports a problem, it is most likely a problem on their end.

If two users report a problem, it is time to look into it.
Almost always, the reports are vague and non-descriptive.

The first question to get an answer to:
is this a service issue, or an infrastructure issue?

## Service issues

If only a single service is not working, like multiplayer, or BaNaNaS in-game (but the website is working), it is most likely something with the service.
Now there are two routes:

- Is it a problem with BaNaNaS? Visit https://nomad-oci.openttd.org/
- Is it a problem with any other service? Visit https://nomad-aws.openttd.org/

You might have guessed it: this is the web-interface to Nomad on OCI/AWS cluod.
You can login via GitHub (it is protected by Cloudflare Zero Trust).
You need to be in the `Core Developers` group to get access.
If you can commit in OpenTTD main repository, you most likely are in that group.

After login, you are presented with Nomad interface.
Welcome.

Be very careful.
You have admin access.

Each backend service has a `-prod` variant and a `-preview` variant.
Click on the service that is acting up, the `-prod` version.
Here you can see the allocations running for that job, and check the logs etc.

If you can't find what is wrong: just restart the service.
Click the "Stop job", click again. Wait. Click "Start job", click again.

The rest should self-heal.

(and in case of the `game-coordinator`: just stop/start the `redis-prod``.
All related services will panic and restart.
From there on, it will self-heal.)

If that didn't fix your problem ... see if you can find anything else wrong.
In the logs, in the CPU usage, etc.

Otherwise it is time to ask TrueBrain, and afterwards ask if he can add this document how to solve it yourself next time.

## Infrastructure issues

If the problem is not isolated to a single service, there are bigger problems.
So time to look at the cluster as a whole.

Still in the Nomad interface, there is a `Client` and `Server` tab, telling you how the cluster is formed.
There should be 5 active nodes.

How Nomad works in detail is an interesting story, but best read in their documentation.
In very short:
you have a Job that defines the OpenTTD backend application.
A Job can run one or more Allocations to instantiate the definition.
Then there are Services that open a port into those Allocations.

In this infrastructure, the `nginx-dc1` has a configuration that is automatically updated when ever a Service is changed.
Check out its definition for details.

Try to follow the routing: the service port defined in this repository should map from nginx to the Service port mentioned in Nomad.
Rarely (it happened once), this wasn't correct.
In that case: stop/start the `nginx-dc1` Job.

Be mindful: this terminates all TURN connections when done on AWS.

There is also a `nginx-public` Job, which routes the TCP connections (except HTTP(S)) to the private part of the Nomad cluster.
Here too, you can check out the routing.

Lastly, there is `cloudflared` which handles the HTTP(S) connections.
It is -very- unlikely this part is broken: Cloudflare did an amazing job writing very stable software.
But it does show a log of what it tried to do with the request.
And often that can give a hint to what is actually wrong.

If this all filas: ask TrueBrain.
And we will update this document afterwards.

## Other issues

If the problem is not in the service, nor in the infrastructure, it is most likely in the cloud provider or the instances themselves.
Here it becomes too complicated to write down in this document how to analyze and solve that.

But in a tldr: those with extra powers have access in 1Password to "Infrastructure", which tells you all the secrets of OpenTTD.
This includes access to the cloud providers, root passwords, etc.

With these, you can login to the cloud provider, go to the instance, make a shell connection, add in the password, and check on the instance itself.
These instances do NOT have SSHd running.
The only way in is via the cloud provider shell access.
