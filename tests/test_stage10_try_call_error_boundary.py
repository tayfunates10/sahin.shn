from __future__ import annotations

import pytest

from sahin.ir import IRLoweringError, lower_source


# Call ABI v1'de yanlış hedef/arity kullanıcı hataları backend try handler'ına
# taşınmaz. Bunlar frontend/IR sınırında fail-closed reddedilmelidir; aksi halde
# backend'in kaynakta var olmayan bir RuntimeErrorSHN payload'ı uydurması gerekir.


def test_try_cannot_turn_wrong_flow_arity_into_backend_runtime_payload():
    source = '''akış tek x
    ver x
dene
    sonuç = tek()
olmazsa hata
    yaz hata
'''

    with pytest.raises(IRLoweringError, match="Semantik doğrulama başarısız"):
        lower_source(source)


def test_try_cannot_turn_non_flow_call_target_into_backend_runtime_payload():
    source = '''değer = 1
dene
    sonuç = değer(2)
olmazsa hata
    yaz hata
'''

    with pytest.raises(IRLoweringError, match="Call ABI"):
        lower_source(source)
