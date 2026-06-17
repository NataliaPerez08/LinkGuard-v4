# Historial de Rendimiento y Conectividad

## 2026-06-14 17:52:28 CST

- reporte actual: `/home/natalia/Documents/Releasev4/docs/reporte-rendimiento-conectividad.md`
- estado del orquestador: `healthy`
- peers visibles: `6`
- qemu incluido: `no`

### hub-spoke

- conectividad real OK: `3/3`
- RTT real promedio agregado: `3.496 ms`
- throughput real promedio agregado: `5.95 Mbps`

### mesh

- conectividad real OK: `3/3`
- RTT real promedio agregado: `1.760 ms`
- throughput real promedio agregado: `5.28 Mbps`
- incluye vista del orquestador para topología con peers mesh

### hub-mesh

- conectividad real OK: `3/3`
- RTT real promedio agregado: `3.592 ms`
- throughput real promedio agregado: `5.17 Mbps`
- incluye vista del orquestador para topología con peers mesh

---
## 2026-06-14 18:00:05 CST

- reporte actual: `/home/natalia/Documents/Releasev4/docs/reporte-rendimiento-conectividad.md`
- estado del orquestador: `healthy`
- peers visibles: `6`
- qemu incluido: `no`

### hub-spoke

- conectividad real OK: `3/3`
- RTT real promedio agregado: `3.551 ms`
- throughput real promedio agregado: `5.17 Mbps`

### mesh

- conectividad real OK: `3/3`
- RTT real promedio agregado: `1.776 ms`
- throughput real promedio agregado: `5.42 Mbps`
- incluye vista del orquestador para topología con peers mesh

### hub-mesh

- conectividad real OK: `3/3`
- RTT real promedio agregado: `3.552 ms`
- throughput real promedio agregado: `5.31 Mbps`
- incluye vista del orquestador para topología con peers mesh

### JSON crudo

```json
{
  "health": {
    "config_version": 161,
    "hub_reachable": true,
    "networks_count": 1,
    "peers_count": 6,
    "status": "healthy"
  },
  "peers": {
    "peer-122-8-179-57": {
      "created_ts": 1781360083,
      "enabled": true,
      "endpoint": "122.8.179.57:51820",
      "ip": "10.20.30.2",
      "keepalive": 25,
      "last_heartbeat": 1781481814,
      "metadata": {
        "owner": "peer-122-8-179-57"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=",
      "status": {
        "endpoint": "122.8.179.57:51820",
        "nat_type": "symmetric",
        "ts": 1781481814,
        "wg": "interface: wg0\n  public key: FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 22 seconds ago\n  transfer: 119.21 MiB received, 3.33 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "user_id": "peer-122-8-179-57"
    },
    "peer-46-250-162-141": {
      "created_ts": 1781360083,
      "enabled": true,
      "endpoint": "46.250.162.141:51820",
      "ip": "10.20.30.3",
      "keepalive": 25,
      "last_heartbeat": 1781481816,
      "metadata": {
        "owner": "peer-46-250-162-141"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=",
      "status": {
        "endpoint": "46.250.162.141:51820",
        "nat_type": "symmetric",
        "ts": 1781481816,
        "wg": "interface: wg0\n  public key: 0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 41 seconds ago\n  transfer: 107.33 MiB received, 3.94 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "user_id": "peer-46-250-162-141"
    },
    "peer-46-250-168-185": {
      "created_ts": 1781360082,
      "enabled": true,
      "endpoint": "46.250.168.185:51820",
      "ip": "10.20.30.4",
      "keepalive": 25,
      "last_heartbeat": 1781481812,
      "metadata": {
        "owner": "peer-46-250-168-185"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=",
      "status": {
        "endpoint": "46.250.168.185:51820",
        "nat_type": "symmetric",
        "ts": 1781481812,
        "wg": "interface: wg0\n  public key: ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 51 seconds ago\n  transfer: 6.67 MiB received, 273.46 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "user_id": "peer-46-250-168-185"
    },
    "qemu-orq": {
      "created_ts": 1781458875,
      "enabled": true,
      "endpoint": "192.168.100.10:51820",
      "ip": "10.20.30.5",
      "keepalive": 25,
      "last_heartbeat": 1781479757,
      "metadata": {
        "owner": "qemu-orq"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=",
      "status": {
        "endpoint": "192.168.100.10:51820",
        "nat_type": "symmetric",
        "ts": 1781479755,
        "wg": "interface: wg0\n  public key: LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 1 minute, 40 seconds ago\n  transfer: 92 B received, 276 B sent\n  persistent keepalive: every 25 seconds\n"
      },
      "tags": [
        "qemu",
        "lab"
      ],
      "user_id": "qemu-orq"
    },
    "qemu-pa": {
      "created_ts": 1781458884,
      "enabled": true,
      "endpoint": "192.168.100.20:51820",
      "ip": "10.20.30.6",
      "keepalive": 25,
      "last_heartbeat": 1781479743,
      "metadata": {
        "owner": "qemu-pa"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=",
      "status": {
        "endpoint": "192.168.100.20:51820",
        "nat_type": "symmetric",
        "ts": 1781479740,
        "wg": "interface: wg0\n  public key: c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 1 minute, 50 seconds ago\n  transfer: 92 B received, 308 B sent\n  persistent keepalive: every 25 seconds\n"
      },
      "tags": [
        "qemu",
        "lab"
      ],
      "user_id": "qemu-pa"
    },
    "qemu-pb": {
      "created_ts": 1781458893,
      "enabled": true,
      "endpoint": "192.168.100.30:51820",
      "ip": "10.20.30.7",
      "keepalive": 25,
      "last_heartbeat": 1781479752,
      "metadata": {
        "owner": "qemu-pb"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=",
      "status": {
        "endpoint": "192.168.100.30:51820",
        "nat_type": "symmetric",
        "ts": 1781479749,
        "wg": "interface: wg0\n  public key: h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 1 minute, 59 seconds ago\n  transfer: 92 B received, 308 B sent\n  persistent keepalive: every 25 seconds\n"
      },
      "tags": [
        "qemu",
        "lab"
      ],
      "user_id": "qemu-pb"
    }
  },
  "qemu_included": false,
  "report_path": "/home/natalia/Documents/Releasev4/docs/reporte-rendimiento-conectividad.md",
  "timestamp": "2026-06-14 18:00:05 CST",
  "topology_results": [
    {
      "mesh_view": null,
      "qemu_pings": [],
      "qemu_throughput": [],
      "real_pings": [
        {
          "avg_ms": 4.804,
          "dst": "10.20.30.2",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 2.943,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 2.906,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.2"
        }
      ],
      "real_throughput": [
        {
          "http": 200,
          "mbps": 5.28,
          "peer_id": "peer-122-8-179-57",
          "size_download": 8388608,
          "speed_download": 660312,
          "time_total": 12.703995
        },
        {
          "http": 200,
          "mbps": 5.05,
          "peer_id": "peer-46-250-162-141",
          "size_download": 8388608,
          "speed_download": 631007,
          "time_total": 13.294529
        }
      ],
      "topology": "hub-spoke"
    },
    {
      "mesh_view": [
        {
          "alive": true,
          "endpoint": "122.8.179.57:51820",
          "last_seen_ts": 1781481727,
          "peer_id": "peer-122-8-179-57",
          "public_key": "FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=",
          "tunnel_ip": "10.20.30.2"
        },
        {
          "alive": true,
          "endpoint": "46.250.162.141:51820",
          "last_seen_ts": 1781481729,
          "peer_id": "peer-46-250-162-141",
          "public_key": "0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=",
          "tunnel_ip": "10.20.30.3"
        },
        {
          "alive": true,
          "endpoint": "46.250.168.185:51820",
          "last_seen_ts": 1781481725,
          "peer_id": "peer-46-250-168-185",
          "public_key": "ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=",
          "tunnel_ip": "10.20.30.4"
        },
        {
          "alive": false,
          "endpoint": "192.168.100.10:51820",
          "last_seen_ts": 1781479757,
          "peer_id": "qemu-orq",
          "public_key": "LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=",
          "tunnel_ip": "10.20.30.5"
        },
        {
          "alive": false,
          "endpoint": "192.168.100.20:51820",
          "last_seen_ts": 1781479743,
          "peer_id": "qemu-pa",
          "public_key": "c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=",
          "tunnel_ip": "10.20.30.6"
        },
        {
          "alive": false,
          "endpoint": "192.168.100.30:51820",
          "last_seen_ts": 1781479752,
          "peer_id": "qemu-pb",
          "public_key": "h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=",
          "tunnel_ip": "10.20.30.7"
        }
      ],
      "qemu_pings": [],
      "qemu_throughput": [],
      "real_pings": [
        {
          "avg_ms": 2.383,
          "dst": "10.20.30.2",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 1.474,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 1.471,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.2"
        }
      ],
      "real_throughput": [
        {
          "http": 200,
          "mbps": 5.39,
          "peer_id": "peer-122-8-179-57",
          "size_download": 8388608,
          "speed_download": 673347,
          "time_total": 12.458064
        },
        {
          "http": 200,
          "mbps": 5.45,
          "peer_id": "peer-46-250-162-141",
          "size_download": 8388608,
          "speed_download": 680782,
          "time_total": 12.322312
        }
      ],
      "topology": "mesh"
    },
    {
      "mesh_view": {
        "direct": [],
        "relay_cidr": "10.20.30.0/24",
        "relay_only": [
          {
            "alive": true,
            "endpoint": "122.8.179.57:51820",
            "last_seen_ts": 1781481795,
            "nat_type": "symmetric",
            "peer_id": "peer-122-8-179-57",
            "public_key": "FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.2"
          },
          {
            "alive": true,
            "endpoint": "46.250.162.141:51820",
            "last_seen_ts": 1781481797,
            "nat_type": "symmetric",
            "peer_id": "peer-46-250-162-141",
            "public_key": "0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.3"
          },
          {
            "alive": true,
            "endpoint": "46.250.168.185:51820",
            "last_seen_ts": 1781481794,
            "nat_type": "symmetric",
            "peer_id": "peer-46-250-168-185",
            "public_key": "ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.4"
          }
        ]
      },
      "qemu_pings": [],
      "qemu_throughput": [],
      "real_pings": [
        {
          "avg_ms": 4.792,
          "dst": "10.20.30.2",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 2.948,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 2.915,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.2"
        }
      ],
      "real_throughput": [
        {
          "http": 200,
          "mbps": 5.53,
          "peer_id": "peer-122-8-179-57",
          "size_download": 8388608,
          "speed_download": 691608,
          "time_total": 12.129129
        },
        {
          "http": 200,
          "mbps": 5.09,
          "peer_id": "peer-46-250-162-141",
          "size_download": 8388608,
          "speed_download": 636609,
          "time_total": 13.177007
        }
      ],
      "topology": "hub-mesh"
    }
  ]
}
```

