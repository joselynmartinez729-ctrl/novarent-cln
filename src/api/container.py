"""Composición de dependencias (Composition Root). Configuración por variables de entorno (12-Factor)."""
from dataclasses import dataclass

from src.application.services import (ConsultasDeNovaRent, ManejadorMantenimientoMayor,
                                      ServicioDeCompensacionDeCategoria, ServicioDeContratos,
                                      ServicioDeDevolucion, ServicioDeEntrega, ServicioDeLimpieza,
                                      ServicioDeValidacionDeDocumentacion)
from src.domain.cargos import CalculadoraDeCargosExtra
from src.domain.events import MantenimientoMayorRegistrado
from src.infrastructure.db import get_engine
from src.infrastructure.memoria import (CatalogoEstatico, PasarelaBancariaSimulada, PrecioCombustibleConfigurable,
                                        PublicadorEnMemoria, RelojDelSistema, ValidadorDePinConfigurable)
from src.infrastructure.seed import seed
from src.infrastructure.sql_repos import SqlUnitOfWork


@dataclass
class Container:
    validacion: ServicioDeValidacionDeDocumentacion
    compensacion: ServicioDeCompensacionDeCategoria
    entrega: ServicioDeEntrega
    devolucion: ServicioDeDevolucion
    limpieza: ServicioDeLimpieza
    contratos: ServicioDeContratos
    consultas: ConsultasDeNovaRent
    publicador: PublicadorEnMemoria


def build_container(database_url=None) -> Container:
    engine = get_engine(database_url)
    seed(engine)
    pub = PublicadorEnMemoria()
    reloj = RelojDelSistema()
    uow = lambda: SqlUnitOfWork(engine, pub)  # noqa: E731
    pub.suscribir(MantenimientoMayorRegistrado, ManejadorMantenimientoMayor(uow))
    return Container(
        ServicioDeValidacionDeDocumentacion(uow, reloj),
        ServicioDeCompensacionDeCategoria(uow, CatalogoEstatico()),
        ServicioDeEntrega(uow, PasarelaBancariaSimulada()),
        ServicioDeDevolucion(uow, CalculadoraDeCargosExtra(), PrecioCombustibleConfigurable()),
        ServicioDeLimpieza(uow), ServicioDeContratos(uow, reloj, ValidadorDePinConfigurable()),
        ConsultasDeNovaRent(uow, reloj), pub)


_container = None


def get_container() -> Container:
    global _container
    if _container is None:
        _container = build_container()
    return _container


def reset_container() -> None:
    global _container
    _container = None


def set_container(c: Container) -> None:
    global _container
    _container = c
