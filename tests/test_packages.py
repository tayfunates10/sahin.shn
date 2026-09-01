import pytest

from sahin.packages import (
    Dependency,
    PackageError,
    PackageManifest,
    RegistryPackage,
    content_hash,
    resolve_manifest,
    verify_archive,
)


def pkg(name: str, version: str, source: str, payload: bytes) -> RegistryPackage:
    return RegistryPackage(name, version, source, content_hash(payload))


def test_manifest_and_lockfile_are_deterministic():
    a = Dependency("alfa", "1.0.0", "https://paket.sahin.dev")
    b = Dependency("beta", "2.0.0", "https://paket.sahin.dev")
    first = PackageManifest("uygulama", "0.1.0", (b, a))
    second = PackageManifest("uygulama", "0.1.0", (a, b))
    registry = {
        "alfa": [pkg("alfa", "1.0.0", a.source, b"alfa")],
        "beta": [pkg("beta", "2.0.0", b.source, b"beta")],
    }
    assert first.canonical_bytes() == second.canonical_bytes()
    assert resolve_manifest(first, registry).canonical_bytes() == resolve_manifest(second, registry).canonical_bytes()


def test_dependency_confusion_source_mismatch_fails_closed():
    dep = Dependency("hesap", "1.0.0", "https://kurum.example")
    manifest = PackageManifest("uygulama", "0.1.0", (dep,))
    registry = {"hesap": [pkg("hesap", "1.0.0", "https://saldirgan.example", b"x")]}
    with pytest.raises(PackageError):
        resolve_manifest(manifest, registry)


def test_ambiguous_duplicate_candidate_fails_closed():
    dep = Dependency("hesap", "1.0.0", "https://kurum.example")
    item = pkg("hesap", "1.0.0", dep.source, b"x")
    with pytest.raises(PackageError):
        resolve_manifest(PackageManifest("uygulama", "0.1.0", (dep,)), {"hesap": [item, item]})


def test_path_traversal_like_package_name_is_rejected():
    with pytest.raises(PackageError):
        Dependency("../gizli", "1.0.0", "https://paket.sahin.dev")


def test_archive_integrity_is_verified_before_use():
    expected = content_hash(b"dogru")
    verify_archive(b"dogru", expected)
    with pytest.raises(PackageError):
        verify_archive(b"bozuk", expected)
