job "bananas-api-[[ stack ]]" {
  datacenters = ["dc1"]
  type = "service"

  group "bananas-api" {
    # The api is stateful; as such, we can only run one container.
    count = 1

    network {
      mode = "host"
      port "http" { to = 80 }
      port "tusd" { to = 1080 }
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
        name = "bananas-api-[[ stack ]]-web"
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
        name = "bananas-api-[[ stack ]]-tusd"
        port = "tusd"
        provider = "nomad"

        tags = [
          "port=[[ tusd_port ]]"
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
        image = "ghcr-proxy.openttd.org/openttd/bananas-api[[ version ]]"
        args = [
          "--bind", "::",
          "--bind", "0.0.0.0",
          "--remote-ip-header", "cf-connecting-ip",
          "--storage", "s3",
          "--storage-s3-bucket", "[[ storage_s3_bucket ]]",
          "--storage-s3-endpoint-url", "[[ storage_s3_endpoint_url ]]",
          "--index", "github",
          "--index-github-url", "[[ index_github_url ]]",
          "--index-github-api-url", "https://github-api-proxy.openttd.org",
          "--client-file", "[[ client_file ]]",
          "--user", "github",
          "--behind-proxy",
        ]
        network_mode = "bridge"
        advertise_ipv6_address = true
        ports = ["http", "tusd"]
      }

      env {
        BANANAS_API_RELOAD_SECRET = "[[ reload_secret ]]"

        BANANAS_API_SENTRY_DSN = "[[ sentry_dsn ]]"
        BANANAS_API_SENTRY_ENVIRONMENT = "[[ sentry_environment ]]"

        BANANAS_API_USER_GITHUB_CLIENT_ID = "[[ user_github_client_id ]]"
        BANANAS_API_USER_GITHUB_CLIENT_SECRET = "[[ user_github_client_secret ]]"

        BANANAS_API_INDEX_GITHUB_APP_ID = "[[ index_github_app_id ]]"
        BANANAS_API_INDEX_GITHUB_APP_KEY = "[[ index_github_app_key ]]"

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
