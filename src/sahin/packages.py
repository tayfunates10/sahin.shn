from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
import re
from typing import Iterable, Mapping, Protocol


class PackageError(ValueError):
    """Fail-closed package ecosystem validation error."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def content_hash(data: bytes) -> str:
    return "sha256:" + sha256(data).hexdigest()


_VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, raw: str) -> "Version":
        match = _VERSION_RE.fullmatch(raw)
        if match is None:
            raise PackageError("sürüm X.Y.Z biçiminde olmalıdır")
        return cls(*(int(part) for part in match.groups()))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class VersionConstraint:
    raw: str

    def __post_init__(self) -> None:
        if not self.raw:
            raise PackageError("sürüm kuralı zorunludur")
        prefix = self.raw[0] if self.raw[0] in "^~" else ""
        Version.parse(self.raw[1:] if prefix else self.raw)

    def accepts(self, version: str) -> bool:
        target = Version.parse(version)
        prefix = self.raw[0] if self.raw[0] in "^~" else ""
        base = Version.parse(self.raw[1:] if prefix else self.raw)
        if not prefix:
            return target == base
        if prefix == "~":
            return target.major == base.major and target.minor == base.minor and target >= base
        if base.major > 0:
            return target.major == base.major and target >= base
        if base.minor > 0:
            return target.major == 0 and target.minor == base.minor and target >= base
        return target.major == 0 and target.minor == 0 and target.patch == base.patch


@dataclass(frozen=True, order=True)
class Dependency:
    name: str
    version: str
    source: str

    def __post_init__(self) -> None:
        if not self.name or "/" in self.name or "\\" in self.name or ".." in self.name:
            raise PackageError("geçersiz paket adı")
        VersionConstraint(self.version)
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
        Version.parse(self.version)
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


class RegistryAdapter(Protocol):
    def candidates(self, name: str, source: str) -> Iterable[RegistryPackage]:
        """Return candidates only for the explicitly requested provenance."""


@dataclass(frozen=True)
class MappingRegistryAdapter:
    packages: Mapping[str, Iterable[RegistryPackage]]

    def candidates(self, name: str, source: str) -> Iterable[RegistryPackage]:
        return tuple(item for item in self.packages.get(name, ()) if item.source == source)


def _adapter_for(
    registry: Mapping[str, Iterable[RegistryPackage]] | RegistryAdapter,
) -> RegistryAdapter:
    if isinstance(registry, Mapping):
        return MappingRegistryAdapter(registry)
    return registry


def resolve_manifest(
    manifest: PackageManifest,
    registry: Mapping[str, Iterable[RegistryPackage]] | RegistryAdapter,
) -> Lockfile:
    adapter = _adapter_for(registry)
    locked: list[LockEntry] = []
    for dep in sorted(manifest.dependencies):
        constraint = VersionConstraint(dep.version)
        candidates = [
            item
            for item in adapter.candidates(dep.name, dep.source)
            if item.name == dep.name and item.source == dep.source and constraint.accepts(item.version)
        ]
        if not candidates:
            raise PackageError(f"bağımlılık güvenle çözümlenemedi: {dep.name}")
        by_version: dict[Version, list[RegistryPackage]] = {}
        for item in candidates:
            by_version.setdefault(Version.parse(item.version), []).append(item)
        selected_version = max(by_version)
        selected = by_version[selected_version]
        if len(selected) != 1:
            raise PackageError(f"bağımlılık güvenle çözümlenemedi: {dep.name}")
        chosen = selected[0]
        locked.append(LockEntry(chosen.name, chosen.version, chosen.source, chosen.archive_hash))
    return Lockfile(content_hash(manifest.canonical_bytes()), tuple(sorted(locked)))


def verify_archive(data: bytes, expected_hash: str) -> None:
    if content_hash(data) != expected_hash:
        raise PackageError("paket bütünlük doğrulaması başarısız")


@dataclass(frozen=True)
class PackageSignature:
    signer: str
    archive_hash: str
    algorithm: str
    value: str

    def __post_init__(self) -> None:
        if not self.signer:
            raise PackageError("imzalayan kimliği zorunludur")
        if self.algorithm != "hmac-sha256":
            raise PackageError("desteklenmeyen paket imza algoritması")
        if not self.archive_hash.startswith("sha256:") or len(self.archive_hash) != 71:
            raise PackageError("imza bütünlük özeti geçersiz")
        if not self.value.startswith("hmac-sha256:") or len(self.value) != 76:
            raise PackageError("paket imzası geçersiz")


@dataclass(frozen=True)
class TrustStore:
    trusted_signers: Mapping[str, bytes]
    revoked_signers: frozenset[str] = frozenset()

    def key_for(self, signer: str) -> bytes:
        if signer in self.revoked_signers:
            raise PackageError("paket imzalayanı iptal edilmiş")
        key = self.trusted_signers.get(signer)
        if key is None:
            raise PackageError("paket imzalayanı güvenilir değil")
        if not key:
            raise PackageError("boş güven anahtarı kabul edilmez")
        return key


def sign_archive(data: bytes, signer: str, key: bytes) -> PackageSignature:
    if not key:
        raise PackageError("boş imza anahtarı kabul edilmez")
    archive_hash = content_hash(data)
    digest = hmac.new(key, archive_hash.encode("ascii"), sha256).hexdigest()
    return PackageSignature(signer, archive_hash, "hmac-sha256", "hmac-sha256:" + digest)


def verify_signed_archive(data: bytes, signature: PackageSignature, trust: TrustStore) -> None:
    verify_archive(data, signature.archive_hash)
    key = trust.key_for(signature.signer)
    expected = sign_archive(data, signature.signer, key)
    if not hmac.compare_digest(expected.value, signature.value):
        raise PackageError("paket imza doğrulaması başarısız")


@dataclass(frozen=True)
class CachedPackage:
    package: RegistryPackage
    archive: bytes
    signature: PackageSignature


class PackageCache:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str, str], CachedPackage] = {}

    @staticmethod
    def _key(package: RegistryPackage) -> tuple[str, str, str]:
        return (package.name, package.version, package.source)

    def put_verified(self, entry: CachedPackage, trust: TrustStore) -> None:
        verify_archive(entry.archive, entry.package.archive_hash)
        if entry.signature.archive_hash != entry.package.archive_hash:
            raise PackageError("paket metadata ve imza özeti uyuşmuyor")
        verify_signed_archive(entry.archive, entry.signature, trust)
        self._entries[self._key(entry.package)] = entry

    def get_offline(self, package: RegistryPackage, trust: TrustStore) -> bytes:
        entry = self._entries.get(self._key(package))
        if entry is None:
            raise PackageError("paket offline cache içinde yok")
        if entry.package.archive_hash != package.archive_hash:
            raise PackageError("offline cache paket özeti lockfile ile uyuşmuyor")
        verify_archive(entry.archive, package.archive_hash)
        verify_signed_archive(entry.archive, entry.signature, trust)
        return entry.archive


class InstallStore:
    """Atomic in-memory install state with optimistic transaction versioning."""

    def __init__(self, installed: Mapping[str, LockEntry] | None = None) -> None:
        self._installed = dict(installed or {})
        self._revision = 0

    @property
    def installed(self) -> Mapping[str, LockEntry]:
        return dict(self._installed)

    def transaction(self) -> "InstallTransaction":
        return InstallTransaction(self)


class InstallTransaction:
    def __init__(self, store: InstallStore) -> None:
        self._store = store
        self._base_revision = store._revision
        self._staged = dict(store._installed)
        self._finished = False

    def stage(self, entry: LockEntry) -> None:
        if self._finished:
            raise PackageError("paket işlemi tamamlandı")
        self._staged[entry.name] = entry

    def commit(self) -> None:
        if self._finished:
            raise PackageError("paket işlemi tamamlandı")
        if self._store._revision != self._base_revision:
            self._finished = True
            raise PackageError("paket kurulum durumu eşzamanlı işlem nedeniyle değişti")
        self._store._installed = dict(self._staged)
        self._store._revision += 1
        self._finished = True

    def rollback(self) -> None:
        if self._finished:
            raise PackageError("paket işlemi tamamlandı")
        # Staging is transaction-local, so rollback must never rewrite shared
        # store state or erase a newer transaction's committed install.
        self._finished = True

    def __enter__(self) -> "InstallTransaction":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self._finished:
            return False
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False
