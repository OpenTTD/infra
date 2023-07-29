job "prometheus" {
  datacenters = ["dc1"]
  type = "service"

  group "prometheus" {
    count = 1

    network {
      mode = "host"
      port "http" { to = 9090 }
    }

    task "app" {
      driver = "docker"

      service {
        name = "prometheus-web"
        port = "http"
        provider = "nomad"

        tags = [
          "port=10010",
        ]

        check {
          type = "http"
          name = "app_health"
          path = "/-/healthy"
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
        image = "registry.ipv6.docker.com/prom/prometheus:v2.44.0"
        args = [
          "--config.file=/etc/prometheus/local/prometheus.yml",
        ]
        network_mode = "bridge"
        advertise_ipv6_address = true
        ports = ["http"]
        volumes = [
            "local:/etc/prometheus/local",
        ]
      }

      resources {
        cpu = 100
        memory = 128
        memory_max = 256
      }

      template {
        data = <<EOT
---
global:
  scrape_interval:     5s
  evaluation_interval: 5s

remote_write:
- url: [[ grafana_cloud_url ]]
  basic_auth:
    username: [[ grafana_cloud_username ]]
    password: [[ grafana_cloud_password ]]

scrape_configs:
- job_name: nomad_services

  nomad_sd_configs:
  - server: 'http://{{ env "attr.unique.network.ip-address" }}:4646'

  relabel_configs:
  - source_labels: ['__meta_nomad_tags']
    regex: '(.*),metrics,(.*)'
    action: keep
  - source_labels: [__meta_nomad_service]
    target_label: job

  scrape_interval: 5s
  metrics_path: /metrics

- job_name: nomad

  static_configs:
  - targets: [
{{- range nomadService "nginx-public" }}
    "{{ .Address }}:4646",
{{- end }}
{{- range nomadService "nginx-dc1" }}
    "{{ .Address }}:4646",
{{- end }}
  ]

  metrics_path: /v1/metrics
  params:
    format: ['prometheus']
EOT

        destination = "local/prometheus.yml"
        change_mode = "signal"
        change_signal = "SIGHUP"
      }
    }
  }
}
