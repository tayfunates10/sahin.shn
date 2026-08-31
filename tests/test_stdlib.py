from datetime import datetime, timezone

import pytest

from sahin.capabilities import Capability, CapabilityError, CapabilitySet
from sahin.stdlib import Ag, An, CozumlemeHatasi, Dosya, Guven, Json, Koleksiyon, Metin, Sayi, StdlibError, VeriSiniriHatasi


def test_metin_nfc_ve_islemler():
    ayrik = "C\u0327ag\u0306rı"
    assert Metin.duzelt(ayrik) == "Çağrı"
    assert Metin.uzunluk(ayrik) == 5
    assert Metin.bol("a,b,c", ",") == ["a", "b", "c"]
    assert Metin.birlestir(["Şa", "hin"], "") == "Şahin"
    assert Metin.ara("merhaba şahin", "şahin") == 8
    assert Metin.ara("merhaba", "yok") is None


def test_sayi_para_aralik():
    assert str(Sayi.yuvarla("12.345", 2)) == "12.35"
    assert Sayi.para("12.3") == "12.30 TRY"
    assert Sayi.aralik(1, 5) == [1, 2, 3, 4]
    with pytest.raises(StdlibError, match="SHN-S104"):
        Sayi.aralik(1, 5, 0)


def test_koleksiyon_deterministik():
    assert Koleksiyon.sec([1, 2, 3, 4], lambda x: x % 2 == 0) == [2, 4]
    assert Koleksiyon.donustur([1, 2], lambda x: x * 3) == [3, 6]
    assert Koleksiyon.sirala([3, 1, 2]) == [1, 2, 3]
    assert Koleksiyon.ilk([]) is None
    assert Koleksiyon.son([1, 2, 3]) == 3
    assert Koleksiyon.tekillestir([2, 1, 2, 1, 3]) == [2, 1, 3]
    assert Koleksiyon.grupla([1, 2, 3, 4], lambda x: x % 2) == {1: [1, 3], 0: [2, 4]}


def test_an_deterministik_saat():
    sabit = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
    an = An.simdi(saat=lambda: sabit)
    assert an.iso() == "2026-08-31T12:00:00+00:00"
    assert an.ekle(saniye=30).iso() == "2026-08-31T12:00:30+00:00"


def test_json_guvenli_cozumleme_ve_sinir():
    assert Json.coz('{"ad":"Şahin"}') == {"ad": "Şahin"}
    assert Json.yaz({"b": 1, "a": "Şahin"}) == '{"a":"Şahin","b":1}'
    with pytest.raises(CozumlemeHatasi, match="SHN-J103"):
        Json.coz("{")
    with pytest.raises(VeriSiniriHatasi, match="SHN-J102"):
        Json.coz("{}", sinir=1)


def test_dosya_varsayilan_kapali(tmp_path):
    yol = tmp_path / "ornek.txt"
    yetkiler = CapabilitySet()
    with pytest.raises(CapabilityError, match="SHN-G001"):
        Dosya.yaz(yol, "Şahin", yetkiler)
    with pytest.raises(CapabilityError, match="SHN-G001"):
        Dosya.oku(yol, yetkiler)

    yetkiler.grant(Capability.DOSYA_YAZ)
    Dosya.yaz(yol, "S\u0327ahin", yetkiler)
    assert yol.read_text(encoding="utf-8") == "Şahin"

    yetkiler.grant(Capability.DOSYA_OKU)
    assert Dosya.oku(yol, yetkiler) == "Şahin"


def test_dosya_boyut_siniri(tmp_path):
    yol = tmp_path / "buyuk.txt"
    yol.write_text("abcdef", encoding="utf-8")
    yetkiler = CapabilitySet({Capability.DOSYA_OKU})
    with pytest.raises(VeriSiniriHatasi, match="SHN-D102"):
        Dosya.oku(yol, yetkiler, sinir=3)


def test_ag_capability_agdan_once_reddedilir(monkeypatch):
    cagrildi = False

    def sahte(*args, **kwargs):
        nonlocal cagrildi
        cagrildi = True
        raise AssertionError("ağ çağrılmamalı")

    monkeypatch.setattr("urllib.request.urlopen", sahte)
    with pytest.raises(CapabilityError, match="SHN-G001"):
        Ag.getir("https://example.invalid", CapabilitySet())
    assert cagrildi is False


def test_ag_parametre_koruma():
    yetkiler = CapabilitySet({Capability.AG})
    with pytest.raises(StdlibError, match="SHN-A101"):
        Ag.getir("file:///etc/passwd", yetkiler)
    with pytest.raises(StdlibError, match="SHN-A102"):
        Ag.getir("https://example.invalid", yetkiler, zaman_asimi=0)


def test_guven_yuksek_seviye_api():
    assert len(Guven.rastgele_bayt(32)) == 32
    assert len(Guven.ozet("Şahin")) == 64
    anahtar = b"0123456789abcdef"
    imza = Guven.imza("veri", anahtar)
    assert Guven.imza_dogrula("veri", anahtar, imza)
    assert not Guven.imza_dogrula("degisik", anahtar, imza)
    with pytest.raises(StdlibError, match="SHN-K102"):
        Guven.ozet("x", algoritma="md5")
    with pytest.raises(StdlibError, match="SHN-K103"):
        Guven.imza("x", b"kisa")
