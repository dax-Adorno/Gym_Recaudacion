# MOOVE RECOVERY · Gestión de cuotas

Aplicación de escritorio para Windows, con datos locales en SQLite y funcionamiento sin conexión.

## Desarrollo

Requiere Python 3.10 o superior. En Windows PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
pytest
python -m moove_recovery
```

La primera apertura solicita crear el dueño y definir los precios reales de los tres planes. No hay credenciales ni precios predeterminados. La base se guarda en `%LOCALAPPDATA%\MOOVE RECOVERY\data\moove.sqlite3`. En esta versión, dueño y empleados deben iniciar sesión en el mismo usuario de Windows para compartir esa base local.

## Estado de implementación

- H1: estructura, migración inicial de SQLite, reglas de cuotas y pruebas.
- H2: login, roles, alumnos, cuotas, cobros, bajas y reactivación.
- H3: adelantos y anulación auditada de cobros; promociones trimestrales y algunas reglas operativas siguen pendientes.
- H4: panel, informes PDF/XLSX, respaldos y calendario mensual del dueño.
- H5-H6: licencia offline, instalador Windows y validación integral pendientes.

El avance detallado y los pendientes están en `docs/roadmap.md`.

La especificación completa está en `docs/specification.md`. La interfaz Qt usa PySide6, distribuido bajo LGPLv3/GPLv3 o licencia comercial de Qt; revisar `docs/decisions.md` y los avisos de dependencias antes de distribuir.