---
## 2026-06-14 18:04:26 CST

- reporte actual: `/home/natalia/Documents/Releasev4/docs/reporte-rendimiento-conectividad.md`
- estado del orquestador: `healthy`
- peers visibles: `6`
- qemu incluido: `sí`

### hub-spoke

- conectividad real OK: `3/3`
- RTT real promedio agregado: `3.548 ms`
- throughput real promedio agregado: `5.39 Mbps`
- conectividad QEMU OK: `2/2`
- RTT QEMU promedio agregado: `180.005 ms`
- throughput QEMU promedio agregado: `4.41 Mbps`

### mesh

- conectividad real OK: `3/3`
- RTT real promedio agregado: `1.776 ms`
- throughput real promedio agregado: `5.67 Mbps`
- conectividad QEMU OK: `2/2`
- RTT QEMU promedio agregado: `3.191 ms`
- throughput QEMU promedio agregado: `30.83 Mbps`
- incluye vista del orquestador para topología con peers mesh

### hub-mesh

- conectividad real OK: `3/3`
- RTT real promedio agregado: `3.612 ms`
- throughput real promedio agregado: `4.85 Mbps`
- conectividad QEMU OK: `2/2`
- RTT QEMU promedio agregado: `194.046 ms`
- throughput QEMU promedio agregado: `4.02 Mbps`
- incluye vista del orquestador para topología con peers mesh

### JSON crudo

