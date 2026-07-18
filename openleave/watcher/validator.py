"""Validate a proposed parameter change against the regression suite.

The proposed diff is written to a temporary overrides file and the full pytest
suite runs in a subprocess with OPENLEAVE_PARAM_OVERRIDES pointing at it. The
suite pins historic determinations to as-of dates, so a diff that silently
rewrites the past fails here — only additive, forward-dated changes pass.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .. import parameters

REPO_ROOT = Path(__file__).resolve().parents[2]


def validate(overrides: dict[str, list[list]]) -> dict:
    result: dict = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "overrides": overrides,
        "passed": False,
        "detail": "",
    }

    unknown = [k for k in overrides if k not in parameters.known_keys()]
    if unknown:
        result["detail"] = f"Unknown parameter keys: {unknown} — a logic change or a hallucinated key."
        return result

    if not overrides:
        result["passed"] = True
        result["detail"] = "No parameter changes to validate."
        return result

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(overrides, f)
        overrides_path = f.name

    # The regression contract is the determination suite; the watcher's own
    # tests are excluded so validation can't recurse into itself.
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_regimes.py", "tests/test_api.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "OPENLEAVE_PARAM_OVERRIDES": overrides_path},
    )
    result["passed"] = proc.returncode == 0
    tail = (proc.stdout or proc.stderr).strip().splitlines()
    result["detail"] = "\n".join(tail[-5:])
    return result
