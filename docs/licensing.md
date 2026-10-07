# Activacion offline: etapa 1

Implementado: codigo MR1 a partir de SHA-256 del MachineGuid de Windows,
con separacion por producto y version. No usa nombre de PC ni MAC.
Se lee la vista de registro de 64 bits sin escribir ni enviar datos.
La huella identifica una instalacion de Windows, no demuestra identidad
fisica: clones con el mismo MachineGuid pueden compartir el codigo.
Reinstalar Windows puede requerir emitir otra licencia.

Formato: JSON con payload (schema entero 1, product moove-recovery,
machine codigo MR1) y signature (Ed25519 en base64). Firma sobre JSON
ASCII ordenado por claves, sin espacios. Licencias permanentes sin expiracion.
Se rechazan campos adicionales, duplicados, producto/version/equipo incorrectos,
firma invalida y archivos de mas de 8192 bytes.

Las pruebas generan claves efimeras en memoria. No hay clave de produccion
ni clave privada en el repositorio. La dependencia cryptography es local;
el producto no incorpora acceso de red.

Emisor separado implementado en tools/license_issuer/issuer.py. No forma parte
del paquete Python del cliente (solo se distribuye src). Genera claves privadas
PKCS8 cifradas con contrasena solicitada sin mostrarla ni pasarla como argumento.
Rechaza rutas de claves/licencias dentro del repositorio y no sobrescribe archivos.
No se ha generado la clave definitiva. La clave publica exportada son 32 bytes.

Uso exclusivo del desarrollador, desde un entorno con el proyecto instalado:

```powershell
python tools/license_issuer/issuer.py generate-key --private D:/LicenciasMoove/issuer.pem --public D:/LicenciasMoove/public.key
python tools/license_issuer/issuer.py issue --private D:/LicenciasMoove/issuer.pem --machine MR1-CODIGO_COMPLETO --output D:/LicenciasMoove/cliente.license
```

Crear previamente la carpeta privada y restringir sus permisos de Windows.
Conservar una copia segura de clave y contrasena: perderlas impide emitir nuevas
licencias compatibles. Nunca entregar la clave privada ni el emisor al cliente.
La contraseña protege el archivo; no sustituye permisos ni protege una PC comprometida.

Implementado: almacenamiento atomico y pantalla con codigo copiable e importacion
de licencia. Se verifica al iniciar antes de abrir la base, crear el administrador
o acceder al login. Cancelar bloquea el acceso; una licencia invalida nunca borra datos.
La licencia se guarda separada de la base, en LOCALAPPDATA/MOOVE RECOVERY/activation.
Restaurar un respaldo de datos no transfiere la activacion.

Clave definitiva generada localmente por el desarrollador. Solo la clave publica
esta incorporada como infrastructure/license_public.txt (32 bytes en hexadecimal)
y declarada como dato del paquete Python. La clave privada cifrada permanece fuera
del repositorio. Se emitio una licencia real para la PC de desarrollo mediante
el emisor y se verificaron firma, equipo, instalacion y lectura posterior.
La licencia emitida permanece fuera del repositorio y no se incluye en el paquete.
Esto no sustituye la prueba de instalacion en una segunda PC ni el smoke test
del instalador sin Python y sin internet.
Si falta la clave publica, el inicio muestra un error y NO permite operar.
No hay clave de prueba incorporada, bypass por entorno ni clave privada distribuida.
La pantalla y el circuito se prueban inyectando claves efimeras desde las pruebas.
Pendiente tambien empaquetado y pruebas Windows sin Python y sin internet.
