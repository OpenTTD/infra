# OpenTTD's infrastructure

In this repository are several [Pulumi](pulumi.com/) projects that combined declare all of OpenTTD's infrastructure as code.

## Prerequisite

- Make sure you have an AWS profile named `openttd` with valid credentials.
- Make sure you have set `CLOUDFLARE_API_TOKEN` with a valid Cloudflare API token.

## Usage

### Core infrastructure

```bash
python3 -m venv .env
.env/bin/pip install -r requirements.txt

( cd aws-core && ../.env/bin/pulumi up )
( cd cloudflare-core && ../.env/bin/pulumi up )
```

### Proxy

```bash
cd cloudflare-core
export CF_ACCESS_CLIENT_ID=$(../.env/bin/pulumi stack output service_token_id --show-secrets)
export CF_ACCESS_CLIENT_SECRET=$(../.env/bin/pulumi stack output service_token_secret --show-secrets)
cd ..
.env/bin/python nomad-proxy nomad.openttd.org
```

Now you should be able to execute `nomad node status` and get a valid response.

## Subfolders

### Pulumi projects

- [aws-core](./aws-core): contains the core infrastructure for AWS.
- [cloudflare-core](./cloudflare-core): contains the core infrastructure for Cloudflare.

### Tools

- [nomad-proxy](./nomad-proxy): as Nomad runs behind Cloudflare Access, it needs extra credentials before Nomad CLI works.
  This proxy adds those credentials for the Nomad CLI.
  See the nomad-proxy's [README](./nomad-proxy/README.md) for more information.

## Bootstrapping

When this is deployed for the first time, [Nomad](https://www.hashicorp.com/products/nomad) is empty, and running in a private subnet on AWS.
In result, it is inaccessible.

To solve this, some minor manual labor is required:
- Run `pulumi stack output tunnel_token --show-secrets` in the `cloudflare-core` project and remember the output.
- Login to AWS.
- Find one of the Nomad EC2 instances.
- Open an EC2 Serial Console.
- Login with `ec2-user` and the password as given via `console_password` config.
- Run the following commands:

```bash
curl -sL https://raw.githubusercontent.com/OpenTTD/infra/main/aws-core/files/cloudflared.nomad -o /tmp/cloudflared.nomad
nomad var put nomad/jobs/cloudflared tunnel_token=<tunnel token>
nomad job run /tmp/cloudflared.nomad
```

- When the tunnel comes online, Cloudflare can be used to access Nomad's UI.
- From here on, the other Pulumi projects can be executed.
