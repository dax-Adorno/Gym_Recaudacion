# MOOVE RECOVERY · Gestión de cuotas

Especificación de producto y guía de implementación para Codex
Versión 1.0 — 3 de octubre de 2026
Responsable: Eduardo Dax Adorno · DAX
Estado: requisitos principales acordados; decisiones pendientes identificadas explícitamente.

## 1. Instrucción para el agente de desarrollo

Construir una aplicación de escritorio real para Windows con Python, PySide6 y SQLite. Implementar por hitos verificables, con pruebas automatizadas y trabajo versionado en un repositorio GitHub privado. Este documento contiene el contexto necesario: no depender del historial de otro chat.

Primero inspeccionar el repositorio y sus instrucciones. Si está vacío, crear estructura, configuración, documentación y pruebas. Preservar cambios existentes. No limitar la entrega a un mockup, un plan o fragmentos de código: implementar funcionalidad ejecutable. No declarar terminada una función que tenga simulaciones, TODO críticos o pruebas sin ejecutar. Informar restricciones del entorno y diferenciar pruebas automáticas, inspección visual y validación manual pendiente.

Las reglas confirmadas prevalecen sobre propuestas técnicas. Resolver elecciones técnicas rutinarias y documentarlas. Preguntar únicamente por decisiones de negocio pendientes que cambien cobros, deuda o permisos; se puede avanzar con el resto. No inventar precios, porcentajes, credenciales ni datos reales. Los ejemplos deben identificarse como ficticios y quedar separados de producción.

## 2. Objetivo y alcance

Gimnasio MOOVE RECOVERY, inicialmente unos 50 alumnos y en crecimiento. Sustituir anotaciones dispersas por control de alumnos, cuotas y cobranzas. Una sola PC Windows, operación completamente offline y dos roles: dueño/administrador y empleado.

Incluye altas, edición, baja lógica, reactivación, buscador, estados por color, planes, cuotas mensuales, adelantos, promoción trimestral, deuda acumulada, reportes PDF/Excel, respaldos y licencia por equipo. No incluye control físico de acceso, asistencia, rutinas, gastos, facturación fiscal, pasarela de pago, WhatsApp, correo automático, sincronización entre PCs ni servicios web. El informe es de cuotas y cobranzas, no un balance contable ni cálculo de ganancias.

## 3. Identidad y archivos gráficos

Nombre visible: MOOVE RECOVERY · Gestión de cuotas.
Logo del gimnasio: archivo original image.png, texto MOOVE RECOVERY y subtítulo Desarrollo del movimiento & actividades físicas, azul marino sobre blanco.
Logo del desarrollador: archivo original 2.png, ilustración tecnológica DAX.
El usuario debe aportar ambos archivos al nuevo repositorio; no asumir que rutas de otro chat existen.
Destinos sugeridos: assets/branding/moove_recovery.png y assets/branding/dax.png.
No redibujar ni reemplazar los logos. Mantener proporciones. Pantalla de carga breve con logo del gimnasio predominante y firma Desarrollado por DAX. Cerrar al finalizar la carga sin retrasos artificiales. Login con logo del gimnasio. Acerca de con DAX y versión. PDF con identidad del gimnasio, período y fecha.
Diseño: fondo claro, navegación azul marino, contraste legible, estados con color y texto. Ventanas utilizables con escalado de Windows y teclado. No introducir temas tecnológicos decorativos que distraigan de cobrar y buscar alumnos.

## 4. Alumnos y búsqueda obligatoria

Datos: nombre, apellido, DNI, teléfono, fecha de alta, actividad, plan de 2/3/4 veces por semana, observaciones y estado activo/inactivo. DNI y teléfono son textos, no números para cálculos. Normalizar DNI para detectar duplicados. No crear un alumno nuevo si existe inactivo con ese DNI: mostrar coincidencia y permitir al dueño reactivarlo.

Buscador siempre visible en gestión de alumnos. Buscar por nombre, apellido y DNI, con coincidencias parciales, sin distinguir mayúsculas; se propone también ignorar tildes. Combinar con filtros todos/al día/próximos a vencer/deudores/inactivos/pendientes. Incluir inactivos en Todos y permitir localizarlos explícitamente. Mostrar resultados vacíos y acción para limpiar filtros. Cada resultado abre ficha e historial; permite cobrar según permisos. Usar consultas parametrizadas y tratar % y _ como caracteres de búsqueda literales salvo que se documente otra conducta.

