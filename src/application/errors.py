from src.domain.value_objects import ConflictoDeEstado


class NoEncontrado(Exception):
    """Recurso inexistente (HTTP 404)."""


class SinVehiculoDisponible(ConflictoDeEstado):
    """No hay unidad 'Disponible' de la categoría (HTTP 409)."""