```json
{
  "health": {
    "config_version": 188,
    "hub_reachable": true,
    "networks_count": 1,
    "peers_count": 6,
    "status": "healthy"
  },
  "peers": {
    "peer-122-8-179-57": {
      "created_ts": 1781360083,
      "enabled": true,
      "endpoint": "122.8.179.57:51820",
      "ip": "10.20.30.2",
      "keepalive": 25,
      "last_heartbeat": 1781482342,
      "metadata": {
        "owner": "peer-122-8-179-57"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=",
      "status": {
        "endpoint": "122.8.179.57:51820",
        "nat_type": "symmetric",
        "ts": 1781482342,
        "wg": "interface: wg0\n  public key: FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 2 seconds ago\n  transfer: 136.22 MiB received, 3.75 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "user_id": "peer-122-8-179-57"
    },
    "peer-46-250-162-141": {
      "created_ts": 1781360083,
      "enabled": true,
      "endpoint": "46.250.162.141:51820",
      "ip": "10.20.30.3",
      "keepalive": 25,
      "last_heartbeat": 1781482343,
      "metadata": {
        "owner": "peer-46-250-162-141"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=",
      "status": {
        "endpoint": "46.250.162.141:51820",
        "nat_type": "symmetric",
        "ts": 1781482343,
        "wg": "interface: wg0\n  public key: 0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 1 minute, 51 seconds ago\n  transfer: 124.33 MiB received, 4.47 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "user_id": "peer-46-250-162-141"
    },
    "peer-46-250-168-185": {
      "created_ts": 1781360082,
      "enabled": true,
      "endpoint": "46.250.168.185:51820",
      "ip": "10.20.30.4",
      "keepalive": 25,
      "last_heartbeat": 1781482341,
      "metadata": {
        "owner": "peer-46-250-168-185"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=",
      "status": {
        "endpoint": "46.250.168.185:51820",
        "nat_type": "symmetric",
        "ts": 1781482341,
        "wg": "interface: wg0\n  public key: ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 1 minute ago\n  transfer: 7.62 MiB received, 315.92 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "user_id": "peer-46-250-168-185"
    },
    "qemu-orq": {
      "created_ts": 1781458875,
      "enabled": true,
      "endpoint": "192.168.100.10:51820",
      "ip": "10.20.30.5",
      "keepalive": 25,
      "last_heartbeat": 1781482346,
      "metadata": {
        "owner": "qemu-orq"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=",
      "status": {
        "endpoint": "192.168.100.10:51820",
        "nat_type": "symmetric",
        "ts": 1781482345,
        "wg": "interface: wg0\n  public key: LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 47 seconds ago\n  transfer: 276 B received, 1.02 KiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "tags": [
        "qemu",
        "lab"
      ],
      "user_id": "qemu-orq"
    },
    "qemu-pa": {
      "created_ts": 1781458884,
      "enabled": true,
      "endpoint": "192.168.100.20:51820",
      "ip": "10.20.30.6",
      "keepalive": 25,
      "last_heartbeat": 1781482348,
      "metadata": {
        "owner": "qemu-pa"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=",
      "status": {
        "endpoint": "192.168.100.20:51820",
        "nat_type": "symmetric",
        "ts": 1781482346,
        "wg": "interface: wg0\n  public key: c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 53 seconds ago\n  transfer: 215.05 KiB received, 8.56 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "tags": [
        "qemu",
        "lab"
      ],
      "user_id": "qemu-pa"
    },
    "qemu-pb": {
      "created_ts": 1781458893,
      "enabled": true,
      "endpoint": "192.168.100.30:51820",
      "ip": "10.20.30.7",
      "keepalive": 25,
      "last_heartbeat": 1781482349,
      "metadata": {
        "owner": "qemu-pb"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=",
      "status": {
        "endpoint": "192.168.100.30:51820",
        "nat_type": "symmetric",
        "ts": 1781482347,
        "wg": "interface: wg0\n  public key: h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 34 seconds ago\n  transfer: 8.49 MiB received, 215.59 KiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "tags": [
        "qemu",
        "lab"
      ],
      "user_id": "qemu-pb"
    }
  },
  "qemu_included": true,
  "report_path": "/home/natalia/Documents/Releasev4/docs/reporte-rendimiento-conectividad.md",
  "timestamp": "2026-06-14 18:04:26 CST",
  "topology_results": [
    {
      "mesh_view": null,
      "qemu_pings": [
        {
          "avg_ms": null,
          "dst": "qemu-pb",
          "ok": true,
          "src": "qemu-pa"
        },
        {
          "avg_ms": 180.005,
          "dst": "qemu-pa",
          "ok": true,
          "src": "qemu-pb"
        }
      ],
      "qemu_throughput": [
        {
          "http": 200,
          "mbps": 4.41,
          "peer_id": "qemu-pb",
          "size_download": 4194304,
          "speed_download": 550723,
          "time_total": 7.615992
        }
      ],
      "real_pings": [
        {
          "avg_ms": 4.82,
          "dst": "10.20.30.2",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 2.912,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 2.913,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.2"
        }
      ],
      "real_throughput": [
        {
          "http": 200,
          "mbps": 5.48,
          "peer_id": "peer-122-8-179-57",
          "size_download": 8388608,
          "speed_download": 684473,
          "time_total": 12.25556
        },
        {
          "http": 200,
          "mbps": 5.31,
          "peer_id": "peer-46-250-162-141",
          "size_download": 8388608,
          "speed_download": 664128,
          "time_total": 12.631403
        }
      ],
      "topology": "hub-spoke"
    },
    {
      "mesh_view": [
        {
          "alive": true,
          "endpoint": "122.8.179.57:51820",
          "last_seen_ts": 1781482205,
          "peer_id": "peer-122-8-179-57",
          "public_key": "FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=",
          "tunnel_ip": "10.20.30.2"
        },
        {
          "alive": true,
          "endpoint": "46.250.162.141:51820",
          "last_seen_ts": 1781482207,
          "peer_id": "peer-46-250-162-141",
          "public_key": "0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=",
          "tunnel_ip": "10.20.30.3"
        },
        {
          "alive": true,
          "endpoint": "46.250.168.185:51820",
          "last_seen_ts": 1781482205,
          "peer_id": "peer-46-250-168-185",
          "public_key": "ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=",
          "tunnel_ip": "10.20.30.4"
        },
        {
          "alive": true,
          "endpoint": "192.168.100.10:51820",
          "last_seen_ts": 1781482211,
          "peer_id": "qemu-orq",
          "public_key": "LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=",
          "tunnel_ip": "10.20.30.5"
        },
        {
          "alive": true,
          "endpoint": "192.168.100.20:51820",
          "last_seen_ts": 1781482213,
          "peer_id": "qemu-pa",
          "public_key": "c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=",
          "tunnel_ip": "10.20.30.6"
        },
        {
          "alive": true,
          "endpoint": "192.168.100.30:51820",
          "last_seen_ts": 1781482213,
          "peer_id": "qemu-pb",
          "public_key": "h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=",
          "tunnel_ip": "10.20.30.7"
        }
      ],
      "qemu_pings": [
        {
          "avg_ms": 2.88,
          "dst": "qemu-pb",
          "ok": true,
          "src": "qemu-pa"
        },
        {
          "avg_ms": 3.501,
          "dst": "qemu-pa",
          "ok": true,
          "src": "qemu-pb"
        }
      ],
      "qemu_throughput": [
        {
          "http": 200,
          "mbps": 30.83,
          "peer_id": "qemu-pb",
          "size_download": 4194304,
          "speed_download": 3854028,
          "time_total": 1.088291
        }
      ],
      "real_pings": [
        {
          "avg_ms": 2.394,
          "dst": "10.20.30.2",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 1.472,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 1.461,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.2"
        }
      ],
      "real_throughput": [
        {
          "http": 200,
          "mbps": 5.72,
          "peer_id": "peer-122-8-179-57",
          "size_download": 8388608,
          "speed_download": 715452,
          "time_total": 11.724902
        },
        {
          "http": 200,
          "mbps": 5.63,
          "peer_id": "peer-46-250-162-141",
          "size_download": 8388608,
          "speed_download": 703270,
          "time_total": 11.928529
        }
      ],
      "topology": "mesh"
    },
    {
      "mesh_view": {
        "direct": [],
        "relay_cidr": "10.20.30.0/24",
        "relay_only": [
          {
            "alive": true,
            "endpoint": "122.8.179.57:51820",
            "last_seen_ts": 1781482294,
            "nat_type": "symmetric",
            "peer_id": "peer-122-8-179-57",
            "public_key": "FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.2"
          },
          {
            "alive": true,
            "endpoint": "46.250.162.141:51820",
            "last_seen_ts": 1781482296,
            "nat_type": "symmetric",
            "peer_id": "peer-46-250-162-141",
            "public_key": "0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.3"
          },
          {
            "alive": true,
            "endpoint": "46.250.168.185:51820",
            "last_seen_ts": 1781482293,
            "nat_type": "symmetric",
            "peer_id": "peer-46-250-168-185",
            "public_key": "ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.4"
          },
          {
            "alive": true,
            "endpoint": "192.168.100.10:51820",
            "last_seen_ts": 1781482299,
            "nat_type": "symmetric",
            "peer_id": "qemu-orq",
            "public_key": "LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.5"
          },
          {
            "alive": true,
            "endpoint": "192.168.100.20:51820",
            "last_seen_ts": 1781482300,
            "nat_type": "symmetric",
            "peer_id": "qemu-pa",
            "public_key": "c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.6"
          },
          {
            "alive": true,
            "endpoint": "192.168.100.30:51820",
            "last_seen_ts": 1781482301,
            "nat_type": "symmetric",
            "peer_id": "qemu-pb",
            "public_key": "h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.7"
          }
        ]
      },
      "qemu_pings": [
        {
          "avg_ms": 195.804,
          "dst": "qemu-pb",
          "ok": true,
          "src": "qemu-pa"
        },
        {
          "avg_ms": 192.288,
          "dst": "qemu-pa",
          "ok": true,
          "src": "qemu-pb"
        }
      ],
      "qemu_throughput": [
        {
          "http": 200,
          "mbps": 4.02,
          "peer_id": "qemu-pb",
          "size_download": 4194304,
          "speed_download": 502790,
          "time_total": 8.342053
        }
      ],
      "real_pings": [
        {
          "avg_ms": 4.764,
          "dst": "10.20.30.2",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 2.919,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 3.154,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.2"
        }
      ],
      "real_throughput": [
        {
          "http": 200,
          "mbps": 4.1,
          "peer_id": "peer-122-8-179-57",
          "size_download": 8388608,
          "speed_download": 512021,
          "time_total": 16.383327
        },
        {
          "http": 200,
          "mbps": 5.6,
          "peer_id": "peer-46-250-162-141",
          "size_download": 8388608,
          "speed_download": 699808,
          "time_total": 11.987967
        }
      ],
      "topology": "hub-mesh"
    }
  ]
}
```