## 5. Permisos

| Acción | Dueño | Empleado |
|---|---|---|
| Buscar y consultar ficha/deuda individual | Sí | Sí |
| Alta de alumnos con plan existente | Sí | Sí |
| Registrar cobro de cuotas completas sin descuento manual | Sí | Sí |
| Recibir descuento automático de ingreso del 50 % | Automático | Automático |
| Cambiar precios y promoción | Sí | No |
| Aplicar promoción trimestral/descuento manual | Sí | No |
| Cambiar plan, inactivar o reactivar | Sí | No |
| Anular pagos con motivo | Sí | No |
| Ver totales globales y exportar reportes | Sí | No |
| Administrar usuarios y restaurar respaldo | Sí | No |

Validar permisos en servicios de aplicación, además de ocultar acciones en UI. El empleado ve lo necesario para cobrar a un alumno, no los números globales. Edición de datos personales por empleado y exportación de respaldos por empleado: pendientes; por defecto técnico restrictivo, reservar al dueño hasta confirmación. Respaldo automático sin intervención de roles.
Crear credenciales en configuración inicial; nunca entregar contraseñas universales ni permitir crear otro administrador después de inicializar sin autorización. Hash de contraseña con biblioteca mantenida, sal y parámetros documentados. No guardar contraseñas en texto claro.

## 6. Reglas confirmadas de cuotas

R01. Planes: 2, 3 o 4 veces por semana. Precio configurado por el dueño. Sin precios ficticios en producción; impedir generar/cobrar cuotas sin precio definido y mostrar cómo resolverlo.
R02. Cuotas mensuales por calendario. Vencimiento nominal día 10; no se traslada si cae sábado o domingo. No excluir feriados.
R03. Puede pagarse hasta el fin del día 10 si es hábil, o hasta el domingo cuando el 10 cae sábado/domingo. En ese caso, deuda vencida desde el lunes siguiente.
R04. Aviso amarillo desde 3 días hábiles antes del día 10. Solo lunes a viernes son hábiles. Una vez iniciada la ventana, permanece durante el fin de semana; si el 10 cae en fin de semana, pasa a vencida el lunes.
R05. Alta días 1 a 20 inclusive: cuota completa del mes. Alta desde el 21: 50 % automático sobre ese mes, visible al empleado y no editable por él.
R06. Si el alta es posterior al vencimiento mensual, la primera cuota vence el día del alta. En otro caso vence el día 10. Al reactivar, se cobra el mes completo con vencimiento regular; si ya pasó, figura vencida inmediatamente. Los meses inactivos no se cobran.
R07. Solo cuotas completas: no pagos parciales. El importe final después de un descuento constituye la cuota completa.
R08. Se pueden abonar meses futuros; cada pago debe identificar los períodos cubiertos. Un pago puede cubrir varias cuotas.
R09. Promoción de tres meses con descuento configurable y aplicado exclusivamente por dueño. No acumular con el 50 % del ingreso. Cuando hay descuento de ingreso, la promoción puede comenzar el mes siguiente.
R10. Deuda acumulativa por cuotas impagas. No agregar recargos no autorizados.
R11. La baja es lógica. Conserva pagos/deuda y detiene generación de nuevas cuotas desde el mes siguiente. Solo dueño puede hacerla.

R11bis. Por solicitud posterior del dueño, se incorpora también eliminación definitiva, separada de la baja lógica. Solo dueño, previa confirmación con nombre y DNI: elimina alumno, cuotas, cobros, aplicaciones, movimientos y auditoría vinculada en una transacción. Conserva una constancia general de ejecución sin datos del alumno. No modifica otros alumnos ni respaldos existentes; los registros eliminados dejan de participar en reportes. Un cobro compartido con otro alumno bloquea la eliminación completa. No implica devolución de dinero.
R12. Cambiar precios no recalcula cuotas históricas ni períodos ya abonados. Guardar precio base, descuento, importe final y origen del descuento en cada cuota.
R13. Marcar pagado es consecuencia de registrar un cobro válido, nunca un interruptor independiente.
R14. Registrar fecha de cobro, importe, medio, períodos, usuario y referencia interna. Una anulación mantiene registro, autor y motivo, y revierte su aplicación a cuotas en una transacción.
R15. Generar las cuotas faltantes al iniciar, sin duplicados, según historial de actividad. No crear cobros/deudas anteriores al comienzo operativo sin procedimiento aprobado para saldos iniciales.

