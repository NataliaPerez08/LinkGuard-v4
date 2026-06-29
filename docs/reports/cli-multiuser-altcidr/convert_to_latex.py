#!/usr/bin/env python3
"""Convert HTML reports to LaTeX (.tex) files."""
import os
import re
from bs4 import BeautifulSoup

LATEX_TEMPLATE = r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[spanish]{babel}
\usepackage{xcolor}
\usepackage{longtable}
\usepackage{listings}
\usepackage{geometry}
\usepackage{hyperref}
\usepackage{booktabs}
\usepackage{colortbl}

\geometry{margin=1.2cm}
\lstset{
  basicstyle=\ttfamily\footnotesize,
  breaklines=true,
  showstringspaces=false,
  frame=single,
  backgroundcolor=\color{gray!5}
}

\definecolor{okgreen}{RGB}{63,185,80}
\definecolor{warnyellow}{RGB}{210,153,34}
\definecolor{failred}{RGB}{248,81,73}
\definecolor{headerblue}{RGB}{121,192,255}
\definecolor{tagblue}{RGB}{88,166,255}
\definecolor{taggreen}{RGB}{63,185,80}
\definecolor{tagpurple}{RGB}{210,168,255}

\newcommand{\ok}[1]{\textcolor{okgreen}{\textbf{#1}}}
\newcommand{\warn}[1]{\textcolor{warnyellow}{\textbf{#1}}}
\newcommand{\fail}[1]{\textcolor{failred}{\textbf{#1}}}
\newcommand{\partialcmd}[1]{\textcolor{warnyellow}{\textbf{#1}}}

\title{TITLE_PLACEHOLDER}
\author{LinkGuard v2}
\date{FECHA_PLACEHOLDER}

\begin{document}
\maketitle

BODY_PLACEHOLDER

\end{document}
"""


def escape_latex(text):
    """Escape special LaTeX characters."""
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\^{}",
        "\\": r"\textbackslash{}",
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    return text


def parse_table(table_element):
    """Parse HTML table to LaTeX longtable."""
    rows = table_element.find_all("tr")
    if not rows:
        return ""

    max_cols = max(len(r.find_all(["th", "td"])) for r in rows)
    col_format = "|" + "c|" * max_cols
    latex_rows = [f"\\begin{{longtable}}{{{col_format}}}\n\\hline"]

    header_th_done = True
    for i, row in enumerate(rows):
        cells = row.find_all(["th", "td"])
        cell_texts = []
        for cell in cells:
            text = cell.get_text(strip=True).replace("\n", " ").replace("—", "--")
            text = escape_latex(text)
            cell_texts.append(text)

        while len(cell_texts) < max_cols:
            cell_texts.append("")

        latex_rows.append(" & ".join(cell_texts) + r" \\ \hline")

        if i == 0 and row.find("th"):
            pass

    latex_rows.append(r"\end{longtable}")
    return "\n".join(latex_rows)


def colorize_status(cell_text):
    """Convert status text to LaTeX colored commands."""
    if "OK" in cell_text and "LENTO" not in cell_text and "PARCIAL" not in cell_text:
        return r"\ok{" + cell_text + "}"
    if "LENTO" in cell_text:
        return r"\warn{" + cell_text + "}"
    if "FALLO" in cell_text:
        return r"\fail{" + cell_text + "}"
    if "PARCIAL" in cell_text:
        return r"\partialcmd{" + cell_text + "}"
    return cell_text


def parse_matrix_table(table_element):
    """Parse connectivity matrix with colored cells."""
    rows = table_element.find_all("tr")
    if not rows:
        return ""

    max_cols = max(len(r.find_all(["th", "td"])) for r in rows)
    col_format = "|" + "p{2.2cm}|" * max_cols
    latex_rows = [
        r"\begin{longtable}{" + col_format + "}",
        r"\hline",
        r"\rowcolor{gray!15}",
    ]

    for i, row in enumerate(rows):
        cells = row.find_all(["th", "td"])
        cell_texts = []
        is_header = bool(row.find("th"))

        for cell in cells:
            text = cell.get_text(strip=True).replace("\n", " ").replace("—", "--")
            text = escape_latex(text)
            classes = cell.get("class", [])

            if "ok" in classes:
                text = r"\cellcolor{green!15}" + colorize_status(text)
            elif "warn" in classes:
                text = r"\cellcolor{yellow!15}" + colorize_status(text)
            elif "fail" in classes:
                text = r"\cellcolor{red!15}" + colorize_status(text)
            elif "partial" in classes:
                text = r"\cellcolor{orange!15}" + colorize_status(text)

            cell_texts.append(r"\footnotesize{" + text + "}")

        while len(cell_texts) < max_cols:
            cell_texts.append("")

        if is_header:
            latex_rows.insert(1, " & ".join(cell_texts) + r" \\ \hline")
            latex_rows.append(r"\endhead")
        else:
            latex_rows.append(" & ".join(cell_texts) + r" \\ \hline")

    latex_rows.append(r"\end{longtable}")
    return "\n".join(latex_rows)


def parse_pre_block(pre_element):
    """Parse <pre> to LaTeX lstlisting."""
    text = pre_element.get_text()
    if len(text) > 3000:
        text = text[:3000] + "\n... (truncado)"

    escaped = text
    escaped = escaped.replace("\\", r"\textbackslash ")
    escaped = escaped.replace("_", r"\_")
    escaped = escaped.replace("$", r"\$")
    escaped = escaped.replace("#", r"\#")
    escaped = escaped.replace("%", r"\%")
    escaped = escaped.replace("&", r"\&")
    escaped = escaped.replace("{", r"\{")
    escaped = escaped.replace("}", r"\}")
    escaped = escaped.replace("~", r"\textasciitilde ")
    escaped = escaped.replace("^", r"\^{}")

    return r"\begin{lstlisting}" + "\n" + escaped + "\n" + r"\end{lstlisting}"


def convert_html_to_latex(html_path, output_path):
    """Convert a single HTML report to LaTeX."""
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text() if title_tag else "Reporte LinkGuard"

    # Extract generation date
    gen_p = soup.find("p")
    fecha_text = gen_p.get_text() if gen_p else ""
    fecha_match = re.search(r"Generado:\s*<code>([^<]+)</code>", str(gen_p)) if gen_p else None
    fecha = fecha_match.group(1) if fecha_match else fecha_text

    body_parts = []

    # Process sections
    sections = soup.find_all("div", class_="section")
    for section in sections:
        section_id = section.get("id", "")

        for child in section.children:
            if not hasattr(child, "name"):
                continue

            if child.name in ("h2", "h3", "h4"):
                tag = child.name
                text = escape_latex(child.get_text(strip=True))
                if tag == "h2":
                    body_parts.append(r"\section{" + text + "}")
                elif tag == "h3":
                    body_parts.append(r"\subsection{" + text + "}")
                elif tag == "h4":
                    body_parts.append(r"\subsubsection*{" + text + "}")

            elif child.name == "p":
                text_parts = []
                for c in child.descendants:
                    if c.name == "code":
                        text_parts.append(r"\texttt{" + escape_latex(c.get_text()) + "}")
                    elif c.name == "b":
                        text_parts.append(r"\textbf{" + escape_latex(c.get_text()) + "}")
                    elif c.name is None and c.string:
                        text_parts.append(escape_latex(c.string))
                    elif c.name == "span":
                        txt = escape_latex(c.get_text())
                        cls = c.get("class", [])
                        if "summary-ok" in cls:
                            txt = r"\ok{" + txt + "}"
                        elif "summary-fail" in cls:
                            txt = r"\fail{" + txt + "}"
                        elif "summary-partial" in cls:
                            txt = r"\partialcmd{" + txt + "}"
                        elif "ok" in cls:
                            txt = r"\ok{" + txt + "}"
                        elif "warn" in cls:
                            txt = r"\warn{" + txt + "}"
                        elif "fail" in cls:
                            txt = r"\fail{" + txt + "}"
                        text_parts.append(txt)

                if text_parts:
                    body_parts.append(" ".join(text_parts) + r"\\")
                    body_parts.append("")

            elif child.name == "table":
                cls = child.get("class", [])
                if "fail" in str(child):
                    pass  # handle matrix tables later
                body_parts.append(parse_table(child))
                body_parts.append("")

            elif child.name == "pre":
                body_parts.append(parse_pre_block(child))
                body_parts.append("")

            elif child.name == "code":
                body_parts.append(r"\texttt{" + escape_latex(child.get_text()) + "}")

    body_text = "\n".join(body_parts)

    # Clean up the title (remove HTML tags)
    title_clean = re.sub(r"</?title>", "", title)
    title_clean = title_clean.strip()
    title_clean = escape_latex(title_clean)

    fecha_clean = escape_latex(fecha.strip()) if fecha else ""

    latex_output = LATEX_TEMPLATE.replace("TITLE_PLACEHOLDER", title_clean)
    latex_output = latex_output.replace("FECHA_PLACEHOLDER", fecha_clean)
    latex_output = latex_output.replace("BODY_PLACEHOLDER", body_text)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(latex_output)

    print(f"  -> {output_path}")


def main():
    base_dir = "/home/natalia/Documents/Releasev4/docs/reports/cli-multiuser-altcidr"
    
    html_files = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.endswith(".html"):
                html_files.append(os.path.join(root, f))

    for html_path in sorted(html_files):
        rel = os.path.relpath(html_path, base_dir)
        print(f"Converting: {rel}")
        output_path = html_path.rsplit(".html", 1)[0] + ".tex"
        convert_html_to_latex(html_path, output_path)

    print(f"\nDone. Converted {len(html_files)} files.")


if __name__ == "__main__":
    main()
