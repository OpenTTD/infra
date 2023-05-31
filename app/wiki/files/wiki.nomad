job "wiki-[[ stack ]]" {
  datacenters = ["dc1"]
  type = "service"

  group "wiki" {
    # The wiki is stateful; as such, we can only run one container.
    count = 1

    network {
      mode = "host"
      port "http" { to = 80 }
    }

    volume "cache" {
      type = "csi"
      read_only = false
      source = "wiki-[[ stack ]]-cache"
      access_mode = "multi-node-multi-writer"
      attachment_mode = "file-system"
    }

    update {
      max_parallel = 1
      health_check = "checks"
      auto_promote = true
      canary = 1
    }

    task "app" {
      driver = "docker"

      service {
        name = "wiki-[[ stack ]]"
        port = "http"
        provider = "nomad"

        tags = [
          "port=7000"
        ]
        canary_tags = [
          "canary"
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
        image = "ghcr-proxy.openttd.org/truebrain/truewiki[[ version ]]"
        args = [
          "--bind", "::",
          "--bind", "0.0.0.0",
          "--storage", "github",
          "--storage-github-url", "[[ storage_github_url ]]",
          "--storage-github-api-url", "https://github-api-proxy.openttd.org",
          "--storage-folder", "/data",
          "--frontend-url", "[[ frontend_url ]]",
          "--user", "github",
          "--user-github-api-url", "https://github-api-proxy.openttd.org",
          "--user-github-url", "https://github-proxy.openttd.org",
          "--cache-metadata-file", "/cache/metadata.json",
          "--cache-page-folder", "/cache-pages",
       ]
        network_mode = "bridge"
        advertise_ipv6_address = true
        ports = ["http"]
      }

      volume_mount {
        volume      = "cache"
        destination = "/cache"
        read_only   = false
      }

      env {
        TRUEWIKI_RELOAD_SECRET = "[[ reload_secret ]]"

        TRUEWIKI_SENTRY_DSN = "[[ sentry_dsn ]]"
        TRUEWIKI_SENTRY_ENVIRONMENT = "[[ sentry_environment ]]"

        TRUEWIKI_STORAGE_GITHUB_APP_ID = "[[ storage_github_app_id ]]"
        TRUEWIKI_STORAGE_GITHUB_APP_KEY = "[[ storage_github_app_key ]]"

        TRUEWIKI_USER_GITHUB_CLIENT_ID = "[[ user_github_client_id ]]"
        TRUEWIKI_USER_GITHUB_CLIENT_SECRET = "[[ user_github_client_secret ]]"
      }

      resources {
        cpu = 100
        memory = [[ memory ]]
      }
    }
  }
}