---
## 2026-06-14 18:13:18 CST

- reporte actual: `/home/natalia/Documents/Releasev4/docs/reporte-rendimiento-conectividad.md`
- estado del orquestador: `healthy`
- peers visibles: `6`
- qemu incluido: `sí`

### hub-spoke

- conectividad real OK: `3/3`
- RTT real promedio agregado: `3.552 ms`
- throughput real promedio agregado: `5.48 Mbps`
- conectividad QEMU OK: `2/2`
- RTT QEMU promedio agregado: `213.567 ms`
- throughput QEMU promedio agregado: `2.10 Mbps`

### mesh

- conectividad real OK: `3/3`
- RTT real promedio agregado: `1.780 ms`
- throughput real promedio agregado: `5.88 Mbps`
- conectividad QEMU OK: `2/2`
- RTT QEMU promedio agregado: `2.542 ms`
- throughput QEMU promedio agregado: `32.09 Mbps`
- incluye vista del orquestador para topología con peers mesh

### hub-mesh

- conectividad real OK: `3/3`
- RTT real promedio agregado: `3.575 ms`
- throughput real promedio agregado: `5.26 Mbps`
- conectividad QEMU OK: `2/2`
- RTT QEMU promedio agregado: `197.042 ms`
- throughput QEMU promedio agregado: `4.44 Mbps`
- incluye vista del orquestador para topología con peers mesh

### JSON crudo

```json
{
  "health": {
    "config_version": 220,
    "hub_reachable": true,
    "networks_count": 1,
    "peers_count": 6,
    "status": "healthy"
  },
  "peers": {
    "peer-122-8-179-57": {
      "created_ts": 1781360083,
      "enabled": true,
      "endpoint": "122.8.179.57:51820",
      "ip": "10.20.30.2",
      "keepalive": 25,
      "last_heartbeat": 1781482874,
      "metadata": {
        "owner": "peer-122-8-179-57"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=",
      "status": {
        "endpoint": "122.8.179.57:51820",
        "nat_type": "symmetric",
        "ts": 1781482874,
        "wg": "interface: wg0\n  public key: FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 9 seconds ago\n  transfer: 153.22 MiB received, 4.13 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "user_id": "peer-122-8-179-57"
    },
    "peer-46-250-162-141": {
      "created_ts": 1781360083,
      "enabled": true,
      "endpoint": "46.250.162.141:51820",
      "ip": "10.20.30.3",
      "keepalive": 25,
      "last_heartbeat": 1781482875,
      "metadata": {
        "owner": "peer-46-250-162-141"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=",
      "status": {
        "endpoint": "46.250.162.141:51820",
        "nat_type": "symmetric",
        "ts": 1781482875,
        "wg": "interface: wg0\n  public key: 0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 2 minutes, 17 seconds ago\n  transfer: 141.32 MiB received, 5.13 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "user_id": "peer-46-250-162-141"
    },
    "peer-46-250-168-185": {
      "created_ts": 1781360082,
      "enabled": true,
      "endpoint": "46.250.168.185:51820",
      "ip": "10.20.30.4",
      "keepalive": 25,
      "last_heartbeat": 1781482873,
      "metadata": {
        "owner": "peer-46-250-168-185"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=",
      "status": {
        "endpoint": "46.250.168.185:51820",
        "nat_type": "symmetric",
        "ts": 1781482873,
        "wg": "interface: wg0\n  public key: ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 58 seconds ago\n  transfer: 8.65 MiB received, 356.02 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "user_id": "peer-46-250-168-185"
    },
    "qemu-orq": {
      "created_ts": 1781458875,
      "enabled": true,
      "endpoint": "192.168.100.10:51820",
      "ip": "10.20.30.5",
      "keepalive": 25,
      "last_heartbeat": 1781482878,
      "metadata": {
        "owner": "qemu-orq"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=",
      "status": {
        "endpoint": "192.168.100.10:51820",
        "nat_type": "symmetric",
        "ts": 1781482877,
        "wg": "interface: wg0\n  public key: LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: Now\n  transfer: 368 B received, 1.17 KiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "tags": [
        "qemu",
        "lab"
      ],
      "user_id": "qemu-orq"
    },
    "qemu-pa": {
      "created_ts": 1781458884,
      "enabled": true,
      "endpoint": "192.168.100.20:51820",
      "ip": "10.20.30.6",
      "keepalive": 25,
      "last_heartbeat": 1781482879,
      "metadata": {
        "owner": "qemu-pa"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=",
      "status": {
        "endpoint": "192.168.100.20:51820",
        "nat_type": "symmetric",
        "ts": 1781482878,
        "wg": "interface: wg0\n  public key: c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 33 seconds ago\n  transfer: 237.48 KiB received, 8.53 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "tags": [
        "qemu",
        "lab"
      ],
      "user_id": "qemu-pa"
    },
    "qemu-pb": {
      "created_ts": 1781458893,
      "enabled": true,
      "endpoint": "192.168.100.30:51820",
      "ip": "10.20.30.7",
      "keepalive": 25,
      "last_heartbeat": 1781482880,
      "metadata": {
        "owner": "qemu-pb"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=",
      "status": {
        "endpoint": "192.168.100.30:51820",
        "nat_type": "symmetric",
        "ts": 1781482879,
        "wg": "interface: wg0\n  public key: h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 28 seconds ago\n  transfer: 8.50 MiB received, 238.20 KiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "tags": [
        "qemu",
        "lab"
      ],
      "user_id": "qemu-pb"
    }
  },
  "qemu_included": true,
  "report_path": "/home/natalia/Documents/Releasev4/docs/reporte-rendimiento-conectividad.md",
  "timestamp": "2026-06-14 18:13:18 CST",
  "topology_results": [
    {
      "mesh_view": null,
      "qemu_pings": [
        {
          "avg_ms": 177.71,
          "dst": "qemu-pb",
          "ok": true,
          "src": "qemu-pa"
        },
        {
          "avg_ms": 249.425,
          "dst": "qemu-pa",
          "ok": true,
          "src": "qemu-pb"
        }
      ],
      "qemu_throughput": [
        {
          "http": 200,
          "mbps": 2.1,
          "peer_id": "qemu-pb",
          "size_download": 4194304,
          "speed_download": 262522,
          "time_total": 15.97691
        }
      ],
      "real_pings": [
        {
          "avg_ms": 4.793,
          "dst": "10.20.30.2",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 2.904,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 2.96,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.2"
        }
      ],
      "real_throughput": [
        {
          "http": 200,
          "mbps": 5.77,
          "peer_id": "peer-122-8-179-57",
          "size_download": 8388608,
          "speed_download": 721821,
          "time_total": 11.621442
        },
        {
          "http": 200,
          "mbps": 5.19,
          "peer_id": "peer-46-250-162-141",
          "size_download": 8388608,
          "speed_download": 648821,
          "time_total": 12.929438
        }
      ],
      "topology": "hub-spoke"
    },
    {
      "mesh_view": [
        {
          "alive": true,
          "endpoint": "122.8.179.57:51820",
          "last_seen_ts": 1781482742,
          "peer_id": "peer-122-8-179-57",
          "public_key": "FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=",
          "tunnel_ip": "10.20.30.2"
        },
        {
          "alive": true,
          "endpoint": "46.250.162.141:51820",
          "last_seen_ts": 1781482743,
          "peer_id": "peer-46-250-162-141",
          "public_key": "0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=",
          "tunnel_ip": "10.20.30.3"
        },
        {
          "alive": true,
          "endpoint": "46.250.168.185:51820",
          "last_seen_ts": 1781482740,
          "peer_id": "peer-46-250-168-185",
          "public_key": "ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=",
          "tunnel_ip": "10.20.30.4"
        },
        {
          "alive": true,
          "endpoint": "192.168.100.10:51820",
          "last_seen_ts": 1781482751,
          "peer_id": "qemu-orq",
          "public_key": "LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=",
          "tunnel_ip": "10.20.30.5"
        },
        {
          "alive": true,
          "endpoint": "192.168.100.20:51820",
          "last_seen_ts": 1781482753,
          "peer_id": "qemu-pa",
          "public_key": "c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=",
          "tunnel_ip": "10.20.30.6"
        },
        {
          "alive": true,
          "endpoint": "192.168.100.30:51820",
          "last_seen_ts": 1781482751,
          "peer_id": "qemu-pb",
          "public_key": "h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=",
          "tunnel_ip": "10.20.30.7"
        }
      ],
      "qemu_pings": [
        {
          "avg_ms": 2.807,
          "dst": "qemu-pb",
          "ok": true,
          "src": "qemu-pa"
        },
        {
          "avg_ms": 2.278,
          "dst": "qemu-pa",
          "ok": true,
          "src": "qemu-pb"
        }
      ],
      "qemu_throughput": [
        {
          "http": 200,
          "mbps": 32.09,
          "peer_id": "qemu-pb",
          "size_download": 4194304,
          "speed_download": 4010939,
          "time_total": 1.045716
        }
      ],
      "real_pings": [
        {
          "avg_ms": 2.384,
          "dst": "10.20.30.2",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 1.506,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 1.45,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.2"
        }
      ],
      "real_throughput": [
        {
          "http": 200,
          "mbps": 6.23,
          "peer_id": "peer-122-8-179-57",
          "size_download": 8388608,
          "speed_download": 778460,
          "time_total": 10.775892
        },
        {
          "http": 200,
          "mbps": 5.53,
          "peer_id": "peer-46-250-162-141",
          "size_download": 8388608,
          "speed_download": 691216,
          "time_total": 12.136366
        }
      ],
      "topology": "mesh"
    },
    {
      "mesh_view": {
        "direct": [],
        "relay_cidr": "10.20.30.0/24",
        "relay_only": [
          {
            "alive": true,
            "endpoint": "122.8.179.57:51820",
            "last_seen_ts": 1781482827,
            "nat_type": "symmetric",
            "peer_id": "peer-122-8-179-57",
            "public_key": "FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.2"
          },
          {
            "alive": true,
            "endpoint": "46.250.162.141:51820",
            "last_seen_ts": 1781482828,
            "nat_type": "symmetric",
            "peer_id": "peer-46-250-162-141",
            "public_key": "0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.3"
          },
          {
            "alive": true,
            "endpoint": "46.250.168.185:51820",
            "last_seen_ts": 1781482826,
            "nat_type": "symmetric",
            "peer_id": "peer-46-250-168-185",
            "public_key": "ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.4"
          },
          {
            "alive": true,
            "endpoint": "192.168.100.10:51820",
            "last_seen_ts": 1781482832,
            "nat_type": "symmetric",
            "peer_id": "qemu-orq",
            "public_key": "LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.5"
          },
          {
            "alive": true,
            "endpoint": "192.168.100.20:51820",
            "last_seen_ts": 1781482834,
            "nat_type": "symmetric",
            "peer_id": "qemu-pa",
            "public_key": "c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.6"
          },
          {
            "alive": true,
            "endpoint": "192.168.100.30:51820",
            "last_seen_ts": 1781482835,
            "nat_type": "symmetric",
            "peer_id": "qemu-pb",
            "public_key": "h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.7"
          }
        ]
      },
      "qemu_pings": [
        {
          "avg_ms": null,
          "dst": "qemu-pb",
          "ok": true,
          "src": "qemu-pa"
        },
        {
          "avg_ms": 197.042,
          "dst": "qemu-pa",
          "ok": true,
          "src": "qemu-pb"
        }
      ],
      "qemu_throughput": [
        {
          "http": 200,
          "mbps": 4.44,
          "peer_id": "qemu-pb",
          "size_download": 4194304,
          "speed_download": 554515,
          "time_total": 7.563904
        }
      ],
      "real_pings": [
        {
          "avg_ms": 4.834,
          "dst": "10.20.30.2",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 3.024,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 2.866,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.2"
        }
      ],
      "real_throughput": [
        {
          "http": 200,
          "mbps": 5.13,
          "peer_id": "peer-122-8-179-57",
          "size_download": 8388608,
          "speed_download": 641761,
          "time_total": 13.071227
        },
        {
          "http": 200,
          "mbps": 5.39,
          "peer_id": "peer-46-250-162-141",
          "size_download": 8388608,
          "speed_download": 673892,
          "time_total": 12.448435
        }
      ],
      "topology": "hub-mesh"
    }
  ]
}
```

