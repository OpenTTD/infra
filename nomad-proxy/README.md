# Nomad's Proxy

Nomad runs behind Cloudflare Access.
For authentication, it needs to have two headers (`CF-Access-Client-Id` and `CF-Access-Client-Secret`).
Sadly, Nomad CLI gives no way to add those headers.

There is where this proxy comes in:
- You tell Nomad CLI to use this proxy as endpoint.
- This endpoint forwards the request to the actual Nomad instance, but with the above two headers set.

## Installation

From the root of this repository:

```bash
python3 -m venv .env
.env/bin/pip install -r requirements.txt
```

The `.env` can be shared with Pulumi, that is no problem.

## Usage

```bash
CF_ACCESS_CLIENT_ID=<access-client-id> CF_ACCESS_CLIENT_SECRET=<access-client-secret> .env/bin/python -m nomad-proxy <uri-of-nomad-behind-cloudflare-access>
```
