# Instalador Windows: BETA 1.0.1

Destino inicial: Windows 10/11 x64, una cuenta Windows compartida por operadores.
Los roles dueno/empleado siguen siendo cuentas distintas dentro del programa.
Datos y activacion pertenecen al usuario Windows y se guardan fuera de la carpeta
del programa. Usar otra cuenta Windows crea otro entorno; multiusuario Windows
con datos compartidos queda pendiente de acordar antes de una entrega diferente.

Construir en Windows, con entorno de desarrollo instalado:

```powershell
python -m pip install -r packaging/requirements-build.txt
powershell -File packaging/build.ps1 -Python D:/GymCuentas/.venv/Scripts/python.exe
```

Para producir el instalador, agregar -MakeNsis con la ruta de makensis.exe
de NSIS 3.13. NSIS reemplaza el candidato Inno Setup; admite uso comercial
sin comprar licencia. Referencias oficiales: https://nsis.sourceforge.io/Download
y https://nsis.sourceforge.io/License
El ejecutable se genera en dist/MooveRecovery y el instalador en dist/installer.
No necesitan Python instalado en destino. Verificar esto en otra PC sigue pendiente.

El paquete incluye runtime, programa, logos y clave publica. Nunca incluye bases,
usuarios, contrasenas, licencias emitidas, emisor ni clave privada. El script revisa
los archivos prohibidos antes de compilar el instalador. El cliente activa su PC
con una licencia emitida por DAX y luego crea su administrador y precios reales.
La compilacion aisla PATH para no recoger DLL incompatibles de otras herramientas.

El instalador no pide una clave universal: la activacion se exige al abrir para
que copiar la carpeta no evite la comprobacion. MachineGuid no protege contra
clones ni modificaciones deliberadas del programa.

Instalacion por usuario, sin privilegios elevados. Actualizar conserva la base
y la licencia. Desinstalar elimina solo los archivos del programa; no se incluye
ninguna instruccion de borrado de datos ni activacion. No borrar manualmente datos
sin respaldo. No hay firma Authenticode: Windows puede advertir sobre editor desconocido.

El programa muestra BETA 1.0.1 y el paquete Python identifica la entrega como
1.0.1b1. Gastos actualiza el esquema de base a 2 con copia preventiva y
migracion; el formato y la clave de licencia se conservan.
El desinstalador usa una lista generada de archivos del paquete y solo elimina
carpetas vacias; no hace borrados recursivos ni elimina archivos agregados por el usuario.
Cierra el programa antes de actualizar o desinstalar.

Se pueden agregar funciones y correcciones en futuras versiones. Las actualizaciones
son manuales y offline: guardar respaldo y ejecutar el nuevo instalador con la app
cerrada. Cambios de estructura de datos requieren migraciones probadas y respaldo
previo; no se promete que cualquier version futura pueda leer cualquier base.
No hay actualizador automatico ni conexion de red. Los cambios compatibles conservan
la clave publica y la licencia; cambiar de clave requiere una estrategia de transicion.

Pendientes de entrega: probar instalador, licencia y alta inicial en
Windows limpio sin Python/sin internet; segunda PC rechaza licencia de desarrollo;
actualizacion y desinstalacion conservan datos; revisar avisos y obligaciones de
licencias Qt y dependencias antes de distribuir comercialmente.

Verificacion local de esta etapa: 107 pruebas aprobadas, lint/formato/tipos
correctos y ejecutable beta construido. Se genero la lista de desinstalacion.
La descarga automatica del compilador NSIS devolvio HTML o errores; no se
ejecutaron archivos que no coincidian con el SHA256 del manifiesto winget.
El desarrollador instalo NSIS 3.13 posteriormente. Se compilo installer.nsi sin
errores: dist/installer/MOOVE_RECOVERY_BETA_1.0.1_Setup.exe (62629409 bytes).
La compilacion no acredita instalacion, actualizacion o desinstalacion: esas
pruebas y la validacion en otra PC limpia siguen pendientes antes de entregar.
Ese instalador fue generado antes de Gastos: no usarlo para instalar los cambios
de este PR. Es necesario reconstruir y verificar una nueva entrega.