---
## 2026-06-14 18:22:08 CST

- reporte actual: `/home/natalia/Documents/Releasev4/docs/reporte-rendimiento-conectividad.md`
- estado del orquestador: `healthy`
- peers visibles: `6`
- qemu incluido: `sí`

### hub-spoke

- conectividad real OK: `3/3`
- RTT real promedio agregado: `3.481 ms`
- throughput real promedio agregado: `5.30 Mbps`
- conectividad QEMU OK: `2/2`
- RTT QEMU promedio agregado: `181.932 ms`
- throughput QEMU promedio agregado: `4.58 Mbps`

### mesh

- conectividad real OK: `3/3`
- RTT real promedio agregado: `1.768 ms`
- throughput real promedio agregado: `9.93 Mbps`
- conectividad QEMU OK: `2/2`
- RTT QEMU promedio agregado: `2.837 ms`
- throughput QEMU promedio agregado: `35.09 Mbps`
- incluye vista del orquestador para topología con peers mesh

### hub-mesh

- conectividad real OK: `3/3`
- RTT real promedio agregado: `3.541 ms`
- throughput real promedio agregado: `5.55 Mbps`
- conectividad QEMU OK: `2/2`
- RTT QEMU promedio agregado: `218.648 ms`
- throughput QEMU promedio agregado: `4.40 Mbps`
- incluye vista del orquestador para topología con peers mesh

### JSON crudo

