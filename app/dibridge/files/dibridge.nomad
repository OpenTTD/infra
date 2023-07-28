job "dibridge-[[ stack ]]" {
  datacenters = ["public"]
  type = "service"

  group "dibridge" {
    # The dibridge is stateful; as such, we can only run one container.
    count = 1

    network {
      mode = "host"
    }

    task "app" {
      driver = "docker"

      config {
        image = "ghcr-proxy.openttd.org/openttd/dibridge[[ version ]]"
        args = [
          "--discord-channel-id", "[[ discord_channel_id ]]",
          "--irc-host", "[[ irc_host ]]",
          "--irc-nick", "[[ irc_nick ]]",
          "--irc-channel", "[[ irc_channel ]]",
          "--irc-ignore-list", "dorpsgek",
        ]
        network_mode = "host"
      }

      env {
        DIBRIDGE_SENTRY_DSN = "[[ sentry_dsn ]]"
        DIBRIDGE_SENTRY_ENVIRONMENT = "[[ sentry_environment ]]"

        DIBRIDGE_DISCORD_TOKEN = "[[ discord_token ]]"
        DIBRIDGE_IRC_PUPPET_IP_RANGE = "${meta.dibridge.ip_range}"
      }

      resources {
        cpu = 100
        memory = [[ memory ]]
        memory_max = [[ memory_max ]]
      }
    }
  }
}
