job "plugin-efs" {
  datacenters = ["dc1"]

  type = "system"

  constraint {
    operator = "distinct_hosts"
    value = true
  }

  group "nodes" {
    task "plugin" {
      driver = "docker"

      config {
        image = "registry.ipv6.docker.com/amazon/aws-efs-csi-driver:v1.5.6"

        args = [
          "--endpoint=unix://csi/csi.sock",
          "--logtostderr",
          "--v=5",
        ]

        privileged = true
      }

      csi_plugin {
        id = "aws-efs0"
        type = "node"
        mount_dir = "/csi"
        health_timeout = "30s"
      }

      resources {
        cpu = 100
        memory = 64
        memory_max = 128
      }
    }
  }
}