```json
{
  "health": {
    "config_version": 252,
    "hub_reachable": true,
    "networks_count": 1,
    "peers_count": 6,
    "status": "healthy"
  },
  "peers": {
    "peer-122-8-179-57": {
      "created_ts": 1781360083,
      "enabled": true,
      "endpoint": "122.8.179.57:51820",
      "ip": "10.20.30.2",
      "keepalive": 25,
      "last_heartbeat": 1781483405,
      "metadata": {
        "owner": "peer-122-8-179-57"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=",
      "status": {
        "endpoint": "122.8.179.57:51820",
        "nat_type": "symmetric",
        "ts": 1781483405,
        "wg": "interface: wg0\n  public key: FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 16 seconds ago\n  transfer: 170.21 MiB received, 4.55 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "user_id": "peer-122-8-179-57"
    },
    "peer-46-250-162-141": {
      "created_ts": 1781360083,
      "enabled": true,
      "endpoint": "46.250.162.141:51820",
      "ip": "10.20.30.3",
      "keepalive": 25,
      "last_heartbeat": 1781483406,
      "metadata": {
        "owner": "peer-46-250-162-141"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=",
      "status": {
        "endpoint": "46.250.162.141:51820",
        "nat_type": "symmetric",
        "ts": 1781483406,
        "wg": "interface: wg0\n  public key: 0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 4 seconds ago\n  transfer: 158.31 MiB received, 5.67 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "user_id": "peer-46-250-162-141"
    },
    "peer-46-250-168-185": {
      "created_ts": 1781360082,
      "enabled": true,
      "endpoint": "46.250.168.185:51820",
      "ip": "10.20.30.4",
      "keepalive": 25,
      "last_heartbeat": 1781483404,
      "metadata": {
        "owner": "peer-46-250-168-185"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=",
      "status": {
        "endpoint": "46.250.168.185:51820",
        "nat_type": "symmetric",
        "ts": 1781483404,
        "wg": "interface: wg0\n  public key: ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 1 minute, 2 seconds ago\n  transfer: 9.60 MiB received, 396.67 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "user_id": "peer-46-250-168-185"
    },
    "qemu-orq": {
      "created_ts": 1781458875,
      "enabled": true,
      "endpoint": "192.168.100.10:51820",
      "ip": "10.20.30.5",
      "keepalive": 25,
      "last_heartbeat": 1781483408,
      "metadata": {
        "owner": "qemu-orq"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=",
      "status": {
        "endpoint": "192.168.100.10:51820",
        "nat_type": "symmetric",
        "ts": 1781483407,
        "wg": "interface: wg0\n  public key: LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 2 minutes, 6 seconds ago\n  transfer: 276 B received, 988 B sent\n  persistent keepalive: every 25 seconds\n"
      },
      "tags": [
        "qemu",
        "lab"
      ],
      "user_id": "qemu-orq"
    },
    "qemu-pa": {
      "created_ts": 1781458884,
      "enabled": true,
      "endpoint": "192.168.100.20:51820",
      "ip": "10.20.30.6",
      "keepalive": 25,
      "last_heartbeat": 1781483410,
      "metadata": {
        "owner": "qemu-pa"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=",
      "status": {
        "endpoint": "192.168.100.20:51820",
        "nat_type": "symmetric",
        "ts": 1781483408,
        "wg": "interface: wg0\n  public key: c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 33 seconds ago\n  transfer: 234.17 KiB received, 8.70 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "tags": [
        "qemu",
        "lab"
      ],
      "user_id": "qemu-pa"
    },
    "qemu-pb": {
      "created_ts": 1781458893,
      "enabled": true,
      "endpoint": "192.168.100.30:51820",
      "ip": "10.20.30.7",
      "keepalive": 25,
      "last_heartbeat": 1781483411,
      "metadata": {
        "owner": "qemu-pb"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=",
      "status": {
        "endpoint": "192.168.100.30:51820",
        "nat_type": "symmetric",
        "ts": 1781483409,
        "wg": "interface: wg0\n  public key: h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 28 seconds ago\n  transfer: 8.49 MiB received, 236.20 KiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "tags": [
        "qemu",
        "lab"
      ],
      "user_id": "qemu-pb"
    }
  },
  "qemu_included": true,
  "report_path": "/home/natalia/Documents/Releasev4/docs/reporte-rendimiento-conectividad.md",
  "timestamp": "2026-06-14 18:22:08 CST",
  "topology_results": [
    {
      "mesh_view": null,
      "qemu_pings": [
        {
          "avg_ms": null,
          "dst": "qemu-pb",
          "ok": true,
          "src": "qemu-pa"
        },
        {
          "avg_ms": 181.932,
          "dst": "qemu-pa",
          "ok": true,
          "src": "qemu-pb"
        }
      ],
      "qemu_throughput": [
        {
          "http": 200,
          "mbps": 4.58,
          "peer_id": "qemu-pb",
          "size_download": 4194304,
          "speed_download": 571934,
          "time_total": 7.333538
        }
      ],
      "real_pings": [
        {
          "avg_ms": 4.74,
          "dst": "10.20.30.2",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 2.863,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 2.841,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.2"
        }
      ],
      "real_throughput": [
        {
          "http": 200,
          "mbps": 5.55,
          "peer_id": "peer-122-8-179-57",
          "size_download": 8388608,
          "speed_download": 693413,
          "time_total": 12.09756
        },
        {
          "http": 200,
          "mbps": 5.05,
          "peer_id": "peer-46-250-162-141",
          "size_download": 8388608,
          "speed_download": 631339,
          "time_total": 13.287877
        }
      ],
      "topology": "hub-spoke"
    },
    {
      "mesh_view": [
        {
          "alive": true,
          "endpoint": "122.8.179.57:51820",
          "last_seen_ts": 1781483272,
          "peer_id": "peer-122-8-179-57",
          "public_key": "FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=",
          "tunnel_ip": "10.20.30.2"
        },
        {
          "alive": true,
          "endpoint": "46.250.162.141:51820",
          "last_seen_ts": 1781483273,
          "peer_id": "peer-46-250-162-141",
          "public_key": "0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=",
          "tunnel_ip": "10.20.30.3"
        },
        {
          "alive": true,
          "endpoint": "46.250.168.185:51820",
          "last_seen_ts": 1781483272,
          "peer_id": "peer-46-250-168-185",
          "public_key": "ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=",
          "tunnel_ip": "10.20.30.4"
        },
        {
          "alive": true,
          "endpoint": "192.168.100.10:51820",
          "last_seen_ts": 1781483277,
          "peer_id": "qemu-orq",
          "public_key": "LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=",
          "tunnel_ip": "10.20.30.5"
        },
        {
          "alive": true,
          "endpoint": "192.168.100.20:51820",
          "last_seen_ts": 1781483278,
          "peer_id": "qemu-pa",
          "public_key": "c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=",
          "tunnel_ip": "10.20.30.6"
        },
        {
          "alive": true,
          "endpoint": "192.168.100.30:51820",
          "last_seen_ts": 1781483278,
          "peer_id": "qemu-pb",
          "public_key": "h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=",
          "tunnel_ip": "10.20.30.7"
        }
      ],
      "qemu_pings": [
        {
          "avg_ms": 3.092,
          "dst": "qemu-pb",
          "ok": true,
          "src": "qemu-pa"
        },
        {
          "avg_ms": 2.582,
          "dst": "qemu-pa",
          "ok": true,
          "src": "qemu-pb"
        }
      ],
      "qemu_throughput": [
        {
          "http": 200,
          "mbps": 35.09,
          "peer_id": "qemu-pb",
          "size_download": 4194304,
          "speed_download": 4386391,
          "time_total": 0.956208
        }
      ],
      "real_pings": [
        {
          "avg_ms": 2.357,
          "dst": "10.20.30.2",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 1.467,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 1.479,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.2"
        }
      ],
      "real_throughput": [
        {
          "http": 200,
          "mbps": 14.24,
          "peer_id": "peer-122-8-179-57",
          "size_download": 8388608,
          "speed_download": 1779565,
          "time_total": 4.713853
        },
        {
          "http": 200,
          "mbps": 5.61,
          "peer_id": "peer-46-250-162-141",
          "size_download": 8388608,
          "speed_download": 701036,
          "time_total": 11.966965
        }
      ],
      "topology": "mesh"
    },
    {
      "mesh_view": {
        "direct": [],
        "relay_cidr": "10.20.30.0/24",
        "relay_only": [
          {
            "alive": true,
            "endpoint": "122.8.179.57:51820",
            "last_seen_ts": 1781483352,
            "nat_type": "symmetric",
            "peer_id": "peer-122-8-179-57",
            "public_key": "FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.2"
          },
          {
            "alive": true,
            "endpoint": "46.250.162.141:51820",
            "last_seen_ts": 1781483353,
            "nat_type": "symmetric",
            "peer_id": "peer-46-250-162-141",
            "public_key": "0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.3"
          },
          {
            "alive": true,
            "endpoint": "46.250.168.185:51820",
            "last_seen_ts": 1781483352,
            "nat_type": "symmetric",
            "peer_id": "peer-46-250-168-185",
            "public_key": "ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.4"
          },
          {
            "alive": true,
            "endpoint": "192.168.100.10:51820",
            "last_seen_ts": 1781483357,
            "nat_type": "symmetric",
            "peer_id": "qemu-orq",
            "public_key": "LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.5"
          },
          {
            "alive": true,
            "endpoint": "192.168.100.20:51820",
            "last_seen_ts": 1781483360,
            "nat_type": "symmetric",
            "peer_id": "qemu-pa",
            "public_key": "c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.6"
          },
          {
            "alive": true,
            "endpoint": "192.168.100.30:51820",
            "last_seen_ts": 1781483361,
            "nat_type": "symmetric",
            "peer_id": "qemu-pb",
            "public_key": "h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.7"
          }
        ]
      },
      "qemu_pings": [
        {
          "avg_ms": null,
          "dst": "qemu-pb",
          "ok": true,
          "src": "qemu-pa"
        },
        {
          "avg_ms": 218.648,
          "dst": "qemu-pa",
          "ok": true,
          "src": "qemu-pb"
        }
      ],
      "qemu_throughput": [
        {
          "http": 200,
          "mbps": 4.4,
          "peer_id": "qemu-pb",
          "size_download": 4194304,
          "speed_download": 549822,
          "time_total": 7.628475
        }
      ],
      "real_pings": [
        {
          "avg_ms": 4.78,
          "dst": "10.20.30.2",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 2.954,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 2.888,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.2"
        }
      ],
      "real_throughput": [
        {
          "http": 200,
          "mbps": 5.75,
          "peer_id": "peer-122-8-179-57",
          "size_download": 8388608,
          "speed_download": 718909,
          "time_total": 11.668525
        },
        {
          "http": 200,
          "mbps": 5.35,
          "peer_id": "peer-46-250-162-141",
          "size_download": 8388608,
          "speed_download": 668202,
          "time_total": 12.554207
        }
      ],
      "topology": "hub-mesh"
    }
  ]
}
```

