#!/usr/bin/env python3
"""Genera reporte HTML para topologia hub-spoke (3 nubes AWS + 1 VM + 1 RPi5 via jump + 3 QEMU)."""

import sys

from report_common import run_report

if __name__ == "__main__":
    sys.exit(run_report(
        "hub-spoke",
        title="Reporte Hub-Spoke CLI Multiusuario \u2014 LinkGuard v2 (AWS + VM + RPi5 + QEMU)",
        report_subdir="hub-spoke",
        file_prefix="reporte-hubspoke",
        default_topology="hub-spoke",
        description="Genera reporte HTML para topologia hub-spoke (3 nubes AWS + 1 VM + 1 RPi5 + 3 QEMU)",
    ))
