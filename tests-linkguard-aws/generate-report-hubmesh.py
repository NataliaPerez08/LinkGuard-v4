#!/usr/bin/env python3
"""Genera reporte HTML para topologia hub-mesh (3 nubes AWS + 1 VM + 1 RPi5 via jump + 3 QEMU)."""

import sys

from report_common import run_report

if __name__ == "__main__":
    sys.exit(run_report(
        "hub-mesh",
        title="Reporte Hub-Mesh CLI Multiusuario \u2014 LinkGuard v2 (AWS + VM + RPi5 + QEMU)",
        report_subdir="hub-mesh",
        file_prefix="reporte-hubmesh",
        default_topology="hub-mesh",
        description="Genera reporte HTML para topologia hub-mesh (3 nubes AWS + 1 VM + 1 RPi5 + 3 QEMU)",
    ))