---
## 2026-06-14 20:00:46 CST

- reporte actual: `/home/natalia/Documents/Releasev4/docs/reporte-rendimiento-conectividad.md`
- estado del orquestador: `healthy`
- peers visibles: `6`
- qemu incluido: `sí`

### hub-spoke

- conectividad real OK: `3/3`
- RTT real promedio agregado: `3.550 ms`
- throughput real promedio agregado: `5.02 Mbps`
- conectividad QEMU OK: `1/2`
- RTT QEMU promedio agregado: `197.681 ms`
- throughput QEMU promedio agregado: `4.30 Mbps`

### mesh

- conectividad real OK: `3/3`
- RTT real promedio agregado: `1.752 ms`
- throughput real promedio agregado: `6.82 Mbps`
- conectividad QEMU OK: `2/2`
- RTT QEMU promedio agregado: `2.670 ms`
- throughput QEMU promedio agregado: `33.53 Mbps`
- incluye vista del orquestador para topología con peers mesh

### hub-mesh

- conectividad real OK: `3/3`
- RTT real promedio agregado: `3.568 ms`
- throughput real promedio agregado: `5.43 Mbps`
- conectividad QEMU OK: `1/2`
- RTT QEMU promedio agregado: `192.208 ms`
- throughput QEMU promedio agregado: `4.59 Mbps`
- incluye vista del orquestador para topología con peers mesh

### JSON crudo

