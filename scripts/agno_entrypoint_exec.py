#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import inspect
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_selected_fqn(config_path: Path) -> str:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    sel = cfg.get("selected") or {}
    fqn = sel.get("fqn")
    if not fqn or "." not in fqn:
        raise ValueError(f"INVALID runtime_entrypoint.json: selected.fqn={fqn!r}")
    return str(fqn)


def import_fqn(fqn: str) -> Any:
    mod, attr = fqn.rsplit(".", 1)
    m = importlib.import_module(mod)
    return getattr(m, attr)


def signature_str(obj: Any) -> str:
    try:
        return str(inspect.signature(obj))
    except Exception:
        return "SIGNATURE_UNAVAILABLE"


def try_call(obj: Any, payload: dict[str, Any]) -> tuple[bool, str, str]:
    # 1) tentar padrão argv/args
    try:
        sig = inspect.signature(obj)
        params = list(sig.parameters.values())
        param_names = {p.name for p in params}

        if "argv" in param_names:
            obj(argv=["--help"])
            return True, "call(argv=['--help'])", "OK"
        if "args" in param_names:
            obj(args=["--help"])
            return True, "call(args=['--help'])", "OK"
    except SystemExit as e:
        code = int(getattr(e, "code", 0) or 0)
        ok = code == 0
        return ok, "SystemExit(help-ish)", f"SystemExit(code={code})"
    except Exception:
        pass

    # 2) classe: instanciar e tentar .run(payload) / __call__(payload)
    try:
        if inspect.isclass(obj):
            inst = obj()  # type: ignore[call-arg]
            if hasattr(inst, "run") and callable(getattr(inst, "run")):
                getattr(inst, "run")(payload)  # type: ignore[misc]
                return True, "class().run(payload)", "OK"
            if callable(inst):
                inst(payload)  # type: ignore[misc]
                return True, "class()(payload)", "OK"
            return False, "class() created but no runnable method", "SKIP"
    except SystemExit as e:
        code = int(getattr(e, "code", 0) or 0)
        ok = code == 0
        return ok, "SystemExit(class)", f"SystemExit(code={code})"
    except TypeError:
        return False, "class() failed (needs args)", "SKIP"
    except Exception as ex:
        return False, "class() exception", f"{type(ex).__name__}: {ex}"

    # 3) callable: tentar kwargs conhecidos, senão call() se possível
    try:
        if callable(obj):
            sig = inspect.signature(obj)
            params = list(sig.parameters.values())
            names = {p.name for p in params}

            kwargs: dict[str, Any] = {}
            if "payload" in names:
                kwargs["payload"] = payload
            if "context" in names:
                kwargs["context"] = payload
            if "data" in names:
                kwargs["data"] = payload

            if kwargs:
                obj(**kwargs)  # type: ignore[misc]
                return True, f"call({', '.join(kwargs.keys())})", "OK"

            if len(params) == 0:
                obj()  # type: ignore[misc]
                return True, "call()", "OK"

            all_optional = True
            for p in params:
                if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
                    continue
                if p.default is inspect._empty:
                    all_optional = False
                    break
            if all_optional:
                obj()  # type: ignore[misc]
                return True, "call() (all optional params)", "OK"

            return False, "call skipped (required params not satisfiable safely)", "SKIP"
    except SystemExit as e:
        code = int(getattr(e, "code", 0) or 0)
        ok = code == 0
        return ok, "SystemExit(callable)", f"SystemExit(code={code})"
    except Exception as ex:
        return False, "callable exception", f"{type(ex).__name__}: {ex}"

    return False, "no-call-path", "SKIP"


def main() -> int:
    ap = argparse.ArgumentParser(prog="agno_entrypoint_exec")
    ap.add_argument(
        "--config",
        default="config/agno/runtime_entrypoint.json",
        help="Caminho para config/agno/runtime_entrypoint.json",
    )
    ap.add_argument("--mode", choices=["probe", "step"], default="probe")
    ap.add_argument("--payload-json", default="{}", help="JSON string do payload (default: {})")
    ap.add_argument("--task-id", default="UNKNOWN_TASK")
    ap.add_argument("--step-id", default="UNKNOWN_STEP")
    ap.add_argument("--out", required=True, help="Arquivo artifact de saída (txt)")
    args = ap.parse_args()

    out_path = Path(args.out)
    cfg_path = Path(args.config)

    header = []
    header.append(f"UTC: {utc_now()}")
    header.append(f"TASK_ID: {args.task_id}")
    header.append(f"STEP_ID: {args.step_id}")
    header.append(f"MODE: {args.mode}")
    header.append(f"CONFIG: {cfg_path}")
    header.append("")

    try:
        payload = json.loads(args.payload_json)
        if not isinstance(payload, dict):
            payload = {"payload": payload}
    except Exception:
        payload = {"payload_parse_error": True, "raw": args.payload_json}

    body = []
    rc = 0

    try:
        fqn = load_selected_fqn(cfg_path)
        obj = import_fqn(fqn)

        body.append(f"SELECTED_FQN: {fqn}")
        body.append(f"OBJ_TYPE: {type(obj)}")
        body.append(f"SIGNATURE: {signature_str(obj)}")
        body.append(f"PAYLOAD_KEYS: {sorted(list(payload.keys()))}")
        body.append("")

        called_ok, strategy, outcome = try_call(obj, payload)

        body.append(f"CALL_ATTEMPTED: {strategy}")
        body.append(f"CALL_OUTCOME: {outcome}")
        body.append(f"CALL_OK: {called_ok}")

        if args.mode == "probe":
            rc = 0
        else:
            rc = 0 if called_ok else 2

    except Exception as ex:
        rc = 2
        body.append("ERROR: exception")
        body.append(f"TYPE: {type(ex).__name__}")
        body.append(f"MSG: {ex}")
        body.append("")
        body.append("TRACEBACK:")
        body.append(traceback.format_exc())

    text = "\n".join(header + body) + "\n"
    write_text(out_path, text)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
