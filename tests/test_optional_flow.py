import unittest

from sahin.optional_flow import FlowTypeEnvironment, parse_type_spec
from sahin.semantics import TypeKind
from sahin.type_model import TypeSpec


class OptionalFlowTests(unittest.TestCase):
    def test_parse_optional_type_name(self):
        spec = parse_type_spec("yazı veya yok")
        self.assertEqual(spec.members, frozenset({TypeKind.YAZI, TypeKind.YOK}))
        self.assertEqual(spec.display(), "yazı veya yok")

    def test_unknown_type_name_is_safe(self):
        self.assertTrue(parse_type_spec("bilinmeyen_tür").is_unknown)

    def test_yok_branch_narrows_both_paths(self):
        env = FlowTypeEnvironment({"müşteri": TypeSpec.optional(TypeKind.YAZI)})
        yes, no = env.branch_for_yok("müşteri")
        self.assertEqual(yes.resolve("müşteri").members, frozenset({TypeKind.YOK}))
        self.assertEqual(no.resolve("müşteri").members, frozenset({TypeKind.YAZI}))

    def test_member_access_requires_narrowing(self):
        env = FlowTypeEnvironment({"müşteri": TypeSpec.optional(TypeKind.YAZI)})
        diagnostic = env.member_access_diagnostic("müşteri")
        self.assertIsNotNone(diagnostic)
        self.assertEqual(diagnostic.code, "SHN-T302")

        _, present = env.branch_for_yok("müşteri")
        self.assertIsNone(present.member_access_diagnostic("müşteri"))

    def test_optional_assignment_accepts_present_and_yok(self):
        env = FlowTypeEnvironment({"değer": TypeSpec.optional(TypeKind.SAYI)})
        self.assertIsNone(env.assign("değer", TypeSpec.of(TypeKind.SAYI)))
        self.assertIsNone(env.assign("değer", TypeSpec.of(TypeKind.YOK)))

    def test_optional_assignment_rejects_unrelated_type(self):
        env = FlowTypeEnvironment({"değer": TypeSpec.optional(TypeKind.SAYI)})
        diagnostic = env.assign("değer", TypeSpec.of(TypeKind.YAZI))
        self.assertIsNotNone(diagnostic)
        self.assertEqual(diagnostic.code, "SHN-T203")


if __name__ == "__main__":
    unittest.main()
