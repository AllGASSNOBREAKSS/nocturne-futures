"""Offline installed-integrity, environment and issued-quantile verification."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import site
import sys

from nocturne.runtime_integrity import exact_pins, file_hash, verify_installed, verify_frozen_inference
from nocturne.shadow import load_artifact

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--native", action="store_true")
    args = parser.parse_args()
    root = args.repository.resolve()
    if sys.prefix == sys.base_prefix or site.ENABLE_USER_SITE:
        raise ValueError("isolated venv with disabled user site required")
    import nocturne
    if not Path(nocturne.__file__).resolve().is_relative_to(root / "src"):
        raise ValueError("package does not originate from requested deployment source")
    pins = exact_pins([root / "requirements/windows-py314.lock.txt", root / "requirements/windows-py314-build.lock.txt"])
    integrity = verify_installed(pins, sys.prefix)
    artifact = load_artifact(root / "models/shadow", "ndx-range-v1")
    forecasts = [json.loads(line) for line in (root / "data/shadow/ndx_range/forecasts.jsonl").read_text().splitlines() if line.strip()]
    parity = verify_frozen_inference(artifact, forecasts)
    native = {"status": "NOT_REQUESTED"}
    if args.native:
        sys.path.insert(0, str(root / "native/build"))
        import nocturne_native
        path = Path(nocturne_native.__file__).resolve()
        if not path.is_relative_to(root / "native/build"):
            raise ValueError("wrong native module origin")
        cache = root / "native/build/CMakeCache.txt"
        prefixes = ("CMAKE_BUILD_TYPE:", "CMAKE_CXX_COMPILER:", "CMAKE_CXX_FLAGS", "CMAKE_GENERATOR:", "PYTHON_EXECUTABLE:")
        native = {"status": "IMPORTED_FRESH_BUILD", "binary_sha256": file_hash(path),
                  "cmake_configuration": [line for line in cache.read_text().splitlines() if line.startswith(prefixes)],
                  "limits": "Binary hash identifies this build; not bitwise reproducibility across compilers/hosts."}
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "status": "VERIFIED_ISOLATED_RUNTIME",
              "python": sys.version, "platform": platform.platform(), "prefix": sys.prefix,
              "pip_version": __import__("importlib.metadata", fromlist=["version"]).version("pip"),
              "dependency_integrity": integrity, "inference_parity": parity, "native": native,
              "network_requests": 0, "new_models_trained": 0, "promotion": "NO_PROMOTION", "trading_decision": "NO_TRADE"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "dependency_files": integrity["files"], "inference_cases": len(parity["records"]), "native": native["status"]}))


if __name__ == "__main__":
    main()
