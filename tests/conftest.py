import os
import sys
from datetime import date, datetime
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["PIN_ADMINISTRACION"] = "4321"
os.environ["DATABASE_URL"] = "sqlite://"  # las pruebas nunca tocan la BD real
os.environ.setdefault("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))

from src.domain.value_objects import (Categoria, Dinero, DocumentacionConductor, InspeccionDeVehiculo,
                                      Kilometraje, NivelDeCombustible, PeriodoDeRenta)
from src.domain.reservacion import Reservacion
from src.domain.vehiculo import Vehiculo

HOY = date(2026, 11, 5)
INICIO = datetime(2026, 11, 10, 9, 0)
FIN = datetime(2026, 11, 12, 9, 0)  # 2 días


def doc(**kw):
    base = dict(titular="Ana Pérez", fecha_nacimiento=date(1995, 3, 10),
                licencia_vigente_hasta=date(2029, 1, 1), identificacion_vigente_hasta=date(2030, 1, 1))
    base.update(kw)
    return DocumentacionConductor(**base)


def insp(km=1000, comb=4, fotos=("f1.jpg",), esquema=True):
    return InspeccionDeVehiculo(esquema, tuple(fotos), Kilometraje(km), NivelDeCombustible(comb))


def reservacion(cat=Categoria.ECONOMICO, tarifa="450"):
    return Reservacion("RES-T", cat, Dinero(Decimal(tarifa)), Dinero(Decimal("900")), PeriodoDeRenta(INICIO, FIN))


def vehiculo(cat=Categoria.ECONOMICO, vid="V1"):
    return Vehiculo(vid, "AAA-001", cat, 40)


@pytest.fixture
def api():
    """Cliente de API con una base SQLite en memoria limpia por prueba."""
    from fastapi.testclient import TestClient
    from src.api import container
    from src.infrastructure.db import get_engine, metadata
    url = os.getenv("TEST_DATABASE_URL", "sqlite://")  # en Docker Compose: PostgreSQL de pruebas
    if not url.startswith("sqlite"):
        e = get_engine(url); metadata.drop_all(e); e.dispose()
    container.set_container(container.build_container(url))
    from src.api.main import app
    with TestClient(app) as c:
        yield c
    container.reset_container()
