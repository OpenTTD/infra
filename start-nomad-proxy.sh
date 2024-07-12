#!/bin/sh

if [ -z "${1}" ]; then
    echo "Usage: ${0} [aws|oci]"
    exit 1
fi

cd cloudflare-core
export CF_ACCESS_CLIENT_ID=$(pulumi stack output service_token_id --show-secrets)
export CF_ACCESS_CLIENT_SECRET=$(pulumi stack output service_token_secret --show-secrets)
cd ..

# 4646 -- Old Nomad, never use.
# 4747 -- OCI Nomad
# 4848 -- AWS Nomad

if [ "${1}" = "aws-old" ]; then
    port=4646
    hostname="aws"
elif [ "${1}" = "aws" ]; then
    port=4848
    hostname="aws"
elif [ "${1}" = "oci" ]; then
    port=4747
    hostname="oci"
elif [ "${1}" = "oci-migrate" ]; then
    port=4848
    hostname="oci"
else
    echo "Invalid cloud provider: ${1}"
    exit 1
fi

.env/bin/python -m nomad-proxy nomad-${hostname}.openttd.org ${port}
