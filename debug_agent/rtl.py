"""Lightweight SystemVerilog indexer: modules, instances, ports and drivers.

Regex-based (no full parser), good enough to answer the questions a debug
engineer asks most:

* which file/module is ``soc_top.u_apb_timer``?
* what drives ``soc_top.u_apb_spi_master.PREADY``, following port
  connections down through sub-module instances?

It traces through instance boundaries (a plain ``.PREADY(PREADY)`` port
pass-through into a child module), which a single-file search misses.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_KEYWORDS = {
    "module", "endmodule", "input", "output", "inout", "logic", "wire", "reg", "assign", "always",
    "always_ff", "always_comb", "always_latch", "initial", "if", "else", "for", "case", "begin", "end",
    "generate", "endgenerate", "function", "task", "return", "localparam", "parameter", "typedef",
    "int", "bit", "genvar", "assert", "property", "sequence", "import", "export", "default",
}
_MODULE = re.compile(r"\bmodule\s+(?:automatic\s+)?(\w+)")
_ENDMODULE = re.compile(r"\bendmodule\b")
_INSTANCE = re.compile(
    r"(?<![\w.$`])(?P<type>\w+)\s*(?:#\s*\((?P<params>(?:[^()]|\((?:[^()]|\([^()]*\))*\))*)\))?\s*"
    r"(?P<name>\w+)\s*(?:\[[^\]]*\]\s*)?\((?P<ports>(?:[^()]|\((?:[^()]|\([^()]*\))*\))*)\)\s*;", re.S)
_PORT_CONN = re.compile(r"\.(\w+)\s*\(\s*([^()]*(?:\([^()]*\)[^()]*)*)\s*\)")
_PORT_DECL = re.compile(r"\b(input|output|inout)\b([^;,)]*?)\b(\w+)\s*(?:\[[^\]]*\]\s*)*(?=[,;)]|$)", re.M)


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group().count("\n"), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


@dataclass
class Instance:
    type: str
    name: str
    ports: dict[str, str]
    line: int


@dataclass
class Module:
    name: str
    file: Path
    line: int
    body: str                       # comment-stripped text, line numbers preserved via offset
    body_line: int
    ports: dict[str, str] = field(default_factory=dict)     # name -> direction
    instances: dict[str, Instance] = field(default_factory=dict)


@dataclass
class Driver:
    module: str
    file: Path
    line: int
    text: str
    kind: str          # assign | procedural | port | tie-off
    path: str          # hierarchical path of the driven signal


class RtlIndex:
    def __init__(self, roots: list[str | Path]):
        self.modules: dict[str, Module] = {}
        for root in roots:
            root = Path(root)
            files = [root] if root.is_file() else sorted(
                p for ext in ("*.sv", "*.v", "*.svh") for p in root.rglob(ext))
            for f in files:
                self._index_file(f)

    def _index_file(self, path: Path) -> None:
        text = _strip_comments(path.read_text(errors="replace"))
        for m in _MODULE.finditer(text):
            end = _ENDMODULE.search(text, m.end())
            body = text[m.start(): end.start() if end else len(text)]
            line = text.count("\n", 0, m.start()) + 1
            mod = Module(m[1], path, line, body, line)
            for pm in _PORT_DECL.finditer(body):
                mod.ports.setdefault(pm[3], pm[1])
            for im in _INSTANCE.finditer(body):
                if im["type"] in _KEYWORDS or im["name"] in _KEYWORDS or im["type"] == m[1]:
                    continue
                ports = {p: e.strip() for p, e in _PORT_CONN.findall(im["ports"])}
                if not ports and im["ports"].strip():
                    continue          # positional / not an instance (e.g. a function call)
                mod.instances[im["name"]] = Instance(im["type"], im["name"], ports,
                                                     line + body.count("\n", 0, im.start()))
            self.modules[mod.name] = mod

    # ---------------------------------------------------------------- lookup
    def resolve(self, hier: str) -> tuple[Module, list[str]]:
        """Resolve ``top.inst.inst[.signal]`` -> (module of deepest instance, remaining parts).

        Leading simulator prefixes (``TOP.``, ``tb_top.dut`` …) are skipped by
        starting at the first component that is a known module name, or that is
        an instance of a module whose parent is unknown.
        """
        parts = [p for p in re.split(r"[./]", hier) if p]
        start = next((i for i, p in enumerate(parts) if p in self.modules), None)
        if start is None:
            raise KeyError(f"no known module in path '{hier}'")
        mod = self.modules[parts[start]]
        rest = parts[start + 1:]
        while rest and rest[0] in mod.instances and mod.instances[rest[0]].type in self.modules:
            mod = self.modules[mod.instances[rest[0]].type]
            rest = rest[1:]
        return mod, rest

    def _line_of(self, mod: Module, offset: int) -> int:
        return mod.body_line + mod.body.count("\n", 0, offset)

    def _src_line(self, mod: Module, line: int) -> str:
        try:
            return mod.file.read_text(errors="replace").splitlines()[line - 1].strip()
        except IndexError:
            return ""

    def drivers(self, hier: str, depth: int = 4) -> list[Driver]:
        """Everything that drives the signal at ``hier``, tracing into child instances."""
        mod, rest = self.resolve(hier)
        if len(rest) != 1:
            raise KeyError(f"'{hier}' does not end in a signal of module {mod.name}")
        return self._drivers_in(mod, rest[0], hier, depth)

    def _drivers_in(self, mod: Module, sig: str, path: str, depth: int) -> list[Driver]:
        out: list[Driver] = []
        s = re.escape(sig)
        for m in re.finditer(rf"\bassign\s+{s}\b\s*(?:\[[^\]]*\]\s*)?=(?!=)", mod.body):
            ln = self._line_of(mod, m.start())
            text = self._src_line(mod, ln)
            kind = "tie-off" if re.search(rf"=\s*(?:\d*'[bhd][0-9a-fA-F_]+|'[01]|\d+)\s*;", text) else "assign"
            out.append(Driver(mod.name, mod.file, ln, text, kind, path))
        for m in re.finditer(rf"(?:^|[;\s]|begin)\s*(?P<sig>{s})\b\s*(?:\[[^\]]*\]\s*)*(<=|=)(?!=)", mod.body, re.M):
            before = mod.body[max(0, m.start("sig") - 200): m.start("sig")]
            if re.search(r"\b(assign|parameter|localparam)\b[^;]*$", before):
                continue
            ln = self._line_of(mod, m.start("sig"))
            out.append(Driver(mod.name, mod.file, ln, self._src_line(mod, ln), "procedural", path))
        if depth > 0:
            for inst in mod.instances.values():
                child = self.modules.get(inst.type)
                for port, expr in inst.ports.items():
                    if not re.fullmatch(rf"{s}(\s*\[[^\]]*\])?", expr):
                        continue
                    if child is None:
                        out.append(Driver(mod.name, mod.file, inst.line,
                                          f"{inst.type} {inst.name} (.{port}({expr})) [module source not indexed]",
                                          "port", path))
                    elif child.ports.get(port) in ("output", "inout"):
                        out.append(Driver(mod.name, mod.file, inst.line,
                                          f"{inst.type} {inst.name} (.{port}({expr}))", "port", path))
                        out.extend(self._drivers_in(child, port, f"{path.rsplit('.', 1)[0]}.{inst.name}.{port}",
                                                    depth - 1))
        # de-duplicate (same file/line)
        seen, uniq = set(), []
        for d in out:
            if (d.file, d.line) not in seen:
                seen.add((d.file, d.line))
                uniq.append(d)
        return uniq

    def hierarchy(self, top: str, max_depth: int = 6) -> list[str]:
        lines: list[str] = []

        def walk(mod: Module, prefix: str, d: int) -> None:
            for inst in mod.instances.values():
                child = self.modules.get(inst.type)
                where = f"{child.file}:{child.line}" if child else "(not indexed)"
                lines.append(f"{prefix}.{inst.name}  [{inst.type}]  {where}")
                if child and d < max_depth:
                    walk(child, f"{prefix}.{inst.name}", d + 1)

        mod = self.modules[top]
        lines.append(f"{top}  {mod.file}:{mod.line}")
        walk(mod, top, 1)
        return lines


def load_rtl(roots: list[str | Path], backend: str = "auto"):
    """RTL index: pyslang (exact, elaborated) when installed, else the regex indexer.

    backend: "auto" | "slang" | "regex". Falls back to regex when pyslang is
    missing or cannot elaborate the sources.
    """
    if backend in ("auto", "slang"):
        try:
            from .rtl_slang import SlangIndex
            idx = SlangIndex(roots)
            if idx.instances:
                return idx
            if backend == "slang":
                raise RuntimeError("pyslang elaborated no instances")
        except ImportError:
            if backend == "slang":
                raise
    idx = RtlIndex(roots)
    idx.backend = "regex"
    return idx
