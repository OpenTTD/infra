job "cloudflared" {
  type = "service"

  group "cloudflared" {
    count = 1

    network {
      mode = "host"
    }

    task "cloudflared" {
      driver = "docker"

      config {
        image = "registry.ipv6.docker.com/cloudflare/cloudflared:latest"
        args = [
          "tunnel",
          "--no-autoupdate",
          "--edge-ip-version=6",
          "run"
        ]
        network_mode = "host"
      }

      template {
        data = <<-EOF
          {{with nomadVar "nomad/jobs/cloudflared"}}
          TUNNEL_TOKEN="{{.tunnel_token}}"
          {{end}}
        EOF

        destination = "secrets/vars.env"
        env = true
      }
    }
  }
}
