job "eints-[[ stack ]]" {
  datacenters = ["dc1"]
  type = "service"

  group "eints" {
    # The eints is stateful; as such, we can only run one container.
    count = 1

    network {
      mode = "host"
      port "http" { to = 80 }
    }

    volume "data" {
      type = "csi"
      read_only = false
      source = "eints-[[ stack ]]"
      access_mode = "multi-node-multi-writer"
      attachment_mode = "file-system"
    }

    task "app" {
      driver = "docker"

      service {
        name = "eints-[[ stack ]]"
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
        image = "ghcr-proxy.openttd.org/openttd/eints[[ version ]]"
        args = [
          "--server-host", "::",
          "--server-port", "80",
          "--server-mode", "production",
          "--authentication", "github",
          "--stable-languages", "stable_languages",
          "--unstable-languages", "unstable_languages",
          "--project-cache", "10",
          "--project-types", "openttd",
          "--project-types", "newgrf",
          "--project-types", "game-script",
          "--storage-format", "split-languages",
          "--data-format", "json",
          "--language-file-size", "10000000",
          "--num-backup-files", "1",
          "--max-num-changes", "5",
          "--min-num-changes", "2",
          "--change-stable-age", "600",
          "--github-organization", "OpenTTD",
          "--github-api-url", "https://github-api-proxy.openttd.org",
          "--github-url", "https://github-proxy.openttd.org",
        ]
        network_mode = "bridge"
        advertise_ipv6_address = true
        ports = ["http"]
      }

      volume_mount {
        volume      = "data"
        destination = "/data"
        read_only   = false
      }

      env {
        EINTS_SENTRY_DSN = "[[ sentry_dsn ]]"
        EINTS_SENTRY_ENVIRONMENT = "[[ sentry_environment ]]"

        EINTS_GITHUB_ORG_API_TOKEN = "[[ github_org_api_token ]]"
        EINTS_GITHUB_OAUTH2_CLIENT_ID = "[[ github_oauth2_client_id ]]"
        EINTS_GITHUB_OAUTH2_CLIENT_SECRET = "[[ github_oauth2_client_secret ]]"
        EINTS_TRANSLATORS_PASSWORD = "[[ translators_password ]]"
      }

      resources {
        cpu = 100
        memory = [[ memory ]]
        memory_max = [[ memory_max ]]
      }
    }
  }
}
