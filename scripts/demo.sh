#!/usr/bin/env bash
# Demostración rápida con curl. Uso: BASE=http://localhost:8000 bash scripts/demo.sh
BASE=${BASE:-http://localhost:8000}
J='-H Content-Type:application/json'
DOC='{"titular":"Ana Pérez","fecha_nacimiento":"1995-03-10","licencia_vigente_hasta":"2029-01-01","identificacion_vigente_hasta":"2030-01-01"}'
INSP='{"esquema_completado":true,"fotos":["frente.jpg"],"kilometraje":1000,"combustible":"lleno"}'
echo "== Panel";                curl -s $BASE/vehiculos?categoria=ECONOMICO; echo
echo "== CU-02 documentación";  curl -s $J -d "$DOC" $BASE/reservaciones/RES-001/validar-documentacion; echo
echo "== CU-01 entrega";        R=$(curl -s $J -d "{\"ultimos_4\":\"1234\",\"titular\":\"Ana Pérez\",\"inspeccion_salida\":$INSP}" $BASE/reservaciones/RES-001/entrega); echo $R
CID=$(echo $R | python3 -c "import sys,json;print(json.load(sys.stdin)['contrato_id'])")
echo "== CU-04 devolución tardía, con km extra y falta de gasolina"
curl -s $J -d "{\"hora_devolucion\":\"2026-11-12T13:00:00\",\"inspeccion_devolucion\":{\"esquema_completado\":true,\"fotos\":[\"f.jpg\"],\"kilometraje\":1700,\"combustible\":\"1/2\"}}" $BASE/contratos/$CID/devolucion; echo
curl -s $BASE/contratos/$CID/cargos; echo
echo "== CU-03 categoría no disponible (SEDAN → upgrade, LUJO → downgrade)"
curl -s -X POST $BASE/reservaciones/RES-002/compensacion; echo
curl -s -X POST $BASE/reservaciones/RES-003/compensacion; echo
