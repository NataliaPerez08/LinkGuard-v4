#!/usr/bin/env python3
"""Genera reporte HTML para topologia hub-spoke (AWS + VM + RPi5 + QEMU) con multiusuario CLI."""

import sys

from report_common import run_report

if __name__ == "__main__":
    sys.exit(run_report(
        "hub-spoke",
        title="Reporte Hub-Spoke AWS Multiusuario CLI — LinkGuard v4 (AWS + VM + RPi5 + 1 QEMU)",
        report_subdir="hub-spoke",
        file_prefix="reporte-aws-hubspoke-1qemu",
        default_topology="hub-spoke",
        description="Genera reporte HTML para topologia hub-spoke (3 nubes AWS + 1 VM + 1 RPi5 + 1 QEMU)",
    ))
