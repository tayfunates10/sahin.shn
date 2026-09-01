import pytest

from sahin.packages import (
    CachedPackage,
    Dependency,
    InstallStore,
    LockEntry,
    MappingRegistryAdapter,
    PackageCache,
    PackageError,
    PackageManifest,
    PackageSignature,
    RegistryPackage,
    TrustStore,
    VersionConstraint,
    content_hash,
    resolve_manifest,
    sign_archive,
    verify_archive,
    verify_signed_archive,
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


def test_trusted_signature_verifies_and_tamper_fails_closed():
    archive = b"imzali-paket"
    trust = TrustStore({"resmi": b"test-only-secret"})
    signature = sign_archive(archive, "resmi", b"test-only-secret")
    verify_signed_archive(archive, signature, trust)
    with pytest.raises(PackageError):
        verify_signed_archive(archive + b"-bozuk", signature, trust)


def test_untrusted_and_revoked_signers_never_fallback():
    archive = b"paket"
    signature = sign_archive(archive, "resmi", b"secret")
    with pytest.raises(PackageError):
        verify_signed_archive(archive, signature, TrustStore({}))
    with pytest.raises(PackageError):
        verify_signed_archive(archive, signature, TrustStore({"resmi": b"secret"}, frozenset({"resmi"})))


def test_substituted_signature_is_rejected():
    archive = b"paket"
    signature = sign_archive(archive, "resmi", b"secret")
    forged = PackageSignature(signature.signer, signature.archive_hash, signature.algorithm, "hmac-sha256:" + "0" * 64)
    with pytest.raises(PackageError):
        verify_signed_archive(archive, forged, TrustStore({"resmi": b"secret"}))


def test_offline_cache_revalidates_integrity_signature_and_lock_identity():
    archive = b"cache-paketi"
    package = pkg("cache", "1.0.0", "https://paket.sahin.dev", archive)
    trust = TrustStore({"resmi": b"secret"})
    cache = PackageCache()
    entry = CachedPackage(package, archive, sign_archive(archive, "resmi", b"secret"))
    cache.put_verified(entry, trust)
    assert cache.get_offline(package, trust) == archive

    substituted = RegistryPackage(package.name, package.version, package.source, content_hash(b"baska"))
    with pytest.raises(PackageError):
        cache.get_offline(substituted, trust)


def test_offline_cache_missing_package_fails_closed():
    package = pkg("eksik", "1.0.0", "https://paket.sahin.dev", b"x")
    with pytest.raises(PackageError):
        PackageCache().get_offline(package, TrustStore({"resmi": b"secret"}))


def test_version_constraints_are_explicit_and_deterministic():
    assert VersionConstraint("^1.2.3").accepts("1.9.0")
    assert not VersionConstraint("^1.2.3").accepts("2.0.0")
    assert VersionConstraint("~1.2.3").accepts("1.2.9")
    assert not VersionConstraint("~1.2.3").accepts("1.3.0")
    with pytest.raises(PackageError):
        VersionConstraint("latest")


def test_compatible_resolution_selects_highest_matching_version():
    dep = Dependency("hesap", "^1.2.0", "https://kurum.example")
    registry = {
        "hesap": [
            pkg("hesap", "1.2.1", dep.source, b"a"),
            pkg("hesap", "1.9.0", dep.source, b"b"),
            pkg("hesap", "2.0.0", dep.source, b"c"),
        ]
    }
    lock = resolve_manifest(PackageManifest("uygulama", "0.1.0", (dep,)), registry)
    assert lock.packages[0].version == "1.9.0"


def test_registry_adapter_enforces_requested_provenance():
    dep = Dependency("hesap", "1.0.0", "https://kurum.example")
    adapter = MappingRegistryAdapter(
        {"hesap": [
            pkg("hesap", "1.0.0", dep.source, b"dogru"),
            pkg("hesap", "1.0.0", "https://saldirgan.example", b"yanlis"),
        ]}
    )
    lock = resolve_manifest(PackageManifest("uygulama", "0.1.0", (dep,)), adapter)
    assert lock.packages[0].source == dep.source


def test_install_transaction_rolls_back_on_error():
    old = LockEntry("hesap", "1.0.0", "https://kurum.example", content_hash(b"old"))
    new = LockEntry("hesap", "1.1.0", "https://kurum.example", content_hash(b"new"))
    store = InstallStore({"hesap": old})
    with pytest.raises(RuntimeError):
        with store.transaction() as tx:
            tx.stage(new)
            raise RuntimeError("kurulum hatası")
    assert store.installed["hesap"] == old


def test_install_transaction_commits_only_when_successful():
    new = LockEntry("hesap", "1.1.0", "https://kurum.example", content_hash(b"new"))
    store = InstallStore()
    with store.transaction() as tx:
        tx.stage(new)
    assert store.installed["hesap"] == new


def test_stale_rollback_never_erases_newer_committed_install():
    a = LockEntry("alfa", "1.0.0", "https://kurum.example", content_hash(b"a"))
    b = LockEntry("beta", "1.0.0", "https://kurum.example", content_hash(b"b"))
    store = InstallStore()
    older = store.transaction()
    newer = store.transaction()
    newer.stage(b)
    newer.commit()
    older.stage(a)
    older.rollback()
    assert store.installed == {"beta": b}


def test_stale_commit_fails_closed_instead_of_erasing_newer_state():
    a = LockEntry("alfa", "1.0.0", "https://kurum.example", content_hash(b"a"))
    b = LockEntry("beta", "1.0.0", "https://kurum.example", content_hash(b"b"))
    store = InstallStore()
    older = store.transaction()
    newer = store.transaction()
    newer.stage(b)
    newer.commit()
    older.stage(a)
    with pytest.raises(PackageError, match="eşzamanlı işlem"):
        older.commit()
    assert store.installed == {"beta": b}