Fechas de negocio locales, zona America/Argentina/Buenos_Aires; fecha y reloj inyectables en pruebas. Actualizar estados al cambiar de día si la app queda abierta y al volver a primer plano. Dinero en centavos enteros; porcentajes y cálculos con Decimal, redondeo definido y probado. No usar float para dinero.

## 7. Estados y prioridad

1. Gris: inactivo, incluso si conserva deuda (mostrar deuda dentro de ficha).
2. Rojo: alumno activo con cualquier cuota vencida impaga, aunque el mes actual esté cubierto.
3. Amarillo: activo sin deuda vencida y cuota actual pendiente dentro de ventana de aviso.
4. Neutro: cuota actual pendiente fuera de la ventana de aviso.
5. Verde: cuota actual cubierta y sin deuda vencida previa.

Si no existe cuota por error/configuración incompleta, mostrar advertencia Sin cuota generada; nunca asumir pagado. No convertir un adelanto de un mes futuro en deuda vigente. Estado se deriva, no se edita manualmente.

## 8. Panel y reportes

Solo dueño. Selector mes/año. Separar:
A. Dinero recibido en el mes por fecha de pago, que puede incluir deuda anterior y adelantos.
B. Cobrado aplicado a cuotas del período seleccionado, independientemente del mes de cobro.
C. Pendiente de cuotas de ese período.
D. Deuda vencida total, si se muestra, con etiqueta explícita.

Torta: B versus C; denominador suma de importes finales de cuotas del período. Descuentos no son deuda. No usar A en esa torta. Si total es cero, Sin cuotas registradas. Mostrar fecha de corte: consulta actual del período, no reconstrucción histórica salvo función adicional aprobada. Definir tratamiento visible de anulaciones; nunca contar pagos anulados como cobros válidos ni borrar su rastro.
PDF y Excel: gimnasio, período, fecha de corte, resúmenes, detalle de cuotas/pagos, medios, descuentos, saldos y anulaciones identificadas. Valores de Excel numéricos donde corresponda, DNI/teléfono como texto. Evitar interpretación de textos del usuario como fórmulas.

## 9. Pantallas

Carga/branding; activación inicial; configuración inicial del dueño y precios; login; gestión de alumnos con buscador y tarjetas; ficha de alumno; alta/edición; cobro y confirmación; panel dueño; planes/promociones; reportes; usuarios; respaldo/restauración; Acerca de.

Cobro: buscar alumno → seleccionar cuotas completas → total no editable para empleado → medio de pago → confirmación → comprobación de guardado → actualización de tarjeta. Deshabilitar doble envío y protegerlo también en persistencia. Mensajes claros ante errores de disco o validación; no mostrar éxito si falla la transacción.

## 10. Arquitectura propuesta

Python + PySide6 + SQLite. Sin servidor HTTP. Estructura src/moove_recovery con domain (reglas puras), application (casos de uso y permisos), infrastructure (SQLite, respaldo, exportes y licencia) y ui (PySide6). Dependencias explícitas, evitar lógica financiera dentro de widgets. Tests unitarios e integración con SQLite temporal. Elegir versiones compatibles y fijarlas en archivo reproducible; no elegir automáticamente versiones preview.

SQLite: claves foráneas activadas en cada conexión, transacciones para pagos/anulaciones/altas, migraciones versionadas, índices de búsqueda y unicidad alumno-período. Persistir fuera de carpeta de instalación; definir si se admite un solo usuario Windows o varios y usar ruta/ACL apropiada. Impedir dos instancias escribiendo simultáneamente en esta versión.

