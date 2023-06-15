job "bananas-web-[[ stack ]]" {
  datacenters = ["dc1"]
  type = "service"

  group "bananas-web" {
    # The web is stateful; as such, we can only run one container.
    count = 1

    network {
      mode = "host"
      port "http" { to = 5000 }
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
        name = "bananas-web-[[ stack ]]"
        port = "http"
        provider = "nomad"

        tags = [
          "port=[[ port ]]",
        ]
        canary_tags = [
          "canary",
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
        image = "ghcr-proxy.openttd.org/openttd/bananas-frontend-web[[ version ]]"
        args = [
          "--api-url", "[[ api_url ]]",
          "--frontend-url", "[[ frontend_url ]]",
          "--remote-ip-header", "cf-connecting-ip",
          "run",
          "-h", "::",
        ]
        network_mode = "bridge"
        advertise_ipv6_address = true
        ports = ["http"]
      }

      env {
        WEBCLIENT_SENTRY_DSN = "[[ sentry_dsn ]]"
        WEBCLIENT_SENTRY_ENVIRONMENT = "[[ sentry_environment ]]"
      }

      resources {
        cpu = 100
        memory = [[ memory ]]
        memory_max = [[ memory_max ]]
      }
    }
  }
}
