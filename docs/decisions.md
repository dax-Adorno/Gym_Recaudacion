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
- Los intervalos de membresía se auditan; la reactivación queda bloqueada hasta definir su política de cuota.

## Pendiente de decisión del dueño

- Reactivación: primer vencimiento, importe y tratamiento de meses inactivos.
- Cambio de plan: vigencia y efecto sobre adelantos.
- Baja con adelantos: devolución o consumo del saldo.
- Promoción trimestral: porcentaje, elegibilidad, inicio y cuotas ya generadas.
- Prioridad de aplicación del cobro cuando hay deuda: confirmar si va primero a la cuota más antigua.
- Importación de alumnos y saldos iniciales aprobados.
- Edición de datos personales y exportación manual de respaldo por empleado; por defecto, dueño solamente.
- Si dueño y empleado usan la misma cuenta de Windows.
- Recuperación del acceso del dueño y comprobación de reembolsos reales.

## Distribución

PySide6 se distribuye bajo LGPLv3/GPLv3 o licencia comercial de Qt. Antes de crear un instalador se revisarán las condiciones de distribución de Qt y las licencias de las dependencias incluidas.