Entidades: usuarios, alumnos, planes, precios_plan con vigencia, historial_alumno, cuotas, pagos, pago_cuotas, promociones, auditoria y configuracion. Una cuota puede tener distintas aplicaciones históricas por anulaciones, pero una sola cobertura válida completa. Auditabilidad no significa inviolabilidad frente al administrador del sistema operativo.

Exportes: seleccionar bibliotecas mantenidas para PDF y XLSX. Gráfico simple integrado; no incorporar una dependencia pesada sin necesidad. Verificar licencias de distribución de componentes Qt y de dependencias elegidas, incluir avisos requeridos. PyInstaller para empaquetado en Windows; instalador con desinstalador y acceso directo, herramienta a seleccionar y documentar.

## 11. Respaldo y recuperación

Propuesta técnica: copia automática al primer inicio de cada día y antes de migraciones/restauraciones; conservación rotativa configurable, punto de partida 30 copias diarias. Botón para guardar copia en pendrive/carpeta. Mostrar fecha, destino y resultado del último respaldo; distinguir local de exportado. Copia en mismo disco no protege de pérdida del equipo.

Crear snapshots consistentes mediante API de backup de SQLite, no copiar a ciegas un archivo abierto con WAL. Incluir esquema/versiones y datos necesarios; no empaquetar claves privadas ni incluir activación que habilite otra PC. Una copia para recuperar datos debe poder usarse en otra PC después de reactivar legítimamente.

Restaurar solo dueño: validar formato, integridad y compatibilidad; confirmar sustitución; copia preventiva; cerrar conexiones; reemplazo seguro; reabrir/verificar. Un fallo no debe destruir el estado anterior. No extraer rutas arbitrarias si se usa ZIP. Documentar recuperación de credenciales tras desastre sin contraseña maestra embebida.

El usuario puede enviar manualmente el archivo por correo o Bluetooth. No implementar envío automático. No afirmar que el archivo está cifrado si no lo está; el respaldo contiene datos personales.

## 12. Licencia offline por equipo

Licencia firmada digitalmente, por ejemplo Ed25519 con biblioteca mantenida. Aplicación contiene únicamente clave pública. Herramienta separada del desarrollador genera/importa clave privada y firma licencias para un código de equipo. La clave real se genera y conserva en el equipo del desarrollador, fuera de Git, builds, logs y CI. Para tests usar claves efímeras.

Flujo: instalar → mostrar código de equipo → DAX emite licencia → importar → validar firma, producto, esquema y equipo al inicio → operar offline. Licencia permanente como propuesta vigente, sin mecanismo de expiración comercial. Seleccionar y documentar huella Windows estable; cambio de hardware/formateo puede requerir reemisión. No basarse únicamente en MAC o nombre de PC. No implementar criptografía propia ni bypass de producción mediante variable de entorno.

El generador puede tener código fuente en tools/license_issuer pero excluirlo del paquete del cliente. Firma usa formato canónico definido. Licencia inválida bloquea operación y ofrece activación, no elimina datos. No prometer protección absoluta ni revocación remota de una licencia permanente offline. Borrar instalador es opcional; desinstalador permanece disponible. Desinstalación conserva datos por defecto; borrado explícito con confirmación. Actualización conserva datos y licencia compatible.

## 13. Decisiones pendientes: no inventar acuerdos

Estas no bloquean estructura ni reglas ya confirmadas. Registrar decisiones en docs/decisions.md.
- Cambio de plan: propuesta aplicar desde mes siguiente, sin alterar cuotas ya pagadas; confirmar tratamiento de adelantos.
- Baja con adelantos: preservar pagos; política de devolución/consumo pendiente. No devolver ni confiscar automáticamente.
- Promoción trimestral: porcentaje, vigencia, elegibilidad de alumnos antiguos, inicio del trimestre y aplicación sobre cuotas ya generadas. Precios/porcentaje serán configurables; no hardcodearlos. Propuesta: tres meses consecutivos, pago completo conjunto y sin aplicación retroactiva.
- Cobro con deuda: confirmar si debe liquidarse primero la más antigua. Hasta decidir, no imponer esa prioridad como regla acordada.
- Puesta en marcha: importación de alumnos existentes, fecha operativa y saldos iniciales aprobados, sin crear deuda desde fechas históricas por defecto.
- Edición de datos personales y respaldo manual por empleado; inicialmente restringidos.
- Versión/arquitectura de Windows del cliente y si dueño/empleado usan la misma cuenta de Windows.
- Recuperación de acceso del dueño y devoluciones reales de dinero; una anulación de registro no demuestra un reembolso bancario.

