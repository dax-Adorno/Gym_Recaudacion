# Decisiones y pendientes

## Decisiones técnicas de esta entrega

- Python 3.14 en desarrollo; soporte declarado desde Python 3.10.
- PySide6 6.11.2, versión estable disponible al iniciar el hito; dependencias fijadas en `pyproject.toml`.
- Contraseñas con Argon2id mediante `argon2-cffi`; nunca se guardan en texto claro.
- Datos en `%LOCALAPPDATA%\MOOVE RECOVERY\data`; pruebas usan SQLite temporal.
- Zona horaria de negocio: `America/Argentina/Buenos_Aires`; el reloj se inyecta en servicios y reglas.
- La fecha de configuración inicial se toma como comienzo operativo. No se generan cuotas previas a esa fecha.
- Los precios iniciales deben ser ingresados por el dueño. No se incluyen valores de ejemplo.
- Los cambios de precio guardan una nueva vigencia y no modifican cuotas ya generadas.
- Dueño y empleados comparten la base bajo un único perfil de Windows; usar perfiles distintos daría bases locales separadas.
- Se usa Argon2id con los parámetros predeterminados de `argon2-cffi`; el hash codifica sal y parámetros para permitir futuras verificaciones.
- PySide6 6.11.2 es la versión estable fijada para desarrollo y entrega inicial.
- Exportes: ReportLab 5.0.1 para PDF (BSD) y openpyxl 3.1.5 para XLSX (MIT); importes del libro se almacenan como celdas numéricas y DNI/teléfono como texto.
- Reactivación: se conserva el registro y el historial; se cobra la cuota completa del mes de reingreso con vencimiento regular, se excluyen los meses inactivos y no se repite la promoción de alta. Si la fecha límite pasó, figura vencida al reingresar.
- Vencimiento de fin de semana: si el día 10 cae sábado o domingo, la cuota se considera vencida el lunes siguiente; no se traslada el vencimiento al lunes.
- Calendario mensual global reservado al dueño; incluye vistas de vencimientos, cobros y movimientos de alumnos.

## Pendiente de decisión del dueño

- Cambio de plan: vigencia y efecto sobre adelantos.
- Baja con adelantos: devolución o consumo del saldo.
- Promoción trimestral: porcentaje, elegibilidad, inicio y cuotas ya generadas.
- Prioridad de aplicación del cobro cuando hay deuda: confirmar si va primero a la cuota más antigua.
- Importación de alumnos y saldos iniciales aprobados.
- Edición de datos personales y exportación manual de respaldo por empleado; por defecto, dueño solamente.
- Si dueño y empleado usan la misma cuenta de Windows.
- Recuperación del acceso del dueño y comprobación de reembolsos reales.

## H3 · Anulación de cobros

- La anulación la puede registrar únicamente el dueño y requiere un motivo.
- Se conserva el cobro original y sus períodos; el estado anulado excluye el importe del saldo pagado.
- La auditoría conserva quién y cuándo anuló, el motivo y las cuotas afectadas.
- Anular el registro no afirma que se haya realizado una devolución de dinero.

## Eliminación definitiva de alumnos

- Solicitud confirmada por el dueño: incorporar una acción distinta de la baja lógica.
- Solo el rol dueño puede eliminar un alumno activo o inactivo, con confirmación explícita de nombre y DNI.
- Se eliminan en una transacción el alumno, sus cuotas, aplicaciones, cobros válidos o anulados, movimientos y auditoría vinculada. Se conserva únicamente una constancia general de quién ejecutó una eliminación y cuándo, sin datos del alumno.
- Los demás alumnos y sus cobros se conservan. Si un cobro está vinculado también a otro alumno, la operación se rechaza completa.
- Los importes eliminados dejan de participar en los reportes. La acción no registra devolución de dinero.
- Los respaldos anteriores no se modifican y pueden conservar una copia de los datos eliminados.

## Distribución

PySide6 se distribuye bajo LGPLv3/GPLv3 o licencia comercial de Qt. Antes de crear un instalador se revisarán las condiciones de distribución de Qt y las licencias de las dependencias incluidas.
