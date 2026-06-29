#!/usr/bin/env python3
"""Genera reporte HTML para topologia mesh (AWS + VM + RPi5 + QEMU) con DOS tenants.

Distribucion de tenants:
  - tenant-a: 3 peers cloud AWS (119, 76, 143)
  - tenant-b: VM40 + RPi5 + QEMU peer01

Verifica conectividad cross-tenant en topologia mesh (P2P entre nubes, relay via hub para NAT).
"""

import sys

from report_common_2tenants import run_report

if __name__ == "__main__":
    sys.exit(run_report(
        "mesh",
        title="Reporte Mesh AWS Multiusuario CLI — 2 Tenants — LinkGuard v4 (AWS + VM + RPi5 + 1 QEMU)",
        report_subdir="mesh",
        file_prefix="reporte-aws-mesh-1qemu-2tenants",
        default_topology="mesh",
        description="Genera reporte HTML para topologia mesh con 2 tenants (3 nubes AWS tenant-a + VM + RPi5 + QEMU tenant-b)",
    ))
