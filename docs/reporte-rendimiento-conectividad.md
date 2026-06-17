# Reporte de Rendimiento y Conectividad

Fecha de ejecución: `2026-06-14 20:00:46 CST`

## Alcance

- infraestructura real conectada al orquestador `101.44.24.91`
- laboratorio QEMU integrado contra el mismo orquestador real

## Estado del orquestador

- `orch.health`: `healthy`
- `hub_reachable`: `True`
- `peers_count`: `6`
- topología restaurada al final: `hub-spoke`

## Topología `hub-spoke`

### Conectividad real

| Origen | Destino | Éxito | RTT promedio |
|---|---|---|---|
| `10.20.30.4` | `10.20.30.2` | `sí` | `4.799 ms` |
| `10.20.30.4` | `10.20.30.3` | `sí` | `2.946 ms` |
| `10.20.30.2` | `10.20.30.3` | `sí` | `2.906 ms` |

### Throughput real

| Cliente | HTTP | Tamaño | Tiempo | speed_download | Aprox. Mbps |
|---|---|---|---|---|---|
| `peer-122-8-179-57` | `200` | `8388608` | `12.937 s` | `648423` | `5.19` |
| `peer-46-250-162-141` | `200` | `8388608` | `13.831 s` | `606551` | `4.85` |

### Conectividad QEMU integrada

| Origen | Destino | Éxito | RTT promedio |
|---|---|---|---|
| `qemu-pa` | `qemu-pb` | `no` | `n/d` |
| `qemu-pb` | `qemu-pa` | `sí` | `197.681 ms` |

### Throughput QEMU integrado

| Cliente | HTTP | Tamaño | Tiempo | speed_download | Aprox. Mbps |
|---|---|---|---|---|---|
| `qemu-pb` | `200` | `4194304` | `7.806 s` | `537301` | `4.30` |

## Topología `mesh`

### Conectividad real

| Origen | Destino | Éxito | RTT promedio |
|---|---|---|---|
| `10.20.30.4` | `10.20.30.2` | `sí` | `2.360 ms` |
| `10.20.30.4` | `10.20.30.3` | `sí` | `1.445 ms` |
| `10.20.30.2` | `10.20.30.3` | `sí` | `1.450 ms` |

### Throughput real

| Cliente | HTTP | Tamaño | Tiempo | speed_download | Aprox. Mbps |
|---|---|---|---|---|---|
| `peer-122-8-179-57` | `200` | `8388608` | `8.080 s` | `1038169` | `8.31` |
| `peer-46-250-162-141` | `200` | `8388608` | `12.600 s` | `665815` | `5.33` |

### Conectividad QEMU integrada

| Origen | Destino | Éxito | RTT promedio |
|---|---|---|---|
| `qemu-pa` | `qemu-pb` | `sí` | `2.854 ms` |
| `qemu-pb` | `qemu-pa` | `sí` | `2.486 ms` |

### Throughput QEMU integrado

| Cliente | HTTP | Tamaño | Tiempo | speed_download | Aprox. Mbps |
|---|---|---|---|---|---|
| `qemu-pb` | `200` | `4194304` | `1.001 s` | `4191730` | `33.53` |

### Vista del orquestador

```json
[
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
]
```

## Topología `hub-mesh`

### Conectividad real

| Origen | Destino | Éxito | RTT promedio |
|---|---|---|---|
| `10.20.30.4` | `10.20.30.2` | `sí` | `4.833 ms` |
| `10.20.30.4` | `10.20.30.3` | `sí` | `2.946 ms` |
| `10.20.30.2` | `10.20.30.3` | `sí` | `2.925 ms` |

### Throughput real

| Cliente | HTTP | Tamaño | Tiempo | speed_download | Aprox. Mbps |
|---|---|---|---|---|---|
| `peer-122-8-179-57` | `200` | `8388608` | `12.058 s` | `695691` | `5.57` |
| `peer-46-250-162-141` | `200` | `8388608` | `12.713 s` | `659844` | `5.28` |

### Conectividad QEMU integrada

| Origen | Destino | Éxito | RTT promedio |
|---|---|---|---|
| `qemu-pa` | `qemu-pb` | `no` | `190.400 ms` |
| `qemu-pb` | `qemu-pa` | `sí` | `194.016 ms` |

### Throughput QEMU integrado

| Cliente | HTTP | Tamaño | Tiempo | speed_download | Aprox. Mbps |
|---|---|---|---|---|---|
| `qemu-pb` | `200` | `4194304` | `7.310 s` | `573784` | `4.59` |

### Vista del orquestador

```json
{
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
}
```

## Peers visibles en el orquestador

- `peer-122-8-179-57` -> `10.20.30.2` endpoint `122.8.179.57:51820`
- `peer-46-250-162-141` -> `10.20.30.3` endpoint `46.250.162.141:51820`
- `peer-46-250-168-185` -> `10.20.30.4` endpoint `46.250.168.185:51820`
- `qemu-orq` -> `10.20.30.5` endpoint `192.168.100.10:51820`
- `qemu-pa` -> `10.20.30.6` endpoint `192.168.100.20:51820`
- `qemu-pb` -> `10.20.30.7` endpoint `192.168.100.30:51820`

## Comandos útiles

```bash
make qemu-status-real TESTBED_REAL_ORCH_PASS='...' 
make performance-report-all-real TESTBED_REAL_ORCH_PASS='...' 
make testbed-down
```

