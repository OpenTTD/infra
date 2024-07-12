#!/bin/sh

CIDR_BLOCK=$(oci-metadata --get "vnics/*/ipv6SubnetCidrBlock" --json | jq -r '.vnics[1].ipv6SubnetCidrBlock' | sed 's/0000:0000:0000:0000/:/')
NODE_NUMBER=$(hostname | rev | cut -d- -f1 | rev | xargs -n 1 printf "%x")
PREFIX=$(echo ${CIDR_BLOCK} | sed "s@:/64@${NODE_NUMBER}::/80@")
LOCAL_VNIC=$(oci-metadata -j | jq '.vnics[0].vnicId' -r)
NETWORK_ENTITY_ID=$(/usr/local/bin/oci network ipv6 list --vnic-id ${LOCAL_VNIC} --auth instance_principal | jq -r '.data[0].id')

for ocid in $(/usr/local/bin/oci network route-table list --compartment-id @COMPARTMENT_ID@ --auth instance_principal | jq -r '.data[].id'); do
    /usr/local/bin/oci network route-table get --rt-id ${ocid} --auth instance_principal > /tmp/route-table.json

    if [ -n "$(grep 'Default Route Table' /tmp/route-table.json)" ]; then
        echo "[${ocid}] Skipping default route-table."
        continue
    fi

    # Check if this route is already announced.
    match=$(cat /tmp/route-table.json | jq '.data."route-rules"[] | select(.destination == "'${PREFIX}'") | ."network-entity-id"' -r)
    if [ -z "${match}" ]; then
        echo "[${ocid}] Adding prefix ${PREFIX}"

        while true; do
            cat /tmp/route-table.json | jq '.data."route-rules"[.data."route-rules" | length] |= . + {
                "cidr-block": null,
                "description": null,
                "destination": "'${PREFIX}'",
                "destination-type": "CIDR_BLOCK",
                "network-entity-id": "'${NETWORK_ENTITY_ID}'",
                "route-type": "STATIC"
            } | [ .data."route-rules"[] ]' > /tmp/route-table-update.json

            etag=$(cat /tmp/route-table.json | jq '.etag' -r)
            /usr/local/bin/oci network route-table update --force --rt-id ${ocid} --route-rules file:///tmp/route-table-update.json --if-match ${etag} --auth instance_principal > /dev/null
            if [ $? -eq 0 ]; then
                break
            fi

            # We failed to update. Most likely the etag mismatched, due to concurrency. Retry.
            echo "[${ocid}] Failed to update route-table. Retrying after 5s..."
            sleep 5
            /usr/local/bin/oci network route-table get --rt-id ${ocid} --auth instance_principal > /tmp/route-table.json
        done

    elif [ "${match}" != "${NETWORK_ENTITY_ID}" ]; then
        # The route is announced, but to another network entity. This should never happen, so only error about it.
        echo "[${ocid}] ERROR: Prefix ${PREFIX} is already in route-table, but pointing to another VNIC."
    else
        echo "[${ocid}] Prefix ${PREFIX} is already in route-table."
    fi
done
