# Plan de pruebas automatizadas

- Reglas puras de vencimiento, ventana de aviso, alta día 20/21, alta posterior al vencimiento, inactividad y estados.
- Persistencia SQLite real en base temporal, claves foráneas, migración repetida e idempotencia de cuotas.
- Cuotas futuras generadas por alumno hasta el período elegido, precio efectivo por mes, idempotencia y asociación del pago al período adelantado.
- Inicialización segura del dueño, verificación de contraseña y bloqueo de segundo administrador.
- Autorización por servicio para precios, baja, anulaciones e informes globales.
- Búsqueda parcial sin distinguir mayúsculas ni tildes, incluyendo `%` y `_` literales; DNI duplicado activo/inactivo.
- Cobro de cuotas completas, adelantos identificados por período, reintentos, rollback y método de pago.
- Panel: ingreso por fecha de cobro separado de aplicación por período de cuota, pendientes, anulaciones excluidas y acceso solo del dueño.
- Inspección manual pendiente de UI Qt y flujo con mouse/teclado; estos tests no acreditan empaquetado Windows.
