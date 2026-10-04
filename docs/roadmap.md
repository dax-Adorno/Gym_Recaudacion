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
- [x] Alta/edición de alumnos, actividad, DNI normalizado, búsqueda y filtros.
- [x] Generación mensual idempotente y cuotas guardadas con importe/descuento.
- [x] Cobro de cuotas completas en una transacción, periodos asociados e idempotencia.
- [x] Estados con prioridad y ficha con cuotas e historial.
- [x] Baja lógica reservada al dueño; no borra pagos ni cuotas.
- [ ] Inspección visual manual de formularios en Windows pendiente.
- [ ] Reactivación bloqueada hasta acordar primera cuota y meses inactivos.

## H3 · Operación avanzada

- [ ] Adelantos, promociones trimestrales y anulación auditada de pagos.
- [ ] Resolver previamente política de cambio de plan, baja con adelantos y prioridad de deuda.

## H4 · Panel e informes

- [ ] Métricas separadas por fecha de cobro y periodo de cuota; PDF y XLSX.

## H5 · Recuperación y distribución

- [ ] Backup SQLite consistente, restauración validada y documentación.
- [ ] Licencia offline Ed25519, branding completo e instalador Windows.

## H6 · Cierre

- [ ] Prueba integral, revisión de accesibilidad/escala y validación de instalador offline.
- [ ] Revisar licencias de Qt y dependencias antes de distribuir.

No se declara listo para producción hasta cerrar las pruebas y validaciones de H6.
