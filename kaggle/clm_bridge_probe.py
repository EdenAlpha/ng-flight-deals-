#!/usr/bin/env python3
"""Kaggle-side probe for the CLM remote-compute bridge.

Runs inside a private Kaggle kernel. It deliberately contains no credentials.
The GitHub workflow authenticates to Kaggle, launches this kernel, waits for it,
and pulls the resulting JSON back as a GitHub Actions artifact.
"""
from __future__ import annotations

import json
import os
import platform
import time
from pathlib import Path


def main() -> None:
    gpu = {
        "torch_available": False,
        "cuda_available": False,
        "device_count": 0,
        "devices": [],
    }
    try:
        import torch
        gpu["torch_available"] = True
        gpu["cuda_available"] = bool(torch.cuda.is_available())
        gpu["device_count"] = int(torch.cuda.device_count())
        gpu["devices"] = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
    except Exception as exc:
        gpu["torch_error"] = repr(exc)

    report = {
        "bridge": "github-actions -> kaggle-kernel -> github-actions",
        "ok": True,
        "unix_time": time.time(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "kaggle_kernel_run_type": os.environ.get("KAGGLE_KERNEL_RUN_TYPE"),
        "gpu": gpu,
        "working_dir": str(Path.cwd()),
    }

    out = Path("/kaggle/working/kaggle_bridge_status.json")
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
