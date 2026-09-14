"""Minimal Windows/desktop GUI for ALS downgrade (stdlib tkinter)."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from alsdowngrade.converter import Outcome, convert_als
from alsdowngrade.gzip_io import load_als_xml_bytes
from alsdowngrade.parser import parse_als_xml
from alsdowngrade.analyzer import analyze_for_target
from alsdowngrade.report import format_inspect
from alsdowngrade.version import list_target_aliases, version_from_tree


TARGETS = [
    ("11.2", "Live 11.2.11 (recommended for 11.2.x)"),
    ("11.2.7", "Live 11.2.7 (older 11.2)"),
    ("11.3", "Live 11.3.21"),
    ("11.1", "Live 11.1"),
    ("11.0", "Live 11.0.12"),
]
MODES = [
    ("compatible", "Compatible (recommended)"),
    ("conservative", "Conservative"),
    ("salvage", "Salvage"),
]


class AlsApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ALS Converter — MontroneDSP")
        self.geometry("720x560")
        self.minsize(640, 480)
        self.source: Path | None = None

        root = ttk.Frame(self, padding=16)
        root.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            root,
            text="Ableton Live Set Downgrader",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor=tk.W)

        ttk.Label(
            root,
            text=(
                "Privacy: no data collection. Everything runs locally on this PC. "
                "Original .als files are never modified. Open source (MIT): "
                "github.com/montronedsp/alsconverter"
            ),
            wraplength=680,
        ).pack(anchor=tk.W, pady=(6, 12))

        row = ttk.Frame(root)
        row.pack(fill=tk.X, pady=(0, 8))
        self.path_var = tk.StringVar(value="No file selected")
        ttk.Entry(row, textvariable=self.path_var, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(row, text="Browse…", command=self.browse).pack(side=tk.LEFT, padx=(8, 0))

        opts = ttk.Frame(root)
        opts.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(opts, text="Target").pack(side=tk.LEFT)
        self.target_var = tk.StringVar(value="11.2")
        ttk.Combobox(
            opts,
            textvariable=self.target_var,
            values=[t[0] for t in TARGETS],
            state="readonly",
            width=12,
        ).pack(side=tk.LEFT, padx=(6, 16))
        ttk.Label(opts, text="Mode").pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="compatible")
        ttk.Combobox(
            opts,
            textvariable=self.mode_var,
            values=[m[0] for m in MODES],
            state="readonly",
            width=14,
        ).pack(side=tk.LEFT, padx=(6, 0))

        actions = ttk.Frame(root)
        actions.pack(fill=tk.X, pady=(0, 8))
        self.inspect_btn = ttk.Button(actions, text="Inspect", command=self.inspect)
        self.inspect_btn.pack(side=tk.LEFT)
        self.convert_btn = ttk.Button(actions, text="Downgrade", command=self.convert)
        self.convert_btn.pack(side=tk.LEFT, padx=(8, 0))

        self.report = tk.Text(root, wrap=tk.WORD, height=20)
        self.report.pack(fill=tk.BOTH, expand=True)
        self.report.insert(tk.END, "Select an .als file to begin.\n")
        self.report.configure(state=tk.DISABLED)

        # Prefer documented aliases; ignore unknown extras
        _ = list_target_aliases()

    def set_report(self, text: str) -> None:
        self.report.configure(state=tk.NORMAL)
        self.report.delete("1.0", tk.END)
        self.report.insert(tk.END, text)
        self.report.configure(state=tk.DISABLED)

    def set_busy(self, busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        self.inspect_btn.configure(state=state)
        self.convert_btn.configure(state=state)

    def browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose Ableton Live Set",
            filetypes=[("Ableton Live Set", "*.als"), ("All files", "*.*")],
        )
        if not path:
            return
        self.source = Path(path)
        self.path_var.set(str(self.source))
        self.set_report(f"Selected: {self.source}\nOriginal will never be modified.\n")

    def inspect(self) -> None:
        if not self.source:
            messagebox.showinfo("ALS Converter", "Choose an .als file first.")
            return
        self.set_busy(True)
        self.set_report("Inspecting…")

        def work() -> None:
            try:
                _, xml = load_als_xml_bytes(self.source)
                tree = parse_als_xml(xml)
                version = version_from_tree(tree)
                analysis = analyze_for_target(tree, target_major=11)
                text = format_inspect(str(self.source), version, analysis)
            except Exception as exc:  # noqa: BLE001
                text = f"Inspect failed: {exc}"
            self.after(0, lambda: (self.set_report(text), self.set_busy(False)))

        threading.Thread(target=work, daemon=True).start()

    def convert(self) -> None:
        if not self.source:
            messagebox.showinfo("ALS Converter", "Choose an .als file first.")
            return
        out_dir = filedialog.askdirectory(title="Choose output folder for the NEW .als")
        if not out_dir:
            return
        self.set_busy(True)
        self.set_report("Converting… writing a NEW file only.")
        target = self.target_var.get()
        mode = self.mode_var.get()
        source = self.source
        output_dir = Path(out_dir)

        def work() -> None:
            text = ""
            ok = False
            output_path = None
            try:
                report = convert_als(
                    source,
                    target=target,
                    mode=mode,
                    output_dir=output_dir,
                )
                lines = [
                    f"Outcome: {report.outcome.value}",
                    f"Target: Live {report.target_label}",
                    f"Mode: {report.mode}",
                    f"Output: {report.output_path or '(none)'}",
                    "ORIGINAL FILE IS NEVER MODIFIED",
                    "",
                ]
                if report.reason:
                    lines += ["Reason:", report.reason, ""]
                if report.preserved:
                    lines.append("Preserved:")
                    for k, v in report.preserved.items():
                        lines.append(f"  {k}: {v}")
                if report.modified:
                    lines.append("Modified:")
                    lines.extend(f"  {m}" for m in report.modified)
                if report.removed:
                    lines.append("Removed:")
                    lines.extend(f"  {m}" for m in report.removed)
                if report.warnings:
                    lines.append("Warnings:")
                    lines.extend(f"  {w}" for w in report.warnings)
                text = "\n".join(lines)
                ok = report.outcome not in {
                    Outcome.INVALID_INPUT,
                    Outcome.REFUSED_UNSUPPORTED,
                }
                output_path = report.output_path
            except Exception as exc:  # noqa: BLE001
                text = f"Convert failed: {exc}"
                ok = False

            def done() -> None:
                self.set_report(text)
                self.set_busy(False)
                if ok and output_path:
                    messagebox.showinfo("ALS Converter", f"Saved:\n{output_path}")

            self.after(0, done)

        threading.Thread(target=work, daemon=True).start()


def main() -> None:
    app = AlsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
