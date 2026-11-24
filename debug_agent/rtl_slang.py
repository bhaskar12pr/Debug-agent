"""pyslang backend for RTL lookups: a real SystemVerilog compiler front end.

Same interface as :class:`debug_agent.rtl.RtlIndex` (``resolve``, ``drivers``,
``hierarchy``), but built on the elaborated design, so it handles what the
regex indexer cannot: macros/`include/`ifdef, parameters, generate blocks
(``u_apb_timer.TIMER_GEN[0].timer_i``), interfaces and exact assignments.

Optional dependency: ``pip install pyslang``.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from pyslang import Bag, DiagnosticEngine, TimeScale, ast
from pyslang.syntax import SyntaxTree

from .rtl import Driver, Module

_SV_EXT = (".sv", ".v")
_SCOPE_KINDS = {ast.SymbolKind.GenerateBlock, ast.SymbolKind.GenerateBlockArray}


class SlangIndex:
    backend = "pyslang"

    def __init__(self, roots: list[str | Path], top: str | None = None, timescale: str = "1ns/1ps"):
        files: list[Path] = []
        for root in map(Path, roots):
            files += [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.suffix in _SV_EXT)
        self.files = files
        opts = ast.CompilationOptions()
        # Simulators apply a default timescale to files without one; do the same.
        opts.defaultTimeScale = TimeScale.fromString(timescale)
        if top:
            opts.topModules = {top}
        self.comp = ast.Compilation(Bag([opts]))
        for f in files:
            self.comp.addSyntaxTree(SyntaxTree.fromFile(str(f)))
        self.root = self.comp.getRoot()
        self.sm = self.comp.sourceManager
        self.errors = [d for d in self.comp.getAllDiagnostics() if d.isError()]
        self.instances: dict[str, ast.InstanceSymbol] = {}
        for t in self.root.topInstances:
            self.instances[t.hierarchicalPath] = t
            self._collect(t)

    def diagnostics(self, errors_only: bool = False) -> list[str]:
        """Compiler errors/warnings as text: a free lint pass over RTL + TB."""
        diags = [d for d in self.comp.getAllDiagnostics() if d.isError() or not errors_only]
        text = DiagnosticEngine.reportAll(self.sm, diags)
        return [l for l in text.splitlines() if re.search(r":\d+:\d+: (error|warning)", l)]

    # ------------------------------------------------------------- helpers
    def _members(self, scope):
        """Members of an instance body, flattening generate blocks (not child instances)."""
        for m in scope:
            if m.kind == ast.SymbolKind.GenerateBlockArray:
                for blk in m.entries:
                    if getattr(blk, "isUninstantiated", False):
                        continue
                    yield from self._members(blk)
            elif m.kind == ast.SymbolKind.GenerateBlock:
                if not getattr(m, "isUninstantiated", False):
                    yield from self._members(m)
            else:
                yield m

    def _children(self, inst):
        return [m for m in self._members(inst.body) if m.kind == ast.SymbolKind.Instance]

    def _collect(self, inst) -> None:
        for c in self._children(inst):
            self.instances[c.hierarchicalPath] = c
            self._collect(c)

    def _loc(self, loc) -> tuple[Path, int]:
        try:
            loc = self.sm.getFullyOriginalLoc(loc)
        except Exception:
            pass
        name = self.sm.getFileName(loc)
        p = Path(name) if os.path.isabs(name) else Path(os.path.normpath(os.path.join(os.getcwd(), name)))
        return p, self.sm.getLineNumber(loc)

    @staticmethod
    def _src(path: Path, line: int) -> str:
        try:
            return path.read_text(errors="replace").splitlines()[line - 1].strip()
        except (OSError, IndexError):
            return ""

    def _module(self, inst) -> Module:
        f, ln = self._loc(inst.definition.location)
        ports = {}
        for p in inst.body.portList:
            d = str(getattr(p, "direction", "")).rsplit(".", 1)[-1].lower()
            ports[p.name] = {"in": "input", "out": "output", "inout": "inout"}.get(d, d)
        return Module(inst.definition.name, f, ln, "", ln, ports)

    # ------------------------------------------------------------- lookup
    def _find_instance(self, parts: list[str]):
        """Longest instance path matching a suffix-anchored prefix of ``parts``."""
        defs = {i.definition.name for i in self.instances.values()}
        for start in range(len(parts)):
            p0 = parts[start]
            bases: list[str] = []
            if p0 in defs:
                bases = sorted((k for k, i in self.instances.items() if i.definition.name == p0), key=len)[:1]
            elif p0 in {k.split(".")[0] for k in self.instances}:
                bases = [p0]
            if not bases:
                continue
            base, j = bases[0], start + 1
            while j < len(parts):
                # generate scopes may be one or two path components (TIMER_GEN[0].timer_i)
                nxt = next((base + "." + ".".join(parts[j:k]) for k in range(j + 1, min(j + 3, len(parts)) + 1)
                            if base + "." + ".".join(parts[j:k]) in self.instances), None)
                if nxt is None:
                    break
                j += nxt.count(".") - base.count(".")
                base = nxt
            return self.instances[base], parts[j:]
        raise KeyError("no known module or instance in path")

    @staticmethod
    def _split(hier: str) -> list[str]:
        return [p for p in re.split(r"\.(?![^\[]*\])|/", hier) if p]

    def resolve(self, hier: str) -> tuple[Module, list[str]]:
        inst, rest = self._find_instance(self._split(hier))
        return self._module(inst), rest

    def drivers(self, hier: str, depth: int = 4) -> list[Driver]:
        parts = self._split(hier)
        inst, rest = self._find_instance(parts)
        if len(rest) != 1:
            raise KeyError(f"'{hier}' does not end in a signal of module {inst.definition.name}")
        return self._drivers_in(inst, rest[0], hier, depth)

    def _lhs_names(self, expr) -> set[str]:
        sym = expr.getSymbolReference() if hasattr(expr, "getSymbolReference") else None
        if sym is not None:
            return {sym.name}
        names: set[str] = set()

        def cb(n):
            if isinstance(n, ast.NamedValueExpression):
                names.add(n.symbol.name)
            return True
        expr.visit(cb)
        return names

    def _drivers_in(self, inst, sig: str, path: str, depth: int) -> list[Driver]:
        out: list[Driver] = []
        mod = inst.definition.name

        def add(expr, kind: str) -> None:
            f, ln = self._loc(expr.sourceRange.start)
            text = self._src(f, ln)
            rhs = expr.right
            while rhs.kind == ast.ExpressionKind.Conversion:
                rhs = rhs.operand
            if kind == "assign" and rhs.kind in (ast.ExpressionKind.IntegerLiteral,
                                                  ast.ExpressionKind.UnbasedUnsizedIntegerLiteral):
                kind = "tie-off"
            out.append(Driver(mod, f, ln, text, kind, path))

        for m in self._members(inst.body):
            if m.kind == ast.SymbolKind.ContinuousAssign:
                a = m.assignment
                if isinstance(a, ast.AssignmentExpression) and sig in self._lhs_names(a.left):
                    add(a, "assign")
            elif m.kind == ast.SymbolKind.ProceduralBlock:
                def cb(n):
                    if isinstance(n, ast.AssignmentExpression) and sig in self._lhs_names(n.left):
                        add(n, "procedural")
                    return True
                m.visit(cb)
            elif m.kind == ast.SymbolKind.Instance and depth > 0:
                for pc in m.portConnections:
                    e = pc.expression
                    if not isinstance(e, ast.AssignmentExpression) or sig not in self._lhs_names(e.left):
                        continue        # inputs are not drivers; outputs appear as assignments
                    f, ln = self._loc(m.location)
                    out.append(Driver(mod, f, ln, f"{m.definition.name} {m.name} (.{pc.port.name}(...))",
                                      "port", path))
                    child_path = m.hierarchicalPath[len(inst.hierarchicalPath) + 1:]
                    out += self._drivers_in(m, pc.port.name, f"{path.rsplit('.', 1)[0]}.{child_path}.{pc.port.name}",
                                            depth - 1)
        seen, uniq = set(), []
        for d in out:
            if (d.file, d.line, d.path) not in seen:
                seen.add((d.file, d.line, d.path))
                uniq.append(d)
        return uniq

    def hierarchy(self, top: str, max_depth: int = 6) -> list[str]:
        inst, _ = self._find_instance([top])
        f, ln = self._loc(inst.definition.location)
        lines = [f"{top}  {f}:{ln}"]

        def walk(i, prefix: str, d: int) -> None:
            for c in self._children(i):
                cf, cl = self._loc(c.definition.location)
                params = {p.name: str(p.value) for p in c.body if p.kind == ast.SymbolKind.Parameter and p.isPortParam}
                ptxt = f"  #({', '.join(f'{k}={v}' for k, v in params.items())})" if params else ""
                rel = c.hierarchicalPath[len(i.hierarchicalPath) + 1:]
                lines.append(f"{prefix}.{rel}  [{c.definition.name}]  {cf}:{cl}{ptxt}")
                if d < max_depth:
                    walk(c, f"{prefix}.{rel}", d + 1)

        walk(inst, top, 1)
        return lines
