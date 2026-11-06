"""Attest an isolated test environment, without claiming a separate host."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import site
import subprocess
import sys
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--expected-prefix", type=Path, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    import nocturne
    import nocturne_native
    packages = {}
    for line in (source / "requirements/windows-py314.lock.txt").read_text().splitlines():
        if line and not line.startswith("#"):
            name, expected = line.split("==")
            observed = importlib.metadata.version(name)
            packages[name] = {"expected": expected, "observed": observed, "match": expected == observed}
    suites = list(ET.parse(args.junit).getroot().iter("testsuite"))
    tests = {key: sum(int(s.attrib.get(key, 0)) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
    checks = {"fresh_venv": sys.prefix != sys.base_prefix and Path(sys.prefix).resolve() == args.expected_prefix.resolve(),
              "user_site_disabled": not site.ENABLE_USER_SITE,
              "package_from_clean_source": Path(nocturne.__file__).resolve().is_relative_to(source / "src"),
              "native_from_clean_build": Path(nocturne_native.__file__).resolve().is_relative_to(source / "native/build"),
              "all_pins_match": all(p["match"] for p in packages.values()),
              "tests_passed": tests["tests"] > 0 and tests["failures"] == tests["errors"] == tests["skipped"] == 0}
    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "status": "VERIFIED_FRESH_ENVIRONMENT_SAME_HOST" if all(checks.values()) else "ENVIRONMENT_CHECK_FAILED",
              "checks": checks, "python": sys.version, "prefix": sys.prefix, "base_prefix": sys.base_prefix,
              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip(),
              "package_path": nocturne.__file__, "native_path": nocturne_native.__file__,
              "tests": tests, "dependencies": packages,
              "limits": "New venv, independent Git clone and native build; same Windows host, OS runtime and installed MSVC/SDK. No off-host restore, service-account or reboot test."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "checks": checks, "tests": tests}))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
