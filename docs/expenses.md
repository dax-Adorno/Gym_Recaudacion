# Gastos y economia registrada

Solo el dueno puede consultar, cargar, editar, pagar o anular gastos. Los servicios
verifican rol y cuenta activa; ocultar el menu no es la unica proteccion.

Cada gasto tiene concepto, categoria editable, fecha prevista, importe positivo
en centavos enteros y observaciones. Un pagado agrega fecha real de pago y medio.
No se admite una fecha de pago futura. No se implementan pagos parciales.

Pagados se filtra por mes de pago. Pendientes muestra todos los pendientes
actuales, aunque correspondan a otro mes, para no ocultar compromisos anteriores.
Registrar pago convierte el mismo registro en pagado de forma transaccional;
una segunda operacion se rechaza sin duplicarlo. El dueno puede corregir el estado
desde Editar: pendiente a pagado requiere fecha y medio; pagado a pendiente pide
confirmacion y elimina la fecha/medio actuales sin borrar la auditoria. Se recalculan
los totales, sin registrar devolucion bancaria. Una edicion con estado desactualizado
se rechaza para no pisar un pago registrado mientras estaba abierto el formulario.
Anular requiere motivo, conserva el registro y lo excluye de los totales.
Altas, ediciones, pagos y anulaciones quedan auditados.

Panel, PDF y XLSX muestran cobros validos del mes, gastos pagados del mes,
resultado (cobros menos gastos) y gastos pendientes actuales separados.
Las cuotas no cobradas y los gastos pendientes no intervienen en ese resultado.
El calendario incluye un filtro Gastos: pagados en fecha real de pago, pendientes
en fecha prevista y anulados identificados sin sumarlos al resultado. Cambios de
gastos refrescan calendario y panel. Las tablas ajustan columnas al espacio
disponible, conservan separadores manuales y envuelven el texto largo.
Se incluyen detalles de gastos en los exportes y se conserva el detalle anterior
de cuotas/cobros. Los textos Excel se escriben como datos, no formulas.
Esto representa flujos registrados, no saldo bancario ni utilidad contable fiscal.
La torta predeterminada compara cobros recibidos (verde) y gastos pagados (rojo)
del mes. Su total es la suma de entradas y salidas, no el resultado neto. Los
pendientes no integran esa torta. El resultado neto se muestra separado, en rojo
si es negativo. El selector conserva la vista de cuotas cobradas/pendientes.
Los estados son actuales: no se reconstruye una foto historica de pendientes.

Esquema SQLite 2: la actualizacion hace una copia preventiva de bases de esquema 1.
Restaurar una copia compatible de esquema 1 la migra antes de sustituir la base
activa. Copias de esquema 2 requieren la tabla expenses y conservan los gastos.
Versiones anteriores del programa no deben abrir bases de esquema 2.

Verificacion: pruebas de permisos, validaciones, auditoria, cambio de mes,
resultado con cobros/anulaciones, rollback, migracion, respaldo/restauracion,
exportes y dialogos. La vista previa usa una base ficticia aislada.
El instalador BETA 1.0.1 generado previamente NO incluye esta funcionalidad;
hay que reconstruir y verificar una nueva entrega antes de actualizar al cliente.

Los controles comparten estilos con mayor contraste: botones neutrales azul gris,
acciones principales verdes, acciones peligrosas rojas, estados de hover/pulsacion,
foco visible y deshabilitados diferenciados. Pestanas seleccionadas verdes; bordes,
padding y peso de letra no cambian al interactuar para evitar saltos de tamano.
