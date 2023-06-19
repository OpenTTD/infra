job "dorpsgek-[[ stack ]]" {
  datacenters = ["dc1"]
  type = "service"

  group "dorpsgek" {
    # The dorpsgek is stateful; as such, we can only run one container.
    count = 1

    network {
      mode = "host"
      port "http" { to = 80 }
    }

    volume "logs" {
      type = "csi"
      read_only = false
      source = "dorpsgek-[[ stack ]]"
      access_mode = "multi-node-multi-writer"
      attachment_mode = "file-system"
    }

    task "app" {
      driver = "docker"

      service {
        name = "dorpsgek-[[ stack ]]"
        port = "http"
        provider = "nomad"

        tags = [
          "port=[[ port ]]",
        ]

        check {
          type = "http"
          name = "app_health"
          path = "/healthz"
          interval = "20s"
          timeout = "5s"

          check_restart {
            limit = 3
            grace = "90s"
            ignore_warnings = false
          }
        }
      }

      config {
        image = "ghcr-proxy.openttd.org/openttd/dorpsgek[[ version ]]"
        args = [
          "--irc-username", "[[ irc_username ]]",
          "--nickserv-username", "[[ irc_username ]]",
          "--addressed-by", "[[ addressed_by ]]",
          "--github-api-url", "https://github-api-proxy.openttd.org",
          [[ channels ]]
        ]
        network_mode = "bridge"
        advertise_ipv6_address = true
        ports = ["http"]
      }

      volume_mount {
        volume  = "logs"
        destination = "/code/logs/ChannelLogger"
        read_only = false
      }

      env {
        DORPSGEK_SENTRY_DSN = "[[ sentry_dsn ]]"
        DORPSGEK_SENTRY_ENVIRONMENT = "[[ sentry_environment ]]"

        DORPSGEK_GITHUB_APP_ID = "[[ github_app_id ]]"
        DORPSGEK_GITHUB_APP_PRIVATE_KEY = "[[ github_app_private_key ]]"
        DORPSGEK_GITHUB_APP_SECRET = "[[ github_app_webhook_secret ]]"

        DORPSGEK_NICKSERV_PASSWORD = "[[ nickserv_password ]]"

        DORPSGEK_DISCORD_WEBHOOK_URL = "[[ discord_webhook_url ]]"
        DORPSGEK_DISCORD_UNFILTERED_WEBHOOK_URL = "[[ discord_unfiltered_webhook_url ]]"
      }

      resources {
        cpu = 100
        memory = [[ memory ]]
        memory_max = [[ memory_max ]]
      }
    }
  }
}
