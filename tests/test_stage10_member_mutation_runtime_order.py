from sahin.ast_nodes import Command, Member, Name
from sahin.runtime import Runtime


class _RebindingAmountRuntime(Runtime):
    def __init__(self, replacement):
        super().__init__(lambda _value: None)
        self._replacement = replacement

    def _evaluate(self, expression, frame):
        if isinstance(expression, Name) and expression.value == "miktar":
            frame.assign("ürün", self._replacement)
            return 1
        return super()._evaluate(expression, frame)


def test_member_mutation_re_evaluates_owner_after_amount_expression():
    original = {"stok": 10}
    replacement = {"stok": 100}
    runtime = _RebindingAmountRuntime(replacement)
    runtime.global_frame.define("ürün", original)

    command = Command(
        name="artır",
        subject=Member(Name("ürün"), "stok"),
        arguments=(Name("miktar"),),
    )

    runtime._execute_command(command, runtime.global_frame)

    # Referans runtime sırası:
    # 1) ürün.stok değerini original üzerinden oku -> 10
    # 2) miktarı değerlendir; bu adım kökü replacement'a yeniden bağlar
    # 3) 10 + 1 hesapla
    # 4) member.owner zincirini yeniden değerlendir ve replacement.stok = 11 yaz
    assert original == {"stok": 10}
    assert replacement == {"stok": 11}
    assert runtime.global_frame.lookup("ürün") is replacement
