import unittest

from sahin.ui import Gorunum, Olcu, UiError, baslik, eylem, ekran, metin
from sahin.ui_adapter import BrowserAdapter
from sahin.ui_state import (
    Durum,
    Esik,
    ResponsiveGorunum,
    ResponsiveKural,
    StateIslemi,
    TasarimTokenlari,
)


class UiStateResponsiveTests(unittest.TestCase):
    def test_design_tokens_are_deterministic_and_nfc_safe(self):
        tokens = TasarimTokenlari.kur(
            bosluklar={"orta": Olcu(2), "ku\u0308çu\u0308k": Olcu(1)},
            tipografi={"başlık": Olcu(3)},
            vurgular={"ana": "lacivert"},
        )
        self.assertEqual(tokens.bosluk("küçük"), Olcu(1))
        self.assertEqual(tokens.yazi("başlık"), Olcu(3))
        self.assertEqual(tokens.vurgu("ana"), "lacivert")
        self.assertEqual([name for name, _ in tokens.bosluklar], sorted(name for name, _ in tokens.bosluklar))

    def test_unknown_token_is_controlled_error(self):
        tokens = TasarimTokenlari.kur()
        with self.assertRaisesRegex(UiError, "SHN-U202"):
            tokens.bosluk("olmayan")

    def test_responsive_rules_merge_over_base(self):
        responsive = ResponsiveGorunum(
            temel=Gorunum(bosluk=Olcu(1), hizalama="baş"),
            kurallar=(
                ResponsiveKural(Esik("tablet", 600, 1023), Gorunum(bosluk=Olcu(2))),
                ResponsiveKural(Esik("geniş", 1024), Gorunum(bosluk=Olcu(3), hizalama="orta")),
            ),
        )
        self.assertEqual(responsive.coz(500).bosluk, Olcu(1))
        self.assertEqual(responsive.coz(700).bosluk, Olcu(2))
        self.assertEqual(responsive.coz(1200).bosluk, Olcu(3))
        self.assertEqual(responsive.coz(1200).hizalama, "orta")

    def test_invalid_breakpoints_fail_closed(self):
        with self.assertRaisesRegex(UiError, "SHN-U204"):
            Esik("bozuk", 900, 600)
        with self.assertRaisesRegex(UiError, "SHN-U205"):
            ResponsiveGorunum(
                kurallar=(
                    ResponsiveKural(Esik("aynı", 0, 10), Gorunum()),
                    ResponsiveKural(Esik("aynı", 11, 20), Gorunum()),
                )
            )

    def test_state_updates_are_immutable_versioned_and_guarded(self):
        once = Durum.kur({"sayaç": 1, "ad": "Şahin"})
        operation = StateIslemi("artır", frozenset({"sayaç"}))
        twice = operation.uygula(once, {"sayaç": 2}, beklenen_surum=0)

        self.assertEqual(once.al("sayaç"), 1)
        self.assertEqual(once.surum, 0)
        self.assertEqual(twice.al("sayaç"), 2)
        self.assertEqual(twice.surum, 1)

        with self.assertRaisesRegex(UiError, "SHN-U210"):
            operation.uygula(twice, {"ad": "değiştirilemez"})
        with self.assertRaisesRegex(UiError, "SHN-U207"):
            operation.uygula(twice, {"sayaç": 3}, beklenen_surum=0)

    def test_browser_adapter_is_structured_and_escapes_untrusted_text(self):
        ir = ekran(
            "ana",
            baslik("baslik", "<script>alert(1)</script>"),
            metin("metin", "A&B"),
            eylem("kaydet", 'Kaydet "şimdi"', "kaydetAkışı"),
            etiket="Ana ekran",
        )
        host = BrowserAdapter().aktar(ir)
        data = host.sozluk()

        self.assertEqual(data["tür"], "ekran")
        self.assertNotIn("<script>", str(data))
        self.assertIn("&lt;script&gt;", str(data))
        self.assertIn("A&amp;B", str(data))
        self.assertNotIn("<button", str(data))
        self.assertNotIn("<div", str(data))

    def test_browser_adapter_rejects_unknown_ir_version(self):
        ir = ekran("ana", metin("m", "merhaba"))
        from dataclasses import replace

        with self.assertRaisesRegex(UiError, "SHN-U301"):
            BrowserAdapter().aktar(replace(ir, surum=99))


if __name__ == "__main__":
    unittest.main()
