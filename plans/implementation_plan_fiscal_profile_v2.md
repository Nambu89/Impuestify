# Plan: Perfil Fiscal Completo para Deducciones Autonómicas

> Fecha: 2026-03-08
> Estado: APROBADO — en implementación
> Fuente: XSD Modelo 100 Renta 2024 (346 deducciones oficiales AEAT)

## Resumen

Actualizar el perfil fiscal del usuario para cubrir el 100% de los campos necesarios para evaluar las 346 deducciones autonómicas oficiales (15 CCAA régimen común) + deducciones forales (4 territorios).

### Estado actual
- **Perfil fiscal**: 55 campos → cubre 39% de requirements
- **Deducciones en BD**: 192 (simplificadas)
- **Deducciones en XSD oficial**: 346 (régimen común) + ~80 forales = ~426

---

## FASE 0: Parseo XSD → Seed actualizado (Python Pro)

**Script**: `backend/scripts/seed_deductions_xsd.py`
- Parsea `diccionarioXSD_2024.properties`
- Extrae 346 deducciones con casillas AEAT reales
- Genera seed idempotente
- JSON referencia en `data/reference/deducciones_autonomicas_xsd.json`

**Estado**: En progreso (agente python-pro)

---

## FASE 1: Backend — Infraestructura (backend-architect)

### Tarea 1.1: Endpoint required-fields por CCAA
`GET /api/irpf/deductions/required-fields?ccaa=Canarias`
- Consulta deducciones activas para CCAA
- Devuelve campos agrupados por categoría
- Diseño "requirement-driven": frontend no hardcodea campos

### Tarea 1.2: Ampliar FiscalProfileRequest
Añadir ~35 campos nuevos (todos `Optional[bool] = None`) al modelo Pydantic.

### Tarea 1.3: Auto-bridge perfil → deduction answers
`build_answers_from_profile(profile: dict) -> dict`
- Mapea campos del perfil fiscal a claves de requirements
- Derivados automáticos: num_descendientes > 0 → tiene_hijos = True
- Los 35 campos nuevos mapean 1:1

### Tarea 1.4: Integrar en endpoints existentes
- `/deductions/discover` carga perfil + merge con answers explícitos
- `deduction_discovery_tool.py` hace lo mismo para el chat

### Tarea 1.5: Tests
`test_deduction_profile_bridge.py`

---

## FASE 2: Frontend — SettingsPage (frontend-dev)

### Tarea 2.1: Ampliar FiscalProfile interface
+35 campos en `useFiscalProfile.ts`

### Tarea 2.2: Hook useDeductionFields
Llama al endpoint required-fields, cachea por CCAA

### Tarea 2.3: Componente DeductionFieldsSection
Reutilizable, agrupa por categoría, muestra solo campos relevantes para CCAA

### Tarea 2.4: Integrar en SettingsPage
Nueva sección collapsible "Deducciones autonómicas"

---

## FASE 3: Frontend — TaxGuidePage (frontend-dev)

### Tarea 3.1: Integrar en paso 6 (Deducciones)
Reutilizar DeductionFieldsSection

### Tarea 3.2: Pasar answers del wizard al discover

### Tarea 3.3: Actualizar useTaxGuideProgress

---

## FASE 4: Chat Agent (backend-architect)

### Tarea 4.1: Auto-populate answers en discover_deductions tool
### Tarea 4.2: Actualizar tool description

---

## Campos nuevos por categoría

### Vivienda (7)
- alquiler_vivienda_habitual (bool)
- importe_alquiler_anual (number)
- vivienda_habitual_propiedad (bool)
- rehabilitacion_vivienda (bool)
- vivienda_rural (bool)
- dacion_pago_alquiler (bool)
- arrendador_vivienda_social (bool)

### Familia (8)
- nacimiento_adopcion_reciente (bool)
- adopcion_internacional (bool)
- acogimiento_familiar (bool)
- familia_monoparental (bool)
- hijos_escolarizados (bool)
- gastos_guarderia (bool)
- ambos_progenitores_trabajan (bool)
- hijos_estudios_universitarios (bool)

### Discapacidad y Dependencia (5)
- descendiente_discapacidad (bool)
- ascendiente_discapacidad (bool)
- ascendiente_a_cargo (bool)
- familiar_discapacitado_cargo (bool)
- empleada_hogar_cuidado (bool)

### Donaciones (5)
- donativo_entidad_autonomica (bool)
- donativo_investigacion (bool)
- donativo_patrimonio (bool)
- donativo_fundacion_local (bool)
- donativo_entidad_canaria (bool)

### Sostenibilidad (5)
- vehiculo_electrico_nuevo (bool)
- obras_mejora_energetica (bool)
- instalacion_renovable (bool)
- adquisicion_bici_electrica (bool)
- seguros_salud (bool)

### Territorio / Otros (5)
- municipio_despoblado (bool)
- primer_acceso_internet_rural (bool)
- autonomo_domicilio (bool)
- inversion_empresa_nueva (bool)
- gastos_idiomas (bool)

---

## Sprints

### Sprint 1 (alta cobertura ~60%)
- alquiler_vivienda_habitual + importe
- nacimiento_adopcion_reciente
- ascendiente_a_cargo
- vivienda_habitual_propiedad
- hijos_escolarizados
- familia_monoparental
- descendiente/ascendiente_discapacidad
- Auto-bridge profile → answers

### Sprint 2 (media ~25%)
- Sostenibilidad (vehículo, obras, renovable)
- Rehabilitación, municipio despoblado
- Empleada hogar, donaciones autonómicas
- Endpoint requirement-driven + componente frontend

### Sprint 3 (nicho ~15%)
- Campos territoriales específicos
- Integración TaxGuidePage
- Integración chat agent

---

## Métricas de éxito
- Antes: 39% cobertura → Después: 100%
- KPI: maybe_eligible < 10% con perfil completo
- Deducciones en BD: 192 → 346+ (régimen común) + forales
