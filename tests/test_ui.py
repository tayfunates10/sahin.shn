from dataclasses import FrozenInstanceError

import pytest

from sahin.ui import (
    Gorunum,
    GuvenliMetin,
    HamIcerik,
    Olcu,
    Rol,
    UiError,
    baslik,
    ekran,
    eylem,
    kart,
    metin,
)


def test_render_ir_host_independent_ve_deterministik():
    urun = kart(
        "urun-1",
        baslik("urun-ad", "Kahve"),
        metin("urun-fiyat", "120 TRY"),
        eylem("satinal", "Satın al", "satınAl", veri={"id": 1}),
    ).gorunumle(ic_bosluk=Olcu(2), bosluk=Olcu(1))

    ir = ekran("ana", urun, etiket="Ürünler")
    assert ir.sozluk() == {
        "sürüm": 1,
        "kök": {
            "kimlik": "ana",
            "rol": "ekran",
            "odaklanabilir": False,
            "etiket": "Ürünler",
            "çocuklar": [
                {
                    "kimlik": "urun-1",
                    "rol": "bölüm",
                    "odaklanabilir": False,
                    "görünüm": {
                        "boşluk": {"değer": 1, "birim": "adım"},
                        "iç_bosluk": {"değer": 2, "birim": "adım"},
                    },
                    "çocuklar": [
                        {"kimlik": "urun-ad", "rol": "başlık", "odaklanabilir": False, "içerik": "Kahve"},
                        {"kimlik": "urun-fiyat", "rol": "metin", "odaklanabilir": False, "içerik": "120 TRY"},
                        {
                            "kimlik": "satinal",
                            "rol": "eylem",
                            "odaklanabilir": True,
                            "etiket": "Satın al",
                            "olaylar": [{"ad": "etkinleştir", "akış": "satınAl", "veri": {"id": 1}}],
                        },
                    ],
                }
            ],
        },
    }


def test_dugumler_immutable():
    node = metin("m", "değer")
    with pytest.raises(FrozenInstanceError):
        node.icerik = "başka"


def test_unicode_nfc_kimlik_ve_icerik():
    node = metin("C\u0327ag\u0306rı", "S\u0327ahin")
    assert node.kimlik == "Çağrı"
    assert node.icerik == "Şahin"


def test_eylem_erisilebilir_etiket_ve_focus_sozlesmesi():
    node = eylem("kaydet", "Kaydet", "kaydet")
    assert node.rol is Rol.EYLEM
    assert node.odaklanabilir is True
    assert node.etiket == "Kaydet"


def test_erisilebilir_etiketsiz_eylem_reddedilir():
    from sahin.ui import Dugum

    with pytest.raises(UiError, match="SHN-U106"):
        Dugum("bozuk", Rol.EYLEM)


def test_global_yinelenen_kimlik_reddedilir():
    a = kart("a", metin("ortak", "bir"))
    b = kart("b", metin("ortak", "iki"))
    with pytest.raises(UiError, match="SHN-U109"):
        ekran("ana", a, b)


def test_guvenli_metin_host_adapterinda_kacirilir():
    metin_degeri = GuvenliMetin('<img src=x onerror="alert(1)">')
    assert metin_degeri.host_metni() == "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;"


def test_ham_icerik_varsayilan_kapali():
    with pytest.raises(UiError, match="SHN-U108"):
        HamIcerik("<b>ham</b>")
    assert HamIcerik("<b>ham</b>", izin=True).deger == "<b>ham</b>"


def test_gorunum_selector_ve_dom_degildir():
    style = Gorunum(bosluk=Olcu(1), hizalama="orta", vurgu="ana")
    assert style.bosluk == Olcu(1)
    assert style.hizalama == "orta"
    with pytest.raises(UiError, match="SHN-U103"):
        Gorunum(hizalama="justify-content")


def test_gecersiz_olcu_reddedilir():
    with pytest.raises(UiError, match="SHN-U101"):
        Olcu(-1)
    with pytest.raises(UiError, match="SHN-U102"):
        Olcu(1, "rem")
