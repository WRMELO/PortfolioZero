#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import inspect
import json
import pkgutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def public_names(obj: Any, limit: int) -> list[str]:
    try:
        names = [n for n in dir(obj) if not n.startswith("_")]
        return sorted(names)[:limit]
    except Exception:
        return []


def classify_symbol(value: Any) -> str:
    try:
        if inspect.isclass(value):
            return "class"
        if inspect.isfunction(value):
            return "function"
        if inspect.ismodule(value):
            return "module"
        if callable(value):
            return "callable"
        return type(value).__name__
    except Exception:
        return "unknown"


def safe_signature(value: Any) -> str | None:
    try:
        if callable(value):
            return str(inspect.signature(value))
    except Exception:
        return None
    return None


def safe_doc_firstline(value: Any) -> str | None:
    try:
        doc = inspect.getdoc(value) or ""
        if doc.strip():
            return doc.strip().splitlines()[0][:200]
    except Exception:
        return None
    return None


@dataclass
class ModuleSymbol:
    name: str
    kind: str
    qualname: str | None
    signature: str | None
    doc_firstline: str | None


@dataclass
class ModuleMap:
    module: str
    import_ok: bool
    error: str | None
    public_count: int
    public_sample: list[str]
    symbols: list[ModuleSymbol]


@dataclass
class AgnoApiMap:
    captured_at_utc: str
    python_executable: str
    python_version: str
    agno_version: str
    agno_file: str
    agno_has_path: bool
    submodules: list[str]
    modules: list[ModuleMap]
    candidates: dict[str, list[dict[str, str]]]


CANDIDATE_KEYWORDS = [
    "agent",
    "workflow",
    "runner",
    "task",
    "tool",
    "orchestr",
    "executor",
    "pipeline",
]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Gera mapa auditável da API Python do pacote agno instalado no .venv."
    )
    ap.add_argument(
        "--out",
        required=True,
        help="JSON de saída (ex: planning/runs/TASK_A_004/agno_api_map.json).",
    )
    ap.add_argument(
        "--max-modules",
        type=int,
        default=80,
        help="Máximo de submódulos a tentar importar (default=80).",
    )
    ap.add_argument(
        "--max-public",
        type=int,
        default=80,
        help="Máximo de nomes públicos por módulo (default=80).",
    )
    ap.add_argument(
        "--max-symbols",
        type=int,
        default=40,
        help="Máximo de símbolos detalhados por módulo (default=40).",
    )
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    agno = importlib.import_module("agno")
    agno_version = getattr(agno, "__version__", "?")
    agno_file = getattr(agno, "__file__", "?")
    agno_has_path = hasattr(agno, "__path__")

    submods: list[str] = []
    if agno_has_path:
        for m in pkgutil.iter_modules(agno.__path__):  # type: ignore[attr-defined]
            submods.append(m.name)
    submods = sorted(submods)[: args.max_modules]

    modules: list[ModuleMap] = []
    candidates: dict[str, list[dict[str, str]]] = {k: [] for k in CANDIDATE_KEYWORDS}

    for sm in submods:
        full = f"agno.{sm}"
        try:
            mod = importlib.import_module(full)
            pub = public_names(mod, args.max_public)

            syms: list[ModuleSymbol] = []
            # detalhar só os primeiros N símbolos (ordem determinística)
            for n in pub[: args.max_symbols]:
                try:
                    v = getattr(mod, n)
                    kind = classify_symbol(v)
                    qn = getattr(v, "__qualname__", None)
                    sig = safe_signature(v)
                    doc1 = safe_doc_firstline(v)
                    syms.append(ModuleSymbol(name=n, kind=kind, qualname=qn, signature=sig, doc_firstline=doc1))

                    low = n.lower()
                    for kw in CANDIDATE_KEYWORDS:
                        if kw in low:
                            candidates[kw].append({"module": full, "symbol": n, "kind": kind})
                except Exception:
                    continue

            modules.append(
                ModuleMap(
                    module=full,
                    import_ok=True,
                    error=None,
                    public_count=len(pub),
                    public_sample=pub[: min(len(pub), 30)],
                    symbols=syms,
                )
            )
        except Exception as e:
            modules.append(
                ModuleMap(
                    module=full,
                    import_ok=False,
                    error=f"{type(e).__name__}: {e}",
                    public_count=0,
                    public_sample=[],
                    symbols=[],
                )
            )

    # também registra o topo do pacote
    topo_pub = public_names(agno, args.max_public)
    topo_symbols: list[ModuleSymbol] = []
    for n in topo_pub[: args.max_symbols]:
        try:
            v = getattr(agno, n)
            kind = classify_symbol(v)
            qn = getattr(v, "__qualname__", None)
            sig = safe_signature(v)
            doc1 = safe_doc_firstline(v)
            topo_symbols.append(ModuleSymbol(name=n, kind=kind, qualname=qn, signature=sig, doc_firstline=doc1))

            low = n.lower()
            for kw in CANDIDATE_KEYWORDS:
                if kw in low:
                    candidates[kw].append({"module": "agno", "symbol": n, "kind": kind})
        except Exception:
            continue

    modules.insert(
        0,
        ModuleMap(
            module="agno",
            import_ok=True,
            error=None,
            public_count=len(topo_pub),
            public_sample=topo_pub[: min(len(topo_pub), 30)],
            symbols=topo_symbols,
        ),
    )

    payload = AgnoApiMap(
        captured_at_utc=utc_now(),
        python_executable=sys.executable,
        python_version=sys.version,
        agno_version=str(agno_version),
        agno_file=str(agno_file),
        agno_has_path=bool(agno_has_path),
        submodules=submods,
        modules=modules,
        candidates=candidates,
    )

    out_path.write_text(json.dumps(asdict(payload), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("WROTE:", out_path)
    print("agno_version:", payload.agno_version)
    print("modules_mapped:", len(payload.modules))
    print("candidates_summary:")
    for kw in CANDIDATE_KEYWORDS:
        print(f" - {kw}: {len(payload.candidates.get(kw, []))}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
