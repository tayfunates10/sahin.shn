import unittest

from sahin.semantics import TypeKind
from sahin.type_model import TypeSpec


class OptionalTypeModelTests(unittest.TestCase):
    def test_optional_type_is_explicitly_nullable(self):
        spec = TypeSpec.optional(TypeKind.YAZI)
        self.assertTrue(spec.is_optional)
        self.assertTrue(spec.can_be_yok)
        self.assertEqual(spec.display(), "yazı veya yok")

    def test_present_narrowing_removes_yok(self):
        spec = TypeSpec.optional(TypeKind.YAZI)
        narrowed = spec.narrowed_present()
        self.assertEqual(narrowed.members, frozenset({TypeKind.YAZI}))
        self.assertFalse(narrowed.can_be_yok)

    def test_join_preserves_all_possible_sahin_types(self):
        joined = TypeSpec.of(TypeKind.SAYI).joined(TypeSpec.of(TypeKind.YOK))
        self.assertEqual(joined.members, frozenset({TypeKind.SAYI, TypeKind.YOK}))
        self.assertEqual(joined.display(), "sayı veya yok")

    def test_optional_contract_rejects_unrelated_type(self):
        expected = TypeSpec.optional(TypeKind.YAZI)
        self.assertTrue(expected.accepts(TypeSpec.of(TypeKind.YAZI)))
        self.assertTrue(expected.accepts(TypeSpec.of(TypeKind.YOK)))
        self.assertFalse(expected.accepts(TypeSpec.of(TypeKind.SAYI)))

    def test_numeric_widening_is_preserved(self):
        self.assertTrue(TypeSpec.of(TypeKind.ONDALIK).accepts(TypeSpec.of(TypeKind.SAYI)))
        self.assertTrue(TypeSpec.optional(TypeKind.PARA).accepts(TypeSpec.of(TypeKind.SAYI)))

    def test_empty_type_is_forbidden(self):
        with self.assertRaises(ValueError):
            TypeSpec(frozenset())


if __name__ == "__main__":
    unittest.main()
