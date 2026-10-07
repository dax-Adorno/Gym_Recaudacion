# Instalador Windows: candidato de prueba

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

Para producir el instalador, agregar -Iscc con la ruta de ISCC.exe de Inno Setup.
No esta instalado el compilador en esta PC. La pagina oficial de Inno Setup
solicita licencia para uso comercial; resolver su licencia o elegir una alternativa
antes de distribuir. Referencia: https://jrsoftware.org/isdl.php
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

Pendientes de entrega: compilar y probar instalador, licencia y alta inicial en
Windows limpio sin Python/sin internet; segunda PC rechaza licencia de desarrollo;
actualizacion y desinstalacion conservan datos; revisar avisos y obligaciones de
licencias Qt y dependencias antes de distribuir comercialmente.
