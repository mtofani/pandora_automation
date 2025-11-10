# Pandora Automation

Script de automatización para actualizar umbrales en Pandora FMS.

## 📋 Descripción

Script que actualiza umbrales (`min_critical`, `max_critical`, etc.) y campos relacionados de la tabla `tagente_modulo` en Pandora FMS, según reglas definidas en un archivo JSON.

Permite mantener configuraciones consistentes por grupo y tipo de módulo, sin editar manualmente la base de datos.

## 🚀 Instalación con UV

[UV](https://github.com/astral-sh/uv) es un instalador de paquetes Python rápido escrito en Rust.

### Instalar UV
```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/Mac
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Instalar dependencias
```bash
uv sync
```

O si prefieres instalar en el entorno global:
```bash
uv pip install -r requirements.txt
```

## ⚙️ Configuración

### config.ini

Define la conexión a la base de datos, modo de ejecución y ruta del log:
```ini
[database]
host = localhost
user = root
password = pandora
database = pandora
port = 3306

[options]
dry_run = false
log_path = /var/log/pandora/update_thresholds.log
```

### thresholds_config.json

Define las reglas y grupos a procesar:
```json
{
  "groups": [16, 18],
  "rules": [
    {
      "name": "Datastore Dedicado",
      "agent_name_includes": ["dedicado", "DS-"],
      "module_name_pattern": "Disk Overallocation",
      "module_description_pattern": "Percentage",
      "min_critical": 105,
      "critical_instructions": "Escalar al equipo de almacenamiento."
    }
  ]
}
```

## 💻 Uso

### Simulación (no modifica la base de datos)
```bash
uv run update_thresholds.py
```

O con Python estándar:
```bash
python update_thresholds.py
```

### Aplicar cambios solo en campos vacíos o distintos
```bash
uv run update_thresholds.py
```

### Forzar actualización de todos los valores
```bash
uv run update_thresholds.py --force
```

## 🧠 Comportamiento

- Solo actualiza módulos cuyo `agent_name`, `module_name` o `descripcion` coincidan con las reglas definidas
- Si `dry_run = true`, solo simula los cambios sin aplicarlos
- Si un valor ya existe, no se sobrescribe, salvo que se ejecute con `--force`

## 🪵 Logs

- Se escriben en el archivo indicado por `log_path` (configurable en `config.ini`)
- Formato compatible con logrotate

## 📁 Archivos de configuración

- `config.ini`: Configuración de base de datos y opciones del script
- `thresholds_config.json`: Reglas de umbrales por agente y módulo