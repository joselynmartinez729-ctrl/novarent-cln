"""Domain Service CompensacionDeCategoria (N4, US03a/US03b, RN-06/RN-07)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional

from .value_objects import Categoria, Dinero


class TipoDeOferta(str, Enum):
    UPGRADE = "UPGRADE"
    DOWNGRADE = "DOWNGRADE"


@dataclass(frozen=True)
class OfertaDeCompensacion:
    tipo: TipoDeOferta
    categoria: Categoria
    tarifa_diaria: Dinero
    descuento_adicional_pct: int


@dataclass(frozen=True)
class DisponibilidadDeCategoria:
    hay_en_categoria: bool
    hay_superior: bool
    hay_inferior: bool


DESCUENTO_DOWNGRADE_PCT = 20  # H-7: se aplica una sola vez sobre la tarifa de la categoría inferior


class CompensacionDeCategoria:
    def determinar_oferta(self, tarifa_reservada: Dinero, disp: DisponibilidadDeCategoria,
                          superior: Optional[Categoria], inferior: Optional[Categoria],
                          tarifa_inferior: Optional[Dinero],
                          rechaza_upgrade: bool = False) -> Optional[OfertaDeCompensacion]:
        from .specifications import requiere_compensacion
        if not requiere_compensacion().is_satisfied_by(disp):
            return None
        if disp.hay_superior and superior is not None and not rechaza_upgrade:
            return OfertaDeCompensacion(TipoDeOferta.UPGRADE, superior, tarifa_reservada, 0)
        if disp.hay_inferior and inferior is not None and tarifa_inferior is not None:
            tarifa = tarifa_inferior.por(Decimal(100 - DESCUENTO_DOWNGRADE_PCT) / 100)
            return OfertaDeCompensacion(TipoDeOferta.DOWNGRADE, inferior, tarifa, DESCUENTO_DOWNGRADE_PCT)
        return None
