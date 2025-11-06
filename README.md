# Pandora Automation

Script de automatización para actualizar umbrales en Pandora.

## Instalación con UV

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

## Uso

1. Configura `config.ini` con tus credenciales de base de datos
2. Ajusta `thresholds_config.json` con las reglas de umbrales
3. Ejecuta el script:

```bash
uv run update_thresholds.py
```

O con Python estándar:

```bash
python update_thresholds.py
```

## Configuración

- `config.ini`: Configuración de base de datos y opciones
- `thresholds_config.json`: Reglas de umbrales por agente y módulo


