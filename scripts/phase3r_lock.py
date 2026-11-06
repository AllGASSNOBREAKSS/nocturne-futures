"""Generate a reviewed Windows wheel hash lock, or verify it offline by default."""
import argparse
from datetime import datetime, timezone
from email.parser import BytesParser
import json
from pathlib import Path
import zipfile

from nocturne.runtime_integrity import exact_pins, normalized_name, file_hash, verify_wheelhouse

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements/windows-py314.hashes.txt"
MANIFEST = ROOT / "requirements/windows-py314.wheels.json"
PIN_FILES = [ROOT / "requirements/windows-py314.lock.txt", ROOT / "requirements/windows-py314-build.lock.txt"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument('--profile', choices=('numerical', 'security'), default='numerical')
    parser.add_argument("--create", action="store_true", help="explicit first-time generation using public PyPI metadata; never overwrite")
    args = parser.parse_args()
    lock_path, manifest_path = LOCK, MANIFEST
    pin_files = list(PIN_FILES)
    if args.profile == 'security':
        lock_path = ROOT / 'requirements/windows-py314-security.hashes.txt'
        manifest_path = ROOT / 'requirements/windows-py314-security.wheels.json'
        pin_files.append(ROOT / 'requirements/windows-py314-security.lock.txt')
    pins = exact_pins(pin_files)
    if args.create:
        if lock_path.exists() or manifest_path.exists():
            raise ValueError("review existing lock; never overwrite it to approve an upgrade")
        import requests
        entries = []
        for path in sorted(args.wheelhouse.glob("*.whl")):
            with zipfile.ZipFile(path) as wheel:
                metadata_files = [n for n in wheel.namelist() if n.count("/") == 1 and n.endswith(".dist-info/METADATA")]
                if len(metadata_files) != 1:
                    raise ValueError("wheel metadata identity missing")
                if wheel.getinfo(metadata_files[0]).file_size > 1024 * 1024:
                    raise ValueError("wheel metadata budget exceeded")
                info = BytesParser().parsebytes(wheel.read(metadata_files[0]))
            name, version = normalized_name(info["Name"]), info["Version"]
            if pins.get(name) != version:
                raise ValueError("unrequested wheel in staging directory")
            response = requests.get(f"https://pypi.org/pypi/{name}/{version}/json", timeout=30)
            response.raise_for_status()
            candidates = [r for r in response.json()["urls"] if r["filename"] == path.name]
            if len(candidates) != 1:
                raise ValueError("exact wheel not listed by upstream")
            upstream = candidates[0]
            entries.append({"name": name, "version": version, "filename": path.name, "bytes": path.stat().st_size,
                            "sha256": file_hash(path), "pypi_sha256": upstream["digests"]["sha256"]})
            if path.stat().st_size != upstream["size"]:
                raise ValueError("upstream size mismatch")
        manifest = {"schema": 1, "target": "windows-x86_64-cpython-314", "created_at": datetime.now(timezone.utc).isoformat(),
                    "trust": "Exact bytes checked against current HTTPS PyPI release metadata; not signed publisher identity or malware assessment.",
                    "wheels": sorted(entries, key=lambda e: e["name"])}
        verify_wheelhouse(args.wheelhouse, manifest, pins)
        lines = ["# Windows x64 CPython 3.14 only; exact reviewed wheel bytes, no sdists."]
        lines += [f"{e['name']}=={e['version']} --hash=sha256:{e['sha256']}" for e in manifest["wheels"]]
        lock_path.write_text("\n".join(lines) + "\n")
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    manifest = json.loads(manifest_path.read_text())
    expected = [f"{e['name']}=={e['version']} --hash=sha256:{e['sha256']}" for e in manifest["wheels"]]
    observed = [line.strip() for line in lock_path.read_text().splitlines() if line and not line.startswith("#")]
    if expected != observed:
        raise ValueError("hash requirements differ from wheel manifest")
    result = verify_wheelhouse(args.wheelhouse, manifest, pins)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "result": result,
              "hash_lock_sha256": file_hash(lock_path), "manifest_sha256": file_hash(manifest_path)}
    name = 'phase3s_dependency_lock.json' if args.profile == 'security' else 'phase3r_dependency_lock.json'
    (ROOT / 'reports' / name).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
