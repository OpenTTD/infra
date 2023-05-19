# OpenTTD's infrastructure

In this repository are several [Pulumi](pulumi.com/) projects that combined declare all of OpenTTD's infrastructure as code.

## Usage

```bash
python3 -m venv .env
.env/bin/pip install -r requirements.txt

( cd aws-core && ../.env/bin/pulumi up )
```

## Projects

- [aws-core](./aws-core): contains the core infrastructure for AWS.

## Bootstrapping

When this is deployed for the first time, [Nomad](https://www.hashicorp.com/products/nomad) is empty, and running in a private subnet on AWS.
In result, it is inaccessible.

To solve this, some minor manual labor is required:
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