## 14. Pruebas requeridas y aceptación

Usar pytest; pytest-qt para interacción de UI si resulta compatible. Tests de servicios con base temporal real. Parametrizar fechas, no depender del día real. Fixtures ficticias aisladas. No sustituir toda la base por mocks.

| ID | Escenario | Resultado esperado |
|---|---|---|
| T01 | Alta día 20 vs 21, precio ficticio 30000 | 30000 vs 15000; solo primer mes al 50 % |
| T02 | Vence 10/10/2026 sábado | Vencimiento 12/10; amarillo desde 07/10; rojo 13/10 |
| T03 | Vence 10/01/2027 domingo | Vencimiento 11/01; feriados no alteran regla |
| T04 | Alta 15/10 y 25/10/2026 | Primera vence día de alta; completa vs mitad |
| T05 | Alta anterior al vencimiento trasladado | No vencer antes del vencimiento efectivo |
| T06 | Mes/año nuevo y febrero bisiesto | Períodos correctos, sin duplicados |
| T07 | Reinicio repetido y meses sin abrir | Generación idempotente según períodos activos |
| T08 | Cobro inferior al importe final | Rechazo sin cambios |
| T09 | Doble clic/reintento de cobro | Un solo pago válido |
| T10 | Error entre pago y aplicación | Rollback completo |
| T11 | Promoción trimestral | Tres cuotas, total y redondeo consistentes; solo dueño |
| T12 | Intento combinar trimestre y mitad | Rechazo o separación explícita según regla |
| T13 | Aumento de precio tras adelanto | Meses pagados e históricos sin cambios |
| T14 | Mes actual pago, deuda anterior | Tarjeta roja |
| T15 | Baja y siguiente mes | Gris, deuda conservada, sin nuevas cuotas |
| T16 | Búsqueda parcial, tildes, DNI, inactivo | Coincidencias correctas y filtros combinables |
| T17 | DNI duplicado activo/inactivo | Bloquear duplicado y mostrar existente |
| T18 | Empleado llama servicios restringidos | Denegación aunque omita UI |
| T19 | Anulación y segunda anulación | Reabre cuotas una sola vez, conserva auditoría |
| T20 | Cobro ficticio 90000 en octubre para nov-ene | Ingreso octubre 90000; no atribuirlo a cuota octubre |
| T21 | PDF/XLSX y mes sin cuotas | Totales reconciliados; sin división por cero |
| T22 | Backup/restore en base nueva | Datos y relaciones recuperados |
| T23 | Backup corrupto/incompatible/disco sin permiso | Error claro; base actual intacta |
| T24 | Firma válida/equipo distinto/licencia alterada | Solo licencia válida del equipo permite operar |
| T25 | Instalación/actualización/desinstalación Windows | Arranque offline, conservación de datos y licencia |
| T26 | Empaquetado de producción | Sin claves privadas, generador, bases reales ni bypass |
| T27 | Cambio de día con app abierta | Actualiza estados sin reiniciar |

Prueba integral: configurar dueño y precios → empleado da alta → cobra → buscar ficha → dueño ve totales → exporta → respaldo → restauración de prueba. Incluir pruebas de login y aislamiento de reportes por rol. Cobertura propuesta >=85 % del dominio y servicios críticos, sin tests vacíos para alcanzar porcentaje.

Verificar visualmente ventana, formularios, mensajes, logos y reportes. Una ejecución headless no acredita que el instalador funcione en Windows. El build y smoke test final deben correr en Windows sin Python preinstalado y sin red. Registrar evidencia de lo ejecutado y pendientes.

## 15. Repositorio y calidad

Repositorio privado sugerido: moove-recovery-desktop. No se ha creado desde esta especificación. El usuario deberá proporcionar acceso o abrir un clon local. No inventar URL ni declarar pushes/PR realizados sin comprobación.

