#!/usr/bin/env python3
"""Start the local API and frontend together for development."""

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROCESSES: list[subprocess.Popen] = []
STOP_REQUESTED = False


def request_stop(_signum: int, _frame: object) -> None:
    global STOP_REQUESTED
    STOP_REQUESTED = True


def stop_processes() -> None:
    for process in PROCESSES:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    deadline = time.monotonic() + 5
    for process in PROCESSES:
        try:
            process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()


def main() -> int:
    for command in ("uv", "pnpm"):
        if shutil.which(command) is None:
            print(f"Comando não encontrado: {command}. Instale-o antes de iniciar o projeto.", file=sys.stderr)
            return 1

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    try:
        PROCESSES.append(
            subprocess.Popen(
                ["uv", "run", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1"],
                cwd=ROOT / "backend",
                start_new_session=True,
            )
        )
        PROCESSES.append(
            subprocess.Popen(
                ["pnpm", "dev"],
                cwd=ROOT / "frontend",
                start_new_session=True,
            )
        )
        print("API: http://127.0.0.1:8000/docs", flush=True)
        print("Site: http://127.0.0.1:5173", flush=True)
        print("Pressione Ctrl+C para encerrar ambos.", flush=True)

        while not STOP_REQUESTED:
            for name, process in zip(("Backend", "Frontend"), PROCESSES):
                result = process.poll()
                if result is not None:
                    print(f"{name} encerrou (código {result}).", file=sys.stderr)
                    return result or 1
            time.sleep(0.2)
        return 0
    except OSError as exc:
        print(f"Não foi possível iniciar o ambiente: {exc}", file=sys.stderr)
        return 1
    finally:
        stop_processes()


if __name__ == "__main__":
    raise SystemExit(main())