```json
{
  "health": {
    "config_version": 284,
    "hub_reachable": true,
    "networks_count": 1,
    "peers_count": 6,
    "status": "healthy"
  },
  "peers": {
    "peer-122-8-179-57": {
      "created_ts": 1781360083,
      "enabled": true,
      "endpoint": "122.8.179.57:51820",
      "ip": "10.20.30.2",
      "keepalive": 25,
      "last_heartbeat": 1781489348,
      "metadata": {
        "owner": "peer-122-8-179-57"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=",
      "status": {
        "endpoint": "122.8.179.57:51820",
        "nat_type": "symmetric",
        "ts": 1781489348,
        "wg": "interface: wg0\n  public key: FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 1 minute, 44 seconds ago\n  transfer: 187.23 MiB received, 4.87 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "user_id": "peer-122-8-179-57"
    },
    "peer-46-250-162-141": {
      "created_ts": 1781360083,
      "enabled": true,
      "endpoint": "46.250.162.141:51820",
      "ip": "10.20.30.3",
      "keepalive": 25,
      "last_heartbeat": 1781489349,
      "metadata": {
        "owner": "peer-46-250-162-141"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=",
      "status": {
        "endpoint": "46.250.162.141:51820",
        "nat_type": "symmetric",
        "ts": 1781489349,
        "wg": "interface: wg0\n  public key: 0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 2 minutes, 11 seconds ago\n  transfer: 175.35 MiB received, 6.10 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "user_id": "peer-46-250-162-141"
    },
    "peer-46-250-168-185": {
      "created_ts": 1781360082,
      "enabled": true,
      "endpoint": "46.250.168.185:51820",
      "ip": "10.20.30.4",
      "keepalive": 25,
      "last_heartbeat": 1781489347,
      "metadata": {
        "owner": "peer-46-250-168-185"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=",
      "status": {
        "endpoint": "46.250.168.185:51820",
        "nat_type": "symmetric",
        "ts": 1781489347,
        "wg": "interface: wg0\n  public key: ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 1 second ago\n  transfer: 10.31 MiB received, 438.05 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "user_id": "peer-46-250-168-185"
    },
    "qemu-orq": {
      "created_ts": 1781458875,
      "enabled": true,
      "endpoint": "192.168.100.10:51820",
      "ip": "10.20.30.5",
      "keepalive": 25,
      "last_heartbeat": 1781489351,
      "metadata": {
        "owner": "qemu-orq"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=",
      "status": {
        "endpoint": "192.168.100.10:51820",
        "nat_type": "symmetric",
        "ts": 1781489350,
        "wg": "interface: wg0\n  public key: LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 21 seconds ago\n  transfer: 368 B received, 1.17 KiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "tags": [
        "qemu",
        "lab"
      ],
      "user_id": "qemu-orq"
    },
    "qemu-pa": {
      "created_ts": 1781458884,
      "enabled": true,
      "endpoint": "192.168.100.20:51820",
      "ip": "10.20.30.6",
      "keepalive": 25,
      "last_heartbeat": 1781489353,
      "metadata": {
        "owner": "qemu-pa"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=",
      "status": {
        "endpoint": "192.168.100.20:51820",
        "nat_type": "symmetric",
        "ts": 1781489351,
        "wg": "interface: wg0\n  public key: c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 41 seconds ago\n  transfer: 226.62 KiB received, 9.10 MiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "tags": [
        "qemu",
        "lab"
      ],
      "user_id": "qemu-pa"
    },
    "qemu-pb": {
      "created_ts": 1781458893,
      "enabled": true,
      "endpoint": "192.168.100.30:51820",
      "ip": "10.20.30.7",
      "keepalive": 25,
      "last_heartbeat": 1781489354,
      "metadata": {
        "owner": "qemu-pb"
      },
      "nat_type": "symmetric",
      "networks": [
        "default"
      ],
      "public_key": "h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=",
      "status": {
        "endpoint": "192.168.100.30:51820",
        "nat_type": "symmetric",
        "ts": 1781489352,
        "wg": "interface: wg0\n  public key: h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=\n  private key: (hidden)\n  listening port: 51820\n\npeer: 8XZVYPb+WXPiX9Co9xlvOurAO5NztOMclIm06764B24=\n  endpoint: 101.44.24.91:51820\n  allowed ips: 10.20.30.0/24\n  latest handshake: 42 seconds ago\n  transfer: 8.54 MiB received, 238.59 KiB sent\n  persistent keepalive: every 25 seconds\n"
      },
      "tags": [
        "qemu",
        "lab"
      ],
      "user_id": "qemu-pb"
    }
  },
  "qemu_included": true,
  "report_path": "/home/natalia/Documents/Releasev4/docs/reporte-rendimiento-conectividad.md",
  "timestamp": "2026-06-14 20:00:46 CST",
  "topology_results": [
    {
      "mesh_view": null,
      "qemu_pings": [
        {
          "avg_ms": null,
          "dst": "qemu-pb",
          "ok": false,
          "src": "qemu-pa"
        },
        {
          "avg_ms": 197.681,
          "dst": "qemu-pa",
          "ok": true,
          "src": "qemu-pb"
        }
      ],
      "qemu_throughput": [
        {
          "http": 200,
          "mbps": 4.3,
          "peer_id": "qemu-pb",
          "size_download": 4194304,
          "speed_download": 537301,
          "time_total": 7.80624
        }
      ],
      "real_pings": [
        {
          "avg_ms": 4.799,
          "dst": "10.20.30.2",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 2.946,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 2.906,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.2"
        }
      ],
      "real_throughput": [
        {
          "http": 200,
          "mbps": 5.19,
          "peer_id": "peer-122-8-179-57",
          "size_download": 8388608,
          "speed_download": 648423,
          "time_total": 12.936918
        },
        {
          "http": 200,
          "mbps": 4.85,
          "peer_id": "peer-46-250-162-141",
          "size_download": 8388608,
          "speed_download": 606551,
          "time_total": 13.830612
        }
      ],
      "topology": "hub-spoke"
    },
    {
      "mesh_view": [
        {
          "alive": true,
          "endpoint": "122.8.179.57:51820",
          "last_seen_ts": 1781489201,
          "peer_id": "peer-122-8-179-57",
          "public_key": "FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=",
          "tunnel_ip": "10.20.30.2"
        },
        {
          "alive": true,
          "endpoint": "46.250.162.141:51820",
          "last_seen_ts": 1781489202,
          "peer_id": "peer-46-250-162-141",
          "public_key": "0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=",
          "tunnel_ip": "10.20.30.3"
        },
        {
          "alive": true,
          "endpoint": "46.250.168.185:51820",
          "last_seen_ts": 1781489200,
          "peer_id": "peer-46-250-168-185",
          "public_key": "ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=",
          "tunnel_ip": "10.20.30.4"
        },
        {
          "alive": true,
          "endpoint": "192.168.100.10:51820",
          "last_seen_ts": 1781489206,
          "peer_id": "qemu-orq",
          "public_key": "LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=",
          "tunnel_ip": "10.20.30.5"
        },
        {
          "alive": true,
          "endpoint": "192.168.100.20:51820",
          "last_seen_ts": 1781489207,
          "peer_id": "qemu-pa",
          "public_key": "c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=",
          "tunnel_ip": "10.20.30.6"
        },
        {
          "alive": true,
          "endpoint": "192.168.100.30:51820",
          "last_seen_ts": 1781489208,
          "peer_id": "qemu-pb",
          "public_key": "h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=",
          "tunnel_ip": "10.20.30.7"
        }
      ],
      "qemu_pings": [
        {
          "avg_ms": 2.854,
          "dst": "qemu-pb",
          "ok": true,
          "src": "qemu-pa"
        },
        {
          "avg_ms": 2.486,
          "dst": "qemu-pa",
          "ok": true,
          "src": "qemu-pb"
        }
      ],
      "qemu_throughput": [
        {
          "http": 200,
          "mbps": 33.53,
          "peer_id": "qemu-pb",
          "size_download": 4194304,
          "speed_download": 4191730,
          "time_total": 1.000614
        }
      ],
      "real_pings": [
        {
          "avg_ms": 2.36,
          "dst": "10.20.30.2",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 1.445,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 1.45,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.2"
        }
      ],
      "real_throughput": [
        {
          "http": 200,
          "mbps": 8.31,
          "peer_id": "peer-122-8-179-57",
          "size_download": 8388608,
          "speed_download": 1038169,
          "time_total": 8.080192
        },
        {
          "http": 200,
          "mbps": 5.33,
          "peer_id": "peer-46-250-162-141",
          "size_download": 8388608,
          "speed_download": 665815,
          "time_total": 12.599661
        }
      ],
      "topology": "mesh"
    },
    {
      "mesh_view": {
        "direct": [],
        "relay_cidr": "10.20.30.0/24",
        "relay_only": [
          {
            "alive": true,
            "endpoint": "122.8.179.57:51820",
            "last_seen_ts": 1781489294,
            "nat_type": "symmetric",
            "peer_id": "peer-122-8-179-57",
            "public_key": "FUCsJR2z0mvnAumuMOUxyqLXNBzkfogxFfMGjDyx6QU=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.2"
          },
          {
            "alive": true,
            "endpoint": "46.250.162.141:51820",
            "last_seen_ts": 1781489296,
            "nat_type": "symmetric",
            "peer_id": "peer-46-250-162-141",
            "public_key": "0f+9O+wSiZPXh16H6yRbMImwBUD5L9XQBtlgVJpypxk=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.3"
          },
          {
            "alive": true,
            "endpoint": "46.250.168.185:51820",
            "last_seen_ts": 1781489292,
            "nat_type": "symmetric",
            "peer_id": "peer-46-250-168-185",
            "public_key": "ruEBCcJqLoFdh8gsVW4VmISdPoirl58cR323mSvR3Qw=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.4"
          },
          {
            "alive": true,
            "endpoint": "192.168.100.10:51820",
            "last_seen_ts": 1781489301,
            "nat_type": "symmetric",
            "peer_id": "qemu-orq",
            "public_key": "LKirLcl+deTt8Yujq9kiuRIa95elt73XUcGaTj3cKy4=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.5"
          },
          {
            "alive": true,
            "endpoint": "192.168.100.20:51820",
            "last_seen_ts": 1781489301,
            "nat_type": "symmetric",
            "peer_id": "qemu-pa",
            "public_key": "c5IBnmnLFt1ggtk9PgKONhS8BVAST07Q1hvh5an+4EI=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.6"
          },
          {
            "alive": true,
            "endpoint": "192.168.100.30:51820",
            "last_seen_ts": 1781489302,
            "nat_type": "symmetric",
            "peer_id": "qemu-pb",
            "public_key": "h3F9K7q00/r6CmO7syTYU0cNjoUnCkoL+dnd15MeT0A=",
            "relay_mode": "auto",
            "tunnel_ip": "10.20.30.7"
          }
        ]
      },
      "qemu_pings": [
        {
          "avg_ms": 190.4,
          "dst": "qemu-pb",
          "ok": false,
          "src": "qemu-pa"
        },
        {
          "avg_ms": 194.016,
          "dst": "qemu-pa",
          "ok": true,
          "src": "qemu-pb"
        }
      ],
      "qemu_throughput": [
        {
          "http": 200,
          "mbps": 4.59,
          "peer_id": "qemu-pb",
          "size_download": 4194304,
          "speed_download": 573784,
          "time_total": 7.309895
        }
      ],
      "real_pings": [
        {
          "avg_ms": 4.833,
          "dst": "10.20.30.2",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 2.946,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.4"
        },
        {
          "avg_ms": 2.925,
          "dst": "10.20.30.3",
          "ok": true,
          "src": "10.20.30.2"
        }
      ],
      "real_throughput": [
        {
          "http": 200,
          "mbps": 5.57,
          "peer_id": "peer-122-8-179-57",
          "size_download": 8388608,
          "speed_download": 695691,
          "time_total": 12.057937
        },
        {
          "http": 200,
          "mbps": 5.28,
          "peer_id": "peer-46-250-162-141",
          "size_download": 8388608,
          "speed_download": 659844,
          "time_total": 12.713114
        }
      ],
      "topology": "hub-mesh"
    }
  ]
}
```

---
