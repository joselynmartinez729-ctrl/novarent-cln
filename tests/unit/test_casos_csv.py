"""Cada fila de data/casos_prueba_novarent.csv es una prueba (así el CI exige que todos los casos pasen)."""
import json

import pytest

from tests.casos_novarent import cargar_casos, ejecutar

CASOS = cargar_casos()


def test_hay_casos_de_todas_las_reglas():
    assert len(CASOS) >= 100
    assert {c["regla"] for c in CASOS} >= {f"RN-{n:02d}" for n in (1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13)}


@pytest.mark.parametrize("caso", CASOS, ids=[c["caso_id"] for c in CASOS])
def test_caso(caso):
    assert ejecutar(caso["tipo_prueba"], json.loads(caso["entrada_json"])) == caso["resultado_esperado"], caso["escenario"]
