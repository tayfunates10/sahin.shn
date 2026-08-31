from __future__ import annotations

from enum import Enum


class TypeKind(str, Enum):
    """Şahin çekirdeğinin atomik tip kimlikleri.

    Kullanıcı yüzeyindeki birleşik/opsiyonel sözleşmeler TypeSpec tarafından
    temsil edilir; TypeKind yalnızca atomik parçaları tanımlar.
    """

    YAZI = "yazı"
    SAYI = "sayı"
    ONDALIK = "ondalık"
    PARA = "para"
    MANTIK = "evet_hayır"
    YOK = "yok"
    AKIS = "akış"
    KAYIT = "kayıt"
    EKRAN = "ekran"
    GORUNUM = "görünüm"
    UYGULAMA = "uygulama"
    BILINMEYEN = "bilinmeyen"


NUMERIC_TYPES = frozenset({TypeKind.SAYI, TypeKind.ONDALIK, TypeKind.PARA})
