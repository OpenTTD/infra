#!/bin/sh

if [ -z "${1}" ] || [ -z "${2}" ]; then
    echo "Usage: $0 [private|public-v4|public-v6|all] <AutoJoin group>"
    exit 1
fi

if [ "${1}" = "private" ]; then
    /usr/local/bin/oci compute instance list-vnics --compartment-id @COMPARTMENT_ID@ --auth instance_principal | jq '.data[] | select((."freeform-tags".AutoJoin == "'${2}'") and (."lifecycle-state" == "AVAILABLE")) | ."private-ip"' -r | tr '\n' ' '
elif [ "${1}" = "public-v4" ]; then
    /usr/local/bin/oci compute instance list-vnics --compartment-id @COMPARTMENT_ID@ --auth instance_principal | jq '.data[] | select((."freeform-tags".AutoJoin == "'${2}'") and (."lifecycle-state" == "AVAILABLE")) | ."public-ip"' -r | tr '\n' ' '
elif [ "${1}" = "public-v6" ]; then
    /usr/local/bin/oci compute instance list-vnics --compartment-id @COMPARTMENT_ID@ --auth instance_principal | jq '.data[] | select((."freeform-tags".AutoJoin == "'${2}'") and (."lifecycle-state" == "AVAILABLE")) | ."ipv6-addresses"[0]' -r | tr '\n' ' '
elif [ "${1}" = "all" ]; then
    /usr/local/bin/oci compute instance list-vnics --compartment-id @COMPARTMENT_ID@ --auth instance_principal | jq '[ .data[] | select((."freeform-tags".AutoJoin == "'${2}'") and (."lifecycle-state" == "AVAILABLE")) | {"ipv6-addresses", "public-ip", "private-ip"} ]'
else
    echo "Usage: $0 [private|public-v4|public-v6|all] <AutoJoin group>"
    exit 1
fi
