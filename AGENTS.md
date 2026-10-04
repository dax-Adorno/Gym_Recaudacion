# Guía del repositorio

## Comandos

- Instalar: `python -m pip install -e ".[dev]"`
- Pruebas: `pytest`
- Lint: `ruff check src tests`
- Formato: `ruff format --check src tests`
- Tipos del dominio/servicios: `mypy`
- Abrir: `python -m moove_recovery`

## Arquitectura

- `domain`: reglas puras, fechas, importes y estados derivados.
- `application`: casos de uso y autorización por rol.
- `infrastructure`: SQLite, migraciones y persistencia.
- `ui`: ventanas PySide6; sin cálculos financieros en widgets.

## Reglas obligatorias

- Dinero en centavos enteros; no usar `float` para importes.
- Cuotas mensuales, vencimiento día 10 trasladado al lunes si cae fin de semana.
- Una cuota se marca cubierta solo mediante un cobro completo y transaccional.
- Verificar permisos en servicios, no solo ocultando controles.
- Proteger DNI duplicado, operaciones parametrizadas y claves foráneas.
- No inventar precios, porcentajes, credenciales ni saldos históricos.
- No guardar ni versionar datos reales, bases locales, respaldos ni claves privadas.
- No añadir servicios web, telemetría ni dependencias de red al producto.

## Entrega

Actualizar documentación y pruebas al cambiar reglas. Reportar los comandos ejecutados y sus resultados. No declarar una función terminada si sigue simulada o depende de una prueba pendiente.
