job "wiki" {
  datacenters = ["dc1"]
  type = "service"

  group "wiki" {
    count = 1

    network {
      mode = "host"
      port "http" { to = 80 }
    }

    volume "cache" {
      type = "csi"
      read_only = false
      source = "wiki-cache"
      access_mode = "multi-node-multi-writer"
      attachment_mode = "file-system"
    }

    task "app" {
      driver = "docker"

      service {
        name = "wiki"
        port = "http"
        provider = "nomad"

        check {
          type = "http"
          name = "app_health"
          path = "/healthz"
          interval = "20s"
          timeout  = "5s"

          check_restart {
            limit = 3
            grace = "90s"
            ignore_warnings = false
          }
        }
      }

      config {
        image = "ghcr-proxy.openttd.org/truebrain/truewiki${CONTAINER_VERSION}"
        args = [
          "--bind",
          "::",
          "--bind",
          "0.0.0.0",
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

      template {
        data = <<-EOF
          {{ with nomadVar "nomad/jobs/wiki" }}
          CONTAINER_VERSION="{{ .version }}"

          TRUEWIKI_SENTRY_DSN="{{ .sentry_dsn }}"
          TRUEWIKI_FRONTEND_URL="{{ .frontend_url }}"
          TRUEWIKI_RELOAD_SECRET="{{ .reload_secret }}"

          TRUEWIKI_STORAGE="github"
          TRUEWIKI_STORAGE_GITHUB_URL="{{ .storage_github_url }}"
          TRUEWIKI_STORAGE_GITHUB_HISTORY_URL="{{ .storage_github_history_url }}"
          TRUEWIKI_STORAGE_GITHUB_APP_ID="{{ .storage_github_app_id }}"
          TRUEWIKI_STORAGE_GITHUB_APP_KEY="{{ .storage_github_app_key }}"
          TRUEWIKI_STORAGE_GITHUB_API_URL="{{ .storage_github_api_url }}"
          TRUEWIKI_STORAGE_FOLDER="/data"

          TRUEWIKI_USER="github"
          TRUEWIKI_USER_GITHUB_CLIENT_ID="{{ .user_github_client_id }}"
          TRUEWIKI_USER_GITHUB_CLIENT_SECRET="{{ .user_github_client_secret }}"
          TRUEWIKI_USER_GITHUB_API_URL="{{ .user_github_api_url }}"
          TRUEWIKI_USER_GITHUB_URL="{{ .user_github_url }}"

          TRUEWIKI_CACHE_METADATA_FILE="/cache/metadata.json"
          TRUEWIKI_CACHE_PAGE_FOLDER="/cache-pages"
          {{ end }}
        EOF

        destination = "secrets/vars.env"
        env = true
      }

      resources {
        cpu = 100
        memory = 128
      }
    }
  }
}