Archivos esperados: README.md, AGENTS.md, pyproject.toml, lockfile, .gitignore, docs/specification.md (este documento), docs/decisions.md, docs/test-plan.md, docs/user-guide.md, docs/recovery.md, src/, tests/, assets/branding/, packaging/, tools/license_issuer/, .github/workflows/ci.yml.

AGENTS.md debe resumir comandos, arquitectura, reglas financieras, prohibición de secretos y criterios de entrega. .gitignore debe excluir entornos, cachés, builds, bases SQLite y WAL/SHM, respaldos, licencias emitidas, claves privadas, .env y datos reales. Versionar migraciones, assets y fixtures sintéticos. No añadir licencia open source al código del cliente sin instrucción del dueño del repositorio.

Ramas por hito, commits pequeños y PR con problema, cambios, pruebas y limitaciones. No force-push ni sobrescribir trabajo ajeno. No publicar Releases ni fusionar main automáticamente sin autorización. CI: lint/formato, tipado en núcleo, tests, cobertura y auditoría de dependencias; fijar versiones de herramientas/actions. Compilar paquete Windows en runner Windows. Firma de licencias y firma de ejecutables son procesos distintos; no afirmar que un ejecutable está firmado si no lo está.

## 16. Plan de implementación

H1. Estructura, configuración, conexión SQLite/migraciones, reloj y reglas puras con tests; README y CI.
H2. Usuarios/permisos, alumnos/búsqueda, generación de cuotas, cobro transaccional y estados; primer circuito completo en UI.
H3. Adelantos, promociones, historial, anulaciones, bajas y cambio de plan después de resolver sus reglas.
H4. Panel, PDF/XLSX, respaldo/restauración y sus pruebas.
H5. Licencia por equipo, generador separado, branding, instalador y documentación operativa.
H6. Integración completa, pruebas Windows offline, actualización/recuperación y revisión del paquete.

Cada hito entrega código ejecutable, tests con resultados reales y documentación actualizada. Mantener checklist de avance. No detenerse al terminar el plan inicial: ejecutar el hito autorizado. Para una primera tarea manejable, el prompt de arranque encarga H1 y H2; el resto se continúa con el contexto persistido en Git.

## 17. Prompt de arranque para copiar en Codex

Lee docs/specification.md (o el archivo MOOVE_RECOVERY_ESPECIFICACION_CODEX.md adjunto) y las instrucciones existentes del repositorio. Construye MOOVE RECOVERY con Python, PySide6 y SQLite. Primero inspecciona el proyecto; luego implementa H1 y H2 completos: estructura, migraciones, login/roles, alumnos con buscador, cuotas, cobros completos y estados, incluyendo tests y CI. No te limites a proponer un plan. Conserva todas las reglas confirmadas del documento. Registra decisiones pendientes sin inventar acuerdos y avanza en lo que no dependa de ellas. Usa los logos aportados. Trabaja en una rama y prepara cambios revisables; si tienes acceso al remoto, crea un PR sin fusionarlo. No incluyas claves privadas ni datos reales. Al finalizar informa cómo ejecutar, qué pruebas corriste con sus resultados, qué no pudiste comprobar y qué queda para H3. No declares lista para producción una entrega parcial.

## 18. Cómo iniciar el proyecto

1. Crear repositorio privado en GitHub, por ejemplo moove-recovery-desktop, con README y .gitignore Python.
2. Guardar este documento como docs/specification.md y añadir los dos logos en assets/branding con los nombres indicados. Commit inicial.
3. Abrir el clon local en el entorno de desarrollo con Codex, o conectar el repositorio al entorno cloud disponible en tu cuenta. Un documento en un chat por sí solo no concede acceso al repositorio.
4. Pegar el prompt de la sección 17. Revisar H1/H2 y continuar por hitos, conservando decisiones en el repositorio.
5. Ejecutar y validar el instalador final en Windows. El gimnasio usará el paquete instalado; no necesita Git, Python ni conexión.

Referencia oficial para la modalidad cloud: https://learn.chatgpt.com/docs/cloud (consultada el 03/10/2026). La interfaz y las opciones disponibles pueden variar según cuenta; esta guía no presupone una conexión ya configurada.
