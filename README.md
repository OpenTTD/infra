# OpenTTD's infrastructure

In this repository are several [Pulumi](https://pulumi.com/) projects that combined declare all of OpenTTD's infrastructure as code.

## Prerequisite

- Pulumi CLI installed
- Nomad CLI installed
- An AWS profile named `openttd` with valid credentials.
- The following environment variables set:
  - `export CLOUDFLARE_API_TOKEN=` with a valid Cloudflare API token.
  - `export GITHUB_TOKEN=` with a valid GitHub API token.
  - `export SENTRY_TOKEN=` with a valid Sentry API token.
  - `export NOMAD_ADDR=http://127.0.0.1:4646`
  - `export AWS_PROFILE=openttd`
  - `export AWS_REGION=eu-west-1`

## Usage

### Core infrastructure

```bash
python3 -m venv .env
.env/bin/pip install -r requirements.txt
( cd pulumi-openttd && pip install -e . )

( cd global-config && ../.env/bin/pulumi up )
( cd aws-core && ../.env/bin/pulumi up )
( cd cloudflare-core && ../.env/bin/pulumi up )
# Read "Bootstrapping" chapter if this is the first time.
( cd nomad-core && ../.env/bin/pulumi up )

cd app
# Deploy all applications in this folder similar to above.
```

### Proxy

```bash
cd cloudflare-core
export CF_ACCESS_CLIENT_ID=$(../.env/bin/pulumi stack output service_token_id --show-secrets)
export CF_ACCESS_CLIENT_SECRET=$(../.env/bin/pulumi stack output service_token_secret --show-secrets)
cd ..
.env/bin/python nomad-proxy nomad-aws.openttd.org 4646
```

Now you should be able to execute `nomad node status` and get a valid response.

## Subfolders

### Core (Pulumi)

- [aws-core](./aws-core): contains the core infrastructure for AWS.
- [cloudflare-core](./cloudflare-core): contains the core infrastructure for Cloudflare.
- [global-config](./global-config): contains configuration used by multiple other projects.
- [nomad-core](./nomad-core): contains the core infrastructure for Nomad.

### Applications (Pulumi)

- [bananas](./app/bananas): OpenTTD's BaNaNaS (CDN + server + api + web)
- [binaries](./app/binaries): OpenTTD's old binaries domain
- [cdn](./app/cdn): OpenTTD's CDN (for releases)
- [dibridge](./app/dibridge): OpenTTD's IRC <-> Discord bridge
- [docs](./app/docs): OpenTTD's docs
- [dorpsgek](./app/dorpsgek): OpenTTD's DorpsGek (Discord / IRC bot to inform about GitHub activity)
- [eints](./app/eints): OpenTTD's translator tool
- [preview](./app/preview): OpenTTD's previews
- [redirect](./app/redirect): OpenTTD's redirect domains
- [survey-web](./app/survey-web): OpenTTD's Survey website
- [symbols](./app/symbols): OpenTTD's Symbol Server
- [website](./app/website): OpenTTD's website
- [wiki](./app/wiki): OpenTTD's wiki

### Others

- [pulumi-openttd](./pulumi-openttd): common bits and pieces for Pulumi used by multiple projects.
- [nomad-proxy](./nomad-proxy): as Nomad runs behind Cloudflare Access, it needs extra credentials before Nomad CLI works.
  This proxy adds those credentials for the Nomad CLI.
  See the nomad-proxy's [README](./nomad-proxy/README.md) for more information.

## Bootstrapping

Make sure you deployed `aws-core` and `cloudflare-core` first.

When this is deployed for the first time, [Nomad](https://www.hashicorp.com/products/nomad) is installed on AWS, scaled up to one instance, which keeps failing health-checks.

To solve this, some manual labor is required.
This will take about 30 minutes to complete in total, and should only be done when there isn't anything to start with.

First, some changes on Cloudflare:
- Login to Cloudflare.
- Navigate to Cloudflare Access (via Zero Trust), find the Tunnel.
- Change the public hostnames for `nomad.openttd.org` to point to port 4646.
  This connection is not very stable, but sufficiently to bootstrap the process.

Next, we need to get the cluster online:
- Run `pulumi stack output tunnel_token --show-secrets` in the `cloudflare-core` project and remember the output.
- Login to AWS.
- Go to the ASG and find `nomad-asg`.
- Delete the Lifecycle Hooks under `Instance management`
- Set the `desired` to 3 under `Details`.
- This will spin up a total of three EC2 instances, that form a single Nomad cluster.
  It needs to be three, as that is how the cluster if configured; before it sees three instances, it will not form a functional cluster.
- Find one of the Nomad EC2 instances.
- Open an EC2 Serial Console.
- Login with `ec2-user` and the password as given via `console_password` config.
- Run the following commands:

```bash
curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/nomad-core/files/cloudflared.nomad -o /tmp/cloudflared.nomad
nomad var put nomad/jobs/cloudflared tunnel_token=<tunnel token>
nomad job run /tmp/cloudflared.nomad

nomad operator scheduler set-config -memory-oversubscription=true
nomad operator scheduler set-config -scheduler-algorithm=spread
```

- Wait for the Cloudflare tunnel to come online.
- Now we can continue with deploying `nomad-core`.
- When `nomad-core` is deployed, redeploy `aws-core` and `cloudflare-core` with `-r` (refresh).
  This undoes our temporary changes and makes the system whole again.
- Validate that the `nomad.openttd.org` in Cloudflare points to port 8686 again.
- Validate that the Lifecycle Hooks on the ASG are installed again.
