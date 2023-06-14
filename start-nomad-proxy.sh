#!/bin/sh

(
    cd cloudflare-core
    export CF_ACCESS_CLIENT_ID=$(pulumi stack output service_token_id --show-secrets)
    export CF_ACCESS_CLIENT_SECRET=$(pulumi stack output service_token_secret --show-secrets)
)

python -m nomad-proxy nomad.openttd.org
