#!/bin/env python3

"""

"""

import aiohttp
import asyncio
import json
import logging
import shlex
import signal

NLB = []
TASK = None
LOOP = None

log = logging.getLogger(__name__)


async def update_dns(domain, ips):
    # First request all current entries (so we can remove them).
    async with aiohttp.ClientSession() as session:
        response = await session.get(
            f"https://api.cloudflare.com/client/v4/zones/[[ cloudflare_zone_id ]]/dns_records",
            params={"name": domain},
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer [[ cloudflare_api_token ]]",
            },
            raise_for_status=True,
        )
        payload = await response.json()

        # Check what IPs need to be added and which to be removed.
        for record in payload["result"]:
            # The record is already there.
            if (record["type"], record["content"]) in ips:
                ips.remove((record["type"], record["content"]))
                continue

            # The record is not there, remove it.
            log.info(f"Removing {record['type']} record {record['content']} ...")
            await session.delete(
                f"https://api.cloudflare.com/client/v4/zones/[[ cloudflare_zone_id ]]/dns_records/{record['id']}",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer [[ cloudflare_api_token ]]",
                },
                raise_for_status=True,
            )

        # Add all the remaining records.
        for ip in ips:
            log.info(f"Adding {ip[0]} record {ip[1]} ...")
            await session.post(
                f"https://api.cloudflare.com/client/v4/zones/[[ cloudflare_zone_id ]]/dns_records",
                json={
                    "type": ip[0],
                    "name": domain,
                    "content": ip[1],
                    "ttl": 60,
                    "proxied": False,
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer [[ cloudflare_api_token ]]",
                },
                raise_for_status=True,
            )


async def update_nlb_dns():
    log.info("NLB configuration changed, updating DNS ...")

    if "[[ target ]]" == "aws":
        proc = await asyncio.create_subprocess_exec(
            "aws",
            *shlex.split(
                "--region eu-west-1 ec2 describe-instances --query 'Reservations[].Instances[].{private:PrivateIpAddress,public_v4:PublicIpAddress,public_v6:NetworkInterfaces[0].Ipv6Prefixes[0].Ipv6Prefix}'"
            ),
            stdout=asyncio.subprocess.PIPE,
        )
        if await proc.wait() != 0:
            log.warning("Failed to get IP mapping")
            return

        ip_mapping = json.loads(await proc.stdout.read())

        # Map the private IP addresses to the public IP addresses.
        ips = []
        for nlb in NLB:
            if not nlb:
                continue

            for ip_map in ip_mapping:
                if ip_map["private"] == nlb:
                    ips.append(("A", ip_map["public_v4"]))
                    ips.append(("AAAA", ip_map["public_v6"].replace("::/80", "::1")))
                    break
            else:
                log.warning(f"Could not find public IP for NLB {nlb}")
    elif "[[ target ]]" == "oci":
        proc = await asyncio.create_subprocess_exec(
            "oci-list-pool-ips.sh",
            *shlex.split("all nomad-public"),
            stdout=asyncio.subprocess.PIPE,
        )
        if await proc.wait() != 0:
            log.warning("Failed to get IP mapping")
            return

        ip_mapping = json.loads(await proc.stdout.read())

        # Map the private IP addresses to the public IP addresses.
        ips = []
        for nlb in NLB:
            if not nlb:
                continue

            for ip_map in ip_mapping:
                if ip_map["private-ip"] == nlb:
                    ips.append(("A", ip_map["public-ip"]))
                    ips.append(("AAAA", ip_map["ipv6-addresses"][0]))
                    break
            else:
                log.warning(f"Could not find public IP for NLB {nlb}")
    else:
        log.warning("Unknown target")
        return

    log.info(f"Public IPs detected:")
    for ip in ips:
        log.info(f"  {ip[1]}")
    log.info("")

    await update_dns("nlb-[[ target ]].openttd.org", ips)

    # Also create a DNS entry for the internal IP addresses. This is not ideal,
    # as you tell the outside world what your internal IP addresses are, but it
    # is by far the simplest way to get a round-robin DNS for the internal
    # services.
    ips = []
    for nlb in NLB:
        if not nlb:
            continue

        ips.append(("A", nlb))

    log.info(f"Internal IPs detected:")
    for ip in ips:
        log.info(f"  {ip[1]}")
    log.info("")

    await update_dns("nlb-[[ target ]]-internal.openttd.org", ips)

    log.info("DNS updated.")
    global TASK
    TASK = None


async def update_nlb_dns_wrapper():
    try:
        await update_nlb_dns()
    except Exception:
        log.exception("Failed to update NLB DNS.")


def update_nlb_dns_trigger():
    global TASK

    if TASK:
        log.info("Cancelling update; newer update found.")
        TASK.cancel()

    TASK = LOOP.create_task(update_nlb_dns_wrapper())


def handle_sighup(*args):
    log.info("Reloading files ...")
    global NLB

    nlb = json.loads(open("local/nlb.json").read())

    if nlb != NLB:
        NLB = nlb
        LOOP.call_soon_threadsafe(update_nlb_dns_trigger)


def main():
    global LOOP

    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO
    )

    LOOP = asyncio.new_event_loop()

    handle_sighup()
    signal.signal(signal.SIGHUP, handle_sighup)

    LOOP.run_forever()


if __name__ == "__main__":
    main()
