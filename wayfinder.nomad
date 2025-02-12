job "wayfinder" {
  datacenters = ["dc1"]
  type = "service"

  group "app" {
    count = 1

    network {
      port "http" {
        to = 5000
      }
    }

    service {
      name = "wayfinder"
      port = "http"
      provider = "nomad"

      check {
        type     = "http"
        path     = "/"
        interval = "10s"
        timeout  = "2s"
      }
    }

    task "server" {
      driver = "docker"

      config {
        image = "djschnei/wayfinder:latest"
        ports = ["http"]
      }

      resources {
        cpu    = 200
        memory = 256
      }
    }
  }
}
