#!/usr/bin/env python3
"""Genera reporte HTML con los resultados de la suite de tests de LinkGuard v4.

Ejecuta las suites de pytest (orchestrator, peer y tests nuevos de CLI) con
--junit-xml, parsea los resultados y renderiza un reporte HTML autocontenido.

Uso:
    python3 scripts/generate-test-report.py
    python3 scripts/generate-test-report.py --output /tmp/reporte.html
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "docs" / "reports" / "test-results"

# Suites a ejecutar: (id, etiqueta, ruta relativa, es_nueva_cli)
SUITES = [
    ("orch", "Orchestrator (full suite)", "orchestrator-install-v2/tests", False),
    ("peer", "Peer (full suite)", "peer-install-v2/tests", False),
    ("cli", "Tests nuevos de CLI", None, True),
]
CLI_FILES = [
    "orchestrator-install-v2/tests/test_orch_cli.py",
    "peer-install-v2/tests/test_wg_auto_cli.py",
]


@dataclass
class TestCase:
    name: str
    classname: str
    status: str  # passed | failed | error | skipped
    time: float
    failure_msg: str = ""


@dataclass
class SuiteResult:
    suite_id: str
    label: str
    is_new_cli: bool
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration: float = 0.0
    cases: list[TestCase] = field(default_factory=list)
    run_error: str = ""


def log(msg: str) -> None:
    print(f"[reporte] {msg}", flush=True)


def run_suite(suite_id: str, label: str, target: str | None, is_new_cli: bool) -> SuiteResult:
    res = SuiteResult(suite_id=suite_id, label=label, is_new_cli=is_new_cli)
    junit_path = REPORT_DIR / f"junit-{suite_id}.xml"
    junit_path.parent.mkdir(parents=True, exist_ok=True)

    if is_new_cli:
        argv = [sys.executable, "-m", "pytest", *CLI_FILES,
                f"--junit-xml={junit_path}", "-q", "--tb=line", "--no-header"]
    else:
        argv = [sys.executable, "-m", "pytest", target,
                f"--junit-xml={junit_path}", "-q", "--tb=line", "--no-header"]

    log(f"Ejecutando {label} ...")
    proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    log(f"  rc={proc.returncode}  stdout_lines={len(proc.stdout.splitlines())}")

    if not junit_path.exists():
        res.run_error = proc.stderr.strip() or proc.stdout.strip() or "sin salida"
        return res

    try:
        tree = ET.parse(junit_path)
    except ET.ParseError as e:
        res.run_error = f"XML inválido: {e}"
        return res

    root = tree.getroot()
    # testsuites -> testsuite (pytest siempre genera una testsuite)
    ts = root.find("testsuite")
    if ts is None:
        res.run_error = "no se encontró <testsuite>"
        return res

    res.total = int(ts.get("tests", 0))
    res.failed = int(ts.get("failures", 0))
    res.errors = int(ts.get("errors", 0))
    res.skipped = int(ts.get("skipped", 0))
    res.passed = res.total - res.failed - res.errors - res.skipped
    res.duration = float(ts.get("time", 0.0))

    for tc in ts.findall("testcase"):
        name = tc.get("name", "?")
        classname = tc.get("classname", "?")
        t = float(tc.get("time", 0.0))
        fail = tc.find("failure")
        err = tc.find("error")
        skip = tc.find("skipped")
        if fail is not None:
            status = "failed"
            msg = fail.get("message", "") or (fail.text or "").strip()
        elif err is not None:
            status = "error"
            msg = err.get("message", "") or (err.text or "").strip()
        elif skip is not None:
            status = "skipped"
            msg = skip.get("message", "") or (skip.text or "").strip()
        else:
            status = "passed"
            msg = ""
        res.cases.append(TestCase(name=name, classname=classname, status=status,
                                  time=t, failure_msg=msg))
    return res


def status_badge(status: str) -> str:
    cls = {"passed": "ok", "failed": "fail", "error": "fail", "skipped": "warn"}.get(status, "")
    label = {"passed": "PASS", "failed": "FAIL", "error": "ERROR", "skipped": "SKIP"}.get(status, status.upper())
    return f'<span class="{cls}">{label}</span>'


def render_html(timestamp: str, results: list[SuiteResult]) -> str:
    total_all = sum(r.total for r in results)
    passed_all = sum(r.passed for r in results)
    failed_all = sum(r.failed for r in results)
    errors_all = sum(r.errors for r in results)
    skipped_all = sum(r.skipped for r in results)
    dur_all = sum(r.duration for r in results)
    all_ok = failed_all == 0 and errors_all == 0

    # Tabla resumen
    summary_rows = ""
    for r in results:
        cls = "summary-ok" if (r.failed == 0 and r.errors == 0 and not r.run_error) else "summary-fail"
        badge = f'<span class="tag-qemu">NUEVO</span>' if r.is_new_cli else ""
        err_col = f'<td class="fail">{r.errors}</td>' if r.errors else "<td>0</td>"
        if r.run_error:
            err_col = f'<td class="fail" colspan="1">RUN ERROR</td>'
        summary_rows += (
            f"<tr>"
            f"<td>{r.label} {badge}</td>"
            f"<td>{r.total}</td>"
            f'<td class="ok">{r.passed}</td>'
            f'<td class="{"fail" if r.failed else ""}">{r.failed}</td>'
            f"{err_col}"
            f"<td>{r.skipped}</td>"
            f"<td>{r.duration:.2f}s</td>"
            f'<td class="{cls}">{"OK" if (r.failed == 0 and r.errors == 0 and not r.run_error) else "FAIL"}</td>'
            f"</tr>"
        )

    # Detalle por suite (colapsable)
    detail_sections = ""
    for r in results:
        if not r.cases and r.run_error:
            detail_sections += (
                f'<div class="section">'
                f"<h3>{r.label}</h3>"
                f'<pre class="fail">{r.run_error}</pre>'
                f"</div>"
            )
            continue
        if not r.cases:
            continue
        rows = ""
        # ordenar: fallos primero, luego pasados
        ordered = sorted(r.cases, key=lambda c: {"failed": 0, "error": 1, "skipped": 2, "passed": 3}.get(c.status, 9))
        for c in ordered:
            short_name = c.name.replace("test_", "")
            rows += (
                f"<tr>"
                f"<td>{c.classname}</td>"
                f"<td>{short_name}</td>"
                f"<td>{status_badge(c.status)}</td>"
                f"<td>{c.time:.3f}s</td>"
                f"</tr>"
            )
            if c.failure_msg:
                msg = c.failure_msg[:500].replace("<", "&lt;").replace(">", "&gt;")
                rows += (
                    f'<tr class="failrow"><td colspan="4"><pre>{msg}</pre></td></tr>'
                )
        detail_sections += (
            f'<div class="section">'
            f"<h3>{r.label} "
            f'<span class="meta">({r.passed}/{r.total} pass, {r.duration:.2f}s)</span></h3>'
            f"<table><tr><th>Clase</th><th>Test</th><th>Estado</th><th>Tiempo</th></tr>"
            f"{rows}</table>"
            f"</div>"
        )

    estado_global = "TODOS LOS TESTS PASAN" if all_ok else f"HAY {failed_all + errors_all} FALLO(S)"
    estado_cls = "summary-ok" if all_ok else "summary-fail"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reporte de Tests — LinkGuard v4 — {timestamp}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #0d1117; color: #c9d1d9; padding: 20px; max-width: 1200px; margin: auto; }}
  h1 {{ color: #58a6ff; font-size: 1.8em; margin-bottom: 5px; }}
  h2 {{ color: #79c0ff; font-size: 1.4em; margin: 25px 0 15px; border-bottom: 1px solid #21262d; padding-bottom: 8px; }}
  h3 {{ color: #c9d1d9; font-size: 1.1em; margin: 20px 0 10px; }}
  .meta {{ color: #8b949e; font-size: 0.9em; margin-bottom: 20px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 0.9em; }}
  th, td {{ border: 1px solid #30363d; padding: 6px 10px; text-align: left; }}
  th {{ background: #161b22; font-weight: 600; color: #79c0ff; }}
  td {{ background: #0d1117; }}
  tr:nth-child(even) td {{ background: #161b22; }}
  .ok {{ color: #3fb950; font-weight: bold; }}
  .warn {{ color: #d29922; font-weight: bold; }}
  .fail {{ color: #f85149; font-weight: bold; }}
  .tag-qemu {{ background: #23863633; color: #3fb950; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }}
  .nav {{ background: #161b22; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; }}
  .nav a {{ color: #58a6ff; text-decoration: none; margin-right: 15px; }}
  .section {{ background: #161b22; border-radius: 8px; padding: 16px; margin-bottom: 20px; border: 1px solid #30363d; }}
  .summary-ok {{ color: #3fb950; font-weight: bold; }}
  .summary-fail {{ color: #f85149; font-weight: bold; }}
  .legend {{ font-size: 0.85em; color: #8b949e; margin-top: 10px; }}
  pre {{ background: #0d1117; padding: 10px; border-radius: 6px; overflow-x: auto; font-size: 0.82em; color: #f85149; border: 1px solid #30363d; white-space: pre-wrap; }}
  .failrow td {{ background: #1a0e0e !important; }}
  .big {{ font-size: 1.3em; font-weight: bold; }}
  details summary {{ cursor: pointer; color: #58a6ff; padding: 8px 0; }}
</style>
</head>
<body>
<h1>Reporte de Tests — LinkGuard v4</h1>
<div class="meta">Generado: {timestamp} · suites: {len(results)} · duración total: {dur_all:.2f}s</div>

<div class="nav">
  <a href="#resumen">Resumen</a>
  <a href="#detalle">Detalle por suite</a>
  <a href="#trabajo">Trabajo realizado</a>
</div>

<div class="section" id="resumen">
  <h2>Resumen general</h2>
  <p class="big {estado_cls}">{estado_global}</p>
  <table>
    <tr><th>Suite</th><th>Total</th><th>PASS</th><th>FAIL</th><th>ERROR</th><th>SKIP</th><th>Duración</th><th>Estado</th></tr>
    {summary_rows}
    <tr style="border-top: 2px solid #30363d;">
      <td><strong>TOTAL</strong></td>
      <td><strong>{total_all}</strong></td>
      <td class="ok"><strong>{passed_all}</strong></td>
      <td class="{'fail' if failed_all else ''}"><strong>{failed_all}</strong></td>
      <td class="{'fail' if errors_all else ''}"><strong>{errors_all}</strong></td>
      <td><strong>{skipped_all}</strong></td>
      <td><strong>{dur_all:.2f}s</strong></td>
      <td class="{estado_cls}"><strong>{"OK" if all_ok else "FAIL"}</strong></td>
    </tr>
  </table>
  <div class="legend">PASS = passed · FAIL = failures · ERROR = errors de colección/ejecución · SKIP = skipped</div>
</div>

<h2 id="detalle">Detalle por suite</h2>
{detail_sections}

<div class="section" id="trabajo">
  <h2>Trabajo realizado en esta sesión</h2>
  <h3>Tests nuevos de CLI (sin modificar tests previos)</h3>
  <ul>
    <li><code>orchestrator-install-v2/tests/test_orch_cli.py</code> — 47 tests del front-end <code>orch-cli.py</code> (mock de ServerProxy, verifica mapeo subcomando→método RPC, defaults, contrato argparse de <code>--admin-token</code>/<code>--token</code>).</li>
    <li><code>peer-install-v2/tests/test_wg_auto_cli.py</code> — 21 tests del front-end <code>wg-auto-cli.py</code> (peer ops, networks, advertised, rotate-key, mesh-status, precedencia JWT).</li>
  </ul>
  <h3>Fixes a tests preexistentes (código de producción intacto)</h3>
  <ul>
    <li><code>test_auto_approve.py</code> — aserción <code>10.0.0.1</code> → <code>10.0.0.2</code> (la IP <code>.1</code> está reservada para el HUB de WireGuard en <code>network_alloc._allocate_ip_in_network</code>).</li>
    <li><code>test_config_gen.py</code> — test dividido en <code>test_mesh_peer_not_alive_still_includes_endpoint</code> y <code>test_mesh_peer_no_endpoint_omitted</code>: el <code>Endpoint</code> se incluye siempre que exista, independientemente de <code>alive</code> (fix intencional de <code>config_gen.py</code> documentado en AGENTS.md).</li>
    <li><code>test_peer_config.py</code> — añadido <code>importlib.reload(config)</code> en <code>test_orch_url_default</code> para releer el env limpio del conftest y evitar contaminación desde <code>test_integration_mixed_nat_topologies.py</code>.</li>
  </ul>
</div>

</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera reporte HTML de la suite de tests de LinkGuard v4")
    parser.add_argument("--output", default=None, help="Ruta de salida (default: docs/reports/test-results/<date>/reporte-tests-<ts>.html)")
    args = parser.parse_args()

    now = datetime.now(timezone.utc).astimezone()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S %Z")
    ts_slug = now.strftime("%Y%m%d_%H%M%S")

    if args.output:
        output_path = Path(args.output)
    else:
        date_dir = now.strftime("%Y-%m-%d")
        output_path = REPORT_DIR / date_dir / f"reporte-tests-{ts_slug}.html"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Sanity: pytest disponible
    if shutil.which("pytest") is None and not Path(sys.executable).exists():
        log("ERROR: pytest no disponible")
        return 1

    results: list[SuiteResult] = []
    for suite_id, label, target, is_new_cli in SUITES:
        results.append(run_suite(suite_id, label, target, is_new_cli))

    log("Generando HTML ...")
    html = render_html(timestamp, results)
    output_path.write_text(html, encoding="utf-8")

    # Copia latest.html
    latest = output_path.parent / "latest.html"
    shutil.copy2(output_path, latest)

    # Resumen por consola
    total_all = sum(r.total for r in results)
    passed_all = sum(r.passed for r in results)
    failed_all = sum(r.failed for r in results)
    errors_all = sum(r.errors for r in results)
    log(f"Reporte: {output_path}")
    log(f"Latest:  {latest}")
    log("-" * 50)
    for r in results:
        estado = "OK" if (r.failed == 0 and r.errors == 0 and not r.run_error) else "FAIL"
        log(f"  {r.label:<28} {r.passed}/{r.total} pass, {r.failed} fail, {r.errors} err  [{estado}]")
    log("-" * 50)
    log(f"  TOTAL: {passed_all}/{total_all} pass, {failed_all} fail, {errors_all} error")
    return 0 if (failed_all == 0 and errors_all == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
