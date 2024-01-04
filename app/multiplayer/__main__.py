import pulumi
import pulumi_openttd
import pulumi_nomad

import game_coordinator
import master_server
import web

config = pulumi.Config()
global_stack = pulumi.StackReference(f"{pulumi.get_organization()}/global-config/prod")
aws_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/aws-core/prod")
cloudflare_core_stack = pulumi.StackReference(f"{pulumi.get_organization()}/cloudflare-core/prod")


pulumi_openttd.autotag.register()

pulumi_nomad.Job(
    "redis",
    jobspec=open("files/redis.nomad").read().replace("[[ stack ]]", pulumi.get_stack()),
    purge_on_destroy=True,
)

game_coordinator.GameCoordinator(
    "coordinator",
    game_coordinator.GameCoordinatorArgs(
        cloudflare_zone_id=global_stack.get_output("cloudflare_zone_id"),
        coordinator_hostname=config.require("coordinator-hostname"),
        coordinator_memory_max=config.require("coordinator-memory-max"),
        coordinator_memory=config.require("coordinator-memory"),
        coordinator_port=config.require("coordinator-port"),
        coordinator_public_port=config.require("coordinator-public-port"),
        domain=global_stack.get_output("domain"),
        sentry_environment=config.require("sentry-environment"),
        sentry_ingest_hostname=global_stack.get_output("sentry_ingest_hostname"),
        shared_secret=config.require_secret("shared-secret"),
        stun_hostname=config.require("stun-hostname"),
        stun_memory_max=config.require("stun-memory-max"),
        stun_memory=config.require("stun-memory"),
        stun_port=config.require("stun-port"),
        stun_public_port=config.require("stun-public-port"),
        turn_1_port=config.require("turn-1-port"),
        turn_1_public_port=config.require("turn-1-public-port"),
        turn_2_port=config.require("turn-2-port"),
        turn_2_public_port=config.require("turn-2-public-port"),
        turn_hostname=config.require("turn-hostname"),
        turn_memory_max=config.require("turn-memory-max"),
        turn_memory=config.require("turn-memory"),
    ),
)

master_server.MasterServer(
    "master",
    master_server.MasterServerArgs(
        api_memory_max=config.require("api-memory-max"),
        api_memory=config.require("api-memory"),
        api_port=config.require("api-port"),
        cloudflare_zone_id=global_stack.get_output("cloudflare_zone_id"),
        domain=global_stack.get_output("domain"),
        master_hostname=config.require("master-hostname"),
        master_memory_max=config.require("master-memory-max"),
        master_memory=config.require("master-memory"),
        master_port=config.require("master-port"),
        master_public_port=config.require("master-public-port"),
        sentry_environment=config.require("sentry-environment"),
        sentry_ingest_hostname=global_stack.get_output("sentry_ingest_hostname"),
    ),
)

web.Web(
    "web",
    web.WebArgs(
        domain=global_stack.get_output("domain"),
        hostname=config.require("web-hostname"),
        memory_max=config.require("web-memory-max"),
        memory=config.require("web-memory"),
        port=config.require("web-port"),
        sentry_environment=config.require("sentry-environment"),
        sentry_ingest_hostname=global_stack.get_output("sentry_ingest_hostname"),
    ),
)
