from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable, Mapping


class PackageError(ValueError):
    """Fail-closed package ecosystem validation error."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def content_hash(data: bytes) -> str:
    return "sha256:" + sha256(data).hexdigest()


@dataclass(frozen=True, order=True)
class Dependency:
    name: str
    version: str
    source: str

    def __post_init__(self) -> None:
        if not self.name or "/" in self.name or "\\" in self.name or ".." in self.name:
            raise PackageError("geçersiz paket adı")
        if not self.version:
            raise PackageError("sürüm zorunludur")
        if not self.source.startswith("https://"):
            raise PackageError("paket kaynağı güvenli https kökeni olmalıdır")


@dataclass(frozen=True)
class PackageManifest:
    name: str
    version: str
    dependencies: tuple[Dependency, ...] = ()

    def __post_init__(self) -> None:
        Dependency(self.name, self.version, "https://manifest.invalid")
        names = [item.name for item in self.dependencies]
        if len(names) != len(set(names)):
            raise PackageError("aynı bağımlılık birden fazla kez tanımlanamaz")

    def canonical_bytes(self) -> bytes:
        return _canonical_bytes(
            {
                "name": self.name,
                "version": self.version,
                "dependencies": [
                    {"name": item.name, "source": item.source, "version": item.version}
                    for item in sorted(self.dependencies)
                ],
            }
        )


@dataclass(frozen=True, order=True)
class RegistryPackage:
    name: str
    version: str
    source: str
    archive_hash: str

    def __post_init__(self) -> None:
        Dependency(self.name, self.version, self.source)
        if not self.archive_hash.startswith("sha256:") or len(self.archive_hash) != 71:
            raise PackageError("geçersiz paket bütünlük özeti")


@dataclass(frozen=True, order=True)
class LockEntry:
    name: str
    version: str
    source: str
    archive_hash: str


@dataclass(frozen=True)
class Lockfile:
    manifest_hash: str
    packages: tuple[LockEntry, ...]

    def canonical_bytes(self) -> bytes:
        return _canonical_bytes(
            {
                "manifest_hash": self.manifest_hash,
                "packages": [
                    {
                        "archive_hash": item.archive_hash,
                        "name": item.name,
                        "source": item.source,
                        "version": item.version,
                    }
                    for item in sorted(self.packages)
                ],
            }
        )


def resolve_manifest(
    manifest: PackageManifest,
    registry: Mapping[str, Iterable[RegistryPackage]],
) -> Lockfile:
    locked: list[LockEntry] = []
    for dep in sorted(manifest.dependencies):
        candidates = [
            item
            for item in registry.get(dep.name, ())
            if item.version == dep.version and item.source == dep.source
        ]
        if len(candidates) != 1:
            raise PackageError(f"bağımlılık güvenle çözümlenemedi: {dep.name}")
        chosen = candidates[0]
        locked.append(LockEntry(chosen.name, chosen.version, chosen.source, chosen.archive_hash))
    return Lockfile(content_hash(manifest.canonical_bytes()), tuple(sorted(locked)))


def verify_archive(data: bytes, expected_hash: str) -> None:
    if content_hash(data) != expected_hash:
        raise PackageError("paket bütünlük doğrulaması başarısız")
