job "bananas-server-[[ stack ]]" {
  datacenters = ["dc1"]
  type = "service"

  spread {
    attribute = "${node.unique.id}"
  }

  group "bananas-server" {
    count = [[ count ]]

    network {
      mode = "host"
      port "http" { to = 80 }
      port "content" { to = 3978 }
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
        name = "bananas-server-[[ stack ]]-web"
        port = "http"
        provider = "nomad"

        tags = [
          "port=[[ web_port ]]"
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

      service {
        name = "bananas-server-[[ stack ]]-content"
        port = "content"
        provider = "nomad"

        tags = [
          "port=[[ content_port ]]",
          "public=[[ content_public_port ]]"
        ]
        canary_tags = [
          "canary"
        ]

        check {
          type = "http"
          port = "http"
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
        image = "ghcr-proxy.openttd.org/openttd/bananas-server[[ version ]]"
        args = [
          "--bind", "::",
          "--bind", "0.0.0.0",
          "--remote-ip-header", "cf-connecting-ip",
          "--storage", "s3",
          "--storage-s3-bucket", "[[ storage_s3_bucket ]]",
          "--storage-s3-endpoint-url", "[[ storage_s3_endpoint_url ]]",
          "--index", "github",
          "--index-github-url", "[[ index_github_url ]]",
          "--cdn-fallback-url", "[[ cdn_fallback_url ]]",
          "--proxy-protocol",
          [[ bootstrap_command ]]
        ]
        network_mode = "bridge"
        advertise_ipv6_address = true
        ports = ["http", "content"]
      }

      env {
        BANANAS_SERVER_RELOAD_SECRET = "[[ reload_secret ]]"

        BANANAS_SERVER_SENTRY_DSN = "[[ sentry_dsn ]]"
        BANANAS_SERVER_SENTRY_ENVIRONMENT = "[[ sentry_environment ]]"

        AWS_ACCESS_KEY_ID = "[[ storage_s3_access_key_id ]]"
        AWS_SECRET_ACCESS_KEY = "[[ storage_s3_secret_access_key ]]"
      }

      resources {
        cpu = 100
        memory = [[ memory ]]
      }
    }
  }
}
