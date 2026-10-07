# Roadmap de implementación

## H1 · Base técnica y reglas — implementado

- [x] Estructura domain/application/infrastructure/ui y configuración reproducible.
- [x] Migración SQLite versionada, claves foráneas y transacciones.
- [x] Reloj de negocio inyectable y zona horaria Buenos Aires.
- [x] Reglas de vencimientos, alta con 50 %, ventana de aviso y estados derivados.
- [x] Documentación inicial, GitHub Actions y pruebas temporales de SQLite.

## H2 · Primer circuito de gestión — implementado en código

- [x] Alta inicial del dueño y precios ingresados por el gimnasio.
- [x] Login con hash Argon2id; creación de empleados; permisos en servicios.
- [x] Edición de cuentas por el dueño y eliminación lógica de empleados, revocación de acceso y conservación de autoría histórica.
- [x] Alta/edición de alumnos, actividad, DNI normalizado, búsqueda y filtros.
- [x] Generación mensual idempotente y cuotas guardadas con importe/descuento.
- [x] Cobro de cuotas completas en una transacción, periodos asociados e idempotencia.
- [x] Estados con prioridad y ficha con cuotas e historial.
- [x] Baja lógica reservada al dueño; no borra pagos ni cuotas.
- [x] Reactivación del mismo alumno: cuota completa desde el mes de reingreso, sin facturar meses inactivos.
- [x] Cerrar sesión y cambiar de usuario con una ventana nueva y permisos del usuario autenticado.
- [x] Eliminación definitiva reservada al dueño, confirmada y transaccional; no modifica otros alumnos ni respaldos anteriores.
- [x] Navegación desplegable animada, iconos de movimientos y referencia rápida en la barra lateral.
- [x] Cuota mensual visible independientemente del saldo; filas inactivas grises, separadores contrastados y tablas redimensionables con altura mínima.
- [ ] Inspección visual manual de formularios en Windows pendiente.

## H3 · Operación avanzada

- [x] Anulación auditada de pagos: dueño, motivo, reversión transaccional e historial conservado.
- [x] Adelantos: preparación idempotente de cuotas futuras y cobro asociado a períodos seleccionados.
- [ ] Promociones trimestrales configurables por dueño, después de acordar elegibilidad y vigencia.
- [ ] Resolver previamente política de cambio de plan, baja con adelantos y prioridad de deuda.

## H4 · Panel e informes

- [x] Panel del dueño con selector mes/año, métricas A–C y torta cobrado aplicado vs pendiente.
- [x] Detalle de cuotas/pagos y exportes PDF/XLSX con saldos, descuentos, medios y anulaciones identificadas.
- [x] Se omite el total agregado de deuda vencida (opcional); el detalle conserva saldos por cuota.
- [x] Respaldo SQLite consistente, restauración validada y pruebas.
- [x] Calendario mensual del dueño con filtros de vencimientos, cobros y movimientos de alumnos.

## H5 · Recuperación y distribución

- [x] Logos del gimnasio y DAX en el acceso y firma personal clicable a Instagram.
- [ ] Licencia offline Ed25519, branding restante e instalador Windows.

## H6 · Cierre

- [ ] Prueba integral, revisión de accesibilidad/escala y validación de instalador offline.
- [ ] Revisar licencias de Qt y dependencias antes de distribuir.

No se declara listo para producción hasta cerrar las pruebas y validaciones de H6.
