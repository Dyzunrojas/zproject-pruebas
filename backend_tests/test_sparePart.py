from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from app.modules.repairs import service as repairService
from app.modules.repairs.schemas import DeviceData, RepairCreate
from app.modules.sparePart import service
from app.modules.sparePart.models import SparePartUsage
from app.modules.sparePart.schemas import (
    SparePartCreate,
    SparePartUpdate,
    SparePartUsageLine,
)


@pytest.fixture()
def makeSparePart(db):
    """Crea un repuesto de prueba con el stock indicado."""

    def _make(name="Pantalla", brand="Genérica", stockUnits=10):
        data = SparePartCreate(
            name=name,
            brand=brand,
            partNumber="REP-001",
            stockUnits=stockUnits,
        )
        return service.createSparePart(db, data)

    return _make


@pytest.fixture()
def makeRepair(db, makeClient):
    """Crea una reparación para asociar el uso de repuestos."""

    def _make():
        client = makeClient()

        data = RepairCreate(
            clientId=client.id,
            device=DeviceData(
                type="Laptop",
                brand="Dell",
                model="Inspiron"
            ),
            problemDescription="No enciende",
            estimatedDeliveryDate=date.today() + timedelta(days=10),
        )

        return repairService.createRepair(db, data)

    return _make


def test_repP01_crearRepuesto(db):
    """Crear un repuesto con datos válidos.
    Esperado: se guarda activo y con el stock indicado."""
    data = SparePartCreate(
        name="Batería",
        brand="Genérica",
        partNumber="BAT-001",
        stockUnits=15,
    )

    part = service.createSparePart(db, data)

    assert part.id is not None
    assert part.isActive is True
    assert part.stockUnits == 15


def test_repP02_actualizarSoloUnCampo(db, makeSparePart):
    """Actualizar solamente el nombre de un repuesto.
    Esperado: cambia el nombre y los demás datos se mantienen."""
    part = makeSparePart(
        name="Pantalla",
        brand="Samsung",
        stockUnits=8
    )

    updated = service.updateSparePart(
        db,
        part.id,
        SparePartUpdate(name="Pantalla OLED")
    )

    assert updated.name == "Pantalla OLED"
    assert updated.brand == "Samsung"
    assert updated.stockUnits == 8


def test_repP03_eliminarEsBorradoLogico(db, makeSparePart):
    """Eliminar un repuesto.
    Esperado: queda inactivo en la BD y ya no se encuentra (404)."""
    part = makeSparePart()

    service.deleteSparePart(db, part.id)

    db.refresh(part)

    assert part.isActive is False

    with pytest.raises(HTTPException) as error:
        service.getSparePart(db, part.id)

    assert error.value.status_code == 404


def test_repP04_listarSoloRepuestosActivos(db, makeSparePart):
    """Listar repuestos después de desactivar uno.
    Esperado: solamente aparecen los repuestos activos."""
    active = makeSparePart(name="Pantalla")
    inactive = makeSparePart(name="Batería")

    service.deleteSparePart(db, inactive.id)

    result = service.getSpareParts(db)

    ids = [part.id for part in result]

    assert active.id in ids
    assert inactive.id not in ids


def test_repP05_registrarUsoDescuentaStock(db, makeSparePart, makeRepair):
    """Registrar el uso de 3 unidades de un repuesto.
    Esperado: baja el stock y se guarda la relación con la reparación."""
    part = makeSparePart(stockUnits=10)
    repair = makeRepair()

    service.consumeSpareParts(
        db,
        repair.id,
        [
            SparePartUsageLine(
                sparePartId=part.id,
                quantityUsed=3
            )
        ]
    )

    db.flush()

    usage = (
        db.query(SparePartUsage)
        .filter_by(
            repairOrderId=repair.id,
            sparePartId=part.id
        )
        .first()
    )

    assert part.stockUnits == 7
    assert usage is not None
    assert usage.quantityUsed == 3


def test_repP06_noPermiteConsumirMasStockDelDisponible(
    db, makeSparePart, makeRepair
):
    """Registrar más unidades de las que existen en inventario.
    Esperado: error 400 y el stock no cambia."""
    part = makeSparePart(stockUnits=2)
    repair = makeRepair()

    with pytest.raises(HTTPException) as error:
        service.consumeSpareParts(
            db,
            repair.id,
            [
                SparePartUsageLine(
                    sparePartId=part.id,
                    quantityUsed=5
                )
            ]
        )

    assert error.value.status_code == 400
    assert part.stockUnits == 2


def test_repP07_repuestosRepetidosSeAgrupan(db, makeSparePart, makeRepair):
    """Registrar dos líneas del mismo repuesto.
    Esperado: se suman las cantidades y se guarda un solo registro de uso."""
    part = makeSparePart(stockUnits=10)
    repair = makeRepair()

    service.consumeSpareParts(
        db,
        repair.id,
        [
            SparePartUsageLine(
                sparePartId=part.id,
                quantityUsed=2
            ),
            SparePartUsageLine(
                sparePartId=part.id,
                quantityUsed=3
            ),
        ],
    )

    db.flush()

    usages = (
        db.query(SparePartUsage)
        .filter_by(
            repairOrderId=repair.id,
            sparePartId=part.id
        )
        .all()
    )

    assert part.stockUnits == 5
    assert len(usages) == 1
    assert usages[0].quantityUsed == 5


def test_repP08_repuestoInexistenteDevuelve404(db, makeRepair):
    """Registrar el uso de un repuesto que no existe.
    Esperado: error 404 'Repuesto no encontrado'."""
    repair = makeRepair()

    with pytest.raises(HTTPException) as error:
        service.consumeSpareParts(
            db,
            repair.id,
            [
                SparePartUsageLine(
                    sparePartId=999,
                    quantityUsed=1
                )
            ]
        )

    assert error.value.status_code == 404