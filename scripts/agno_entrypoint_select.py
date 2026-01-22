#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import inspect
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


# Palavras comuns em runtimes / orquestração (mas não dependemos só disso)
PATTERNS = (
    "orchestr",
    "executor",
    "runner",
    "workflow",
    "task",
    "agent",
    "tool",
    "app",
    "runtime",
    "engine",
    "session",
    "manager",
    "graph",
    "pipeline",
    "plan",
    "flow",
    "dispatch",
)

# Símbolos prováveis para runtime (fallback forte)
PREFERRED_ATTRS = (
    "Orchestrator",
    "Executor",
    "Runner",
    "Workflow",
    "Agent",
    "App",
    "Engine",
    "Runtime",
    "Session",
    "Manager",
    "Tool",
    "Tools",
)

# Algumas rotas comuns (tentadas além do map)
FALLBACK_MODULES = (
    "agno",
    "agno.core",
    "agno.runtime",
    "agno.workflow",
    "agno.workflows",
    "agno.agent",
    "agno.agents",
    "agno.tools",
    "agno.tool",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def flatten_str_values(x: Any) -> list[str]:
    out: list[str] = []
    if isinstance(x, str):
        out.append(x)
    elif isinstance(x, list):
        for v in x:
            out.extend(flatten_str_values(v))
    elif isinstance(x, dict):
        for v in x.values():
            out.extend(flatten_str_values(v))
    return out


def looks_relevant(name: str) -> bool:
    n = name.lower()
    return any(p in n for p in PATTERNS)


def iter_unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if it and it not in seen:
            seen.add(it)
            out.append(it)
    return out


def import_module_safe(mod: str) -> tuple[bool, Any | None, str | None]:
    try:
        m = importlib.import_module(mod)
        return True, m, None
    except Exception as e:
        return False, None, repr(e)


def split_fqn(fqn: str) -> tuple[str, str] | None:
    if "." not in fqn:
        return None
    mod, attr = fqn.rsplit(".", 1)
    return mod, attr


def getattr_safe(mod_obj: Any, attr: str) -> tuple[bool, Any | None, str | None]:
    try:
        return True, getattr(mod_obj, attr), None
    except Exception as e:
        return False, None, repr(e)


def kind_of(obj: Any) -> str:
    if inspect.isclass(obj):
        return "class"
    if inspect.isfunction(obj):
        return "function"
    if callable(obj):
        return "callable"
    return "other"


def score_candidate(fqn: str, kind: str, preferred: bool = False) -> int:
    n = fqn.lower()
    score = 0

    # prioridade máxima para preferidos (fallback)
    if preferred:
        score += 1000

    # pesos de intenção (runtime)
    if "orchestr" in n:
        score += 120
    if "executor" in n:
        score += 110
    if "runner" in n:
        score += 90
    if "workflow" in n or "workflows" in n:
        score += 70
    if ".task" in n or "task" in n:
        score += 50
    if "agent" in n:
        score += 60
    if "tool" in n:
        score += 40
    if "app" in n:
        score += 55
    if "runtime" in n:
        score += 55
    if "engine" in n:
        score += 45
    if "session" in n:
        score += 35
    if "manager" in n:
        score += 25
    if "graph" in n or "pipeline" in n or "flow" in n:
        score += 20

    # preferir classes / callables
    if kind == "class":
        score += 35
    elif kind in ("function", "callable"):
        score += 20

    # penalizações leves
    if "test" in n or "fixture" in n:
        score -= 25
    if "typing" in n or "types" in n:
        score -= 10

    return score


@dataclass
class Candidate:
    fqn: str
    module: str
    attr: str
    kind: str
    import_ok: bool
    error: str | None
    score: int
    preferred: bool


def candidates_from_map(data: dict[str, Any]) -> list[str]:
    # tenta usar "candidates" se existir
    if isinstance(data.get("candidates"), dict):
        return iter_unique(flatten_str_values(data["candidates"]))
    # fallback: tenta chaves comuns
    for key in ("entrypoints", "symbols", "exports"):
        if key in data:
            return iter_unique(flatten_str_values(data[key]))
    return []


def modules_from_map(data: dict[str, Any]) -> list[str]:
    subs = data.get("submodules")
    mods = data.get("modules")
    out: list[str] = []
    if isinstance(subs, list):
        out.extend([x for x in subs if isinstance(x, str)])
    if isinstance(mods, list):
        out.extend([x for x in mods if isinstance(x, str)])
    out.extend(list(FALLBACK_MODULES))
    # sempre tentar raiz
    out.append("agno")
    return iter_unique(out)


def scan_module_for_candidates(mod: str, max_attrs: int = 2500) -> list[str]:
    ok, m, _ = import_module_safe(mod)
    if not ok or m is None:
        return []
    out: list[str] = []
    try:
        names = dir(m)[:max_attrs]
        for name in names:
            if name.startswith("_"):
                continue
            # aqui NÃO exigimos looks_relevant para capturar Agent/App/Workflow etc.
            try:
                obj = getattr(m, name)
            except Exception:
                continue
            if inspect.isclass(obj) or inspect.isfunction(obj) or callable(obj):
                # mas filtramos a lista final por relevância OU por ser preferido
                if looks_relevant(name) or name in PREFERRED_ATTRS:
                    out.append(f"{mod}.{name}")
    except Exception:
        return []
    return iter_unique(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="agno_entrypoint_select",
        description="Seleciona e versiona o entrypoint do Agno para runtime (executor/orquestrador), baseado em evidência.",
    )
    ap.add_argument(
        "--map",
        default="planning/runs/TASK_A_004/agno_api_map.json",
        help="Caminho do JSON de evidência (gerado pela TASK_A_004).",
    )
    ap.add_argument(
        "--out",
        default="config/agno/runtime_entrypoint.json",
        help="Arquivo de saída versionável com o entrypoint selecionado.",
    )
    ap.add_argument("--max-modules", type=int, default=200, help="Máx. de módulos a tentar.")
    ap.add_argument("--max-considered", type=int, default=60, help="Quantos candidatos manter no relatório.")
    ap.add_argument("--dry-run", action="store_true", help="Não grava arquivo de saída.")
    args = ap.parse_args()

    map_path = Path(args.map)
    out_path = Path(args.out)

    result: dict[str, Any] = {
        "status": "init",
        "generated_at": utc_now(),
        "source_map": str(map_path),
        "python": sys.version,
        "agno_version": None,
        "selected": None,
        "considered": [],
        "module_import_errors": {},
        "notes": [],
    }

    if not map_path.exists():
        result["status"] = "fail"
        result["notes"].append(f"map_not_found: {map_path}")
        if args.dry_run:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            safe_write_json(out_path, result)
        return 2

    data = safe_read_json(map_path)

    # melhor esforço: version
    agno_version = data.get("agno_version")
    if not agno_version:
        try:
            import agno  # type: ignore

            agno_version = getattr(agno, "__version__", None)
        except Exception:
            agno_version = None
    result["agno_version"] = agno_version

    # 1) candidatos explícitos do map (se houver)
    explicit = candidates_from_map(data)

    # 2) lista de módulos/submódulos (do map + fallback)
    mods_all = modules_from_map(data)[: args.max_modules]

    # 3) geração de candidatos:
    #    (a) tentar símbolos preferidos em todos os módulos importáveis
    preferred_fqns: list[str] = []
    scanned_fqns: list[str] = []

    for m in mods_all:
        ok, mod_obj, err = import_module_safe(m)
        if not ok or mod_obj is None:
            result["module_import_errors"][m] = err
            continue

        # tenta preferidos (alto valor)
        for a in PREFERRED_ATTRS:
            if hasattr(mod_obj, a):
                preferred_fqns.append(f"{m}.{a}")

        # varredura controlada de atributos
        scanned_fqns.extend(scan_module_for_candidates(m))

    cand_fqns = iter_unique(explicit + preferred_fqns + scanned_fqns)

    candidates: list[Candidate] = []

    for fqn in cand_fqns:
        sp = split_fqn(fqn)
        if not sp:
            continue
        mod, attr = sp
        preferred = attr in PREFERRED_ATTRS

        ok_mod, mobj, err_mod = import_module_safe(mod)
        if not ok_mod or mobj is None:
            candidates.append(
                Candidate(
                    fqn=fqn,
                    module=mod,
                    attr=attr,
                    kind="unknown",
                    import_ok=False,
                    error=f"import_module_fail: {err_mod}",
                    score=0,
                    preferred=preferred,
                )
            )
            continue

        ok_attr, obj, err_attr = getattr_safe(mobj, attr)
        if not ok_attr or obj is None:
            candidates.append(
                Candidate(
                    fqn=fqn,
                    module=mod,
                    attr=attr,
                    kind="unknown",
                    import_ok=False,
                    error=f"getattr_fail: {err_attr}",
                    score=0,
                    preferred=preferred,
                )
            )
            continue

        k = kind_of(obj)
        sc = score_candidate(fqn, k, preferred=preferred)
        candidates.append(
            Candidate(
                fqn=fqn,
                module=mod,
                attr=attr,
                kind=k,
                import_ok=True,
                error=None,
                score=sc,
                preferred=preferred,
            )
        )

    # ordena por (import_ok desc, score desc)
    candidates_sorted = sorted(candidates, key=lambda c: (1 if c.import_ok else 0, c.score), reverse=True)

    considered_payload: list[dict[str, Any]] = []
    for c in candidates_sorted[: args.max_considered]:
        considered_payload.append(
            {
                "fqn": c.fqn,
                "module": c.module,
                "attr": c.attr,
                "kind": c.kind,
                "import_ok": c.import_ok,
                "preferred": c.preferred,
                "score": c.score,
                "error": c.error,
            }
        )
    result["considered"] = considered_payload
    result["notes"].append(f"modules_considered={len(mods_all)}")
    result["notes"].append(f"candidates_total={len(cand_fqns)}")
    result["notes"].append(f"candidates_importable={sum(1 for c in candidates if c.import_ok)}")

    selected = next((c for c in candidates_sorted if c.import_ok and c.score >= 50), None)
    if not selected:
        # se nada com score>=50, pega o melhor importável mesmo assim
        selected = next((c for c in candidates_sorted if c.import_ok), None)

    if not selected:
        result["status"] = "no_candidate_importable"
        result["notes"].append("Nenhum candidato importável foi encontrado. Verifique agno_api_map.json e imports.")
        if args.dry_run:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            safe_write_json(out_path, result)
        return 2

    result["status"] = "selected"
    result["selected"] = {
        "fqn": selected.fqn,
        "module": selected.module,
        "attr": selected.attr,
        "kind": selected.kind,
        "preferred": selected.preferred,
        "score": selected.score,
    }

    if args.dry_run:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        safe_write_json(out_path, result)

    print("STATUS:", result["status"])
    print("SELECTED:", result["selected"]["fqn"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
