# Respaldo y restauración

## Copias automáticas

Al primer inicio completado de cada día de negocio se crea una copia SQLite en:

`%LOCALAPPDATA%\MOOVE RECOVERY\data\backups`

Se conservan 30 copias automáticas por defecto. El dueño puede ajustar la retención entre 1 y 3650 copias desde **Respaldos**; al reducirla, las copias automáticas más antiguas se eliminan. Antes de una migración de esquema se guarda además una instantánea previa en esa carpeta.

## Copia manual

En **Respaldos**, el dueño puede guardar una copia en una carpeta externa o unidad removible. La pantalla muestra la última operación y el historial local de copias automáticas. Una copia en el mismo disco no protege frente a la pérdida del equipo.

Las copias contienen información personal y credenciales con hash. No están cifradas; deben protegerse como los datos originales. No contienen claves privadas de licencia.

## Restauración

1. Inicia sesión como dueño y abre **Respaldos**.
2. Selecciona el archivo `.sqlite3` y confirma el reemplazo.
3. La aplicación valida versión, tablas, integridad y relaciones antes de sustituir la base.
4. Se crea una copia preventiva de la base vigente. La restauración se prepara en un archivo temporal; ante un error de reemplazo se conserva/restaura la base anterior.
5. Si termina correctamente, la aplicación se cierra. Ábrela otra vez e inicia sesión con las credenciales que contenía la copia restaurada.

Una copia incompatible, incompleta o dañada se rechaza sin reemplazar la base activa. Conserva una copia externa antes de restaurar: la rotación local no sustituye un respaldo fuera del equipo.
