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

Pendiente: herramienta separada de emision, almacenamiento atomico de licencia,
pantalla de activacion, clave publica definitiva y validacion obligatoria antes
de crear la base/administrador. Esta etapa NO bloquea aun el inicio de la app.
Pendiente tambien empaquetado y pruebas Windows sin Python y sin internet.
