import json
import pymysql
import configparser
from pathlib import Path


def load_config():
    """Carga configuraciones desde config.ini"""
    config = configparser.ConfigParser()
    config.read(Path(__file__).parent / "config.ini")

    db_cfg = {
        "host": config.get("database", "host"),
        "user": config.get("database", "user"),
        "password": config.get("database", "password"),
        "database": config.get("database", "database"),
        "port": config.getint("database", "port", fallback=3306),
        "cursorclass": pymysql.cursors.DictCursor,
    }

    dry_run = config.getboolean("options", "dry_run", fallback=True)
    return db_cfg, dry_run


def load_thresholds_config():
    """Carga configuración de umbrales desde thresholds_config.json"""
    config_path = Path(__file__).parent / "thresholds_config.json"
    with open(config_path, "r") as f:
        config = json.load(f)
    return config.get("rules", []), config.get("default", {})


def match_rule(agent_name, module_name, rules):
    """Devuelve la primera regla que matchee tipo LIKE '%valor%' (sensible a guiones y espacios)."""
    agent_name_l = agent_name.lower()
    module_name_l = module_name.lower()

    for rule in rules:
        agent_pattern = rule["agent_name_pattern"].lower()
        module_pattern = rule["module_name_pattern"].lower()

        # Comparación tipo SQL LIKE '%pattern%'
        if agent_pattern in agent_name_l and module_pattern in module_name_l:
            return rule

    return None

def main():
    db_cfg, DRY_RUN = load_config()
    rules, defaults = load_thresholds_config()

    conn = pymysql.connect(**db_cfg)
    cur = conn.cursor()

    query = """
        SELECT am.id_agente_modulo, a.nombre AS agente_nombre, am.nombre AS modulo_nombre
        FROM tagente_modulo am
        JOIN tagente a ON a.id_agente = am.id_agente
        WHERE am.disabled = 0 AND a.disabled = 0
    """
    cur.execute(query)
    rows = cur.fetchall()

    updates = []
    for row in rows:
        agent_name = row["agente_nombre"]
        module_name = row["modulo_nombre"]

        rule = match_rule(agent_name, module_name, rules)
        fields = rule if rule else defaults

        set_clauses = []
        values = []
        for key, val in fields.items():
            if key in ("agent_name_pattern", "module_name_pattern"):
                continue
            set_clauses.append(f"{key} = %s")
            values.append(val)

        if not set_clauses:
            continue

        sql = f"UPDATE tagente_modulo SET {', '.join(set_clauses)} WHERE id_agente_modulo = %s"
        values.append(row["id_agente_modulo"])
        updates.append((sql, values))

    print(f"🔍 Se encontraron {len(updates)} módulos a actualizar.")
    if DRY_RUN:
        print("💡 Modo DRY-RUN activo, mostrando primeros ejemplos:\n")
        for sql, vals in updates[:10]:
            print(sql, vals)
        print("\nNo se aplicaron cambios.")
    else:
        print("🚀 Aplicando actualizaciones...")
        for sql, vals in updates:
            cur.execute(sql, vals)
        conn.commit()
        print(f"✅ Actualizados {len(updates)} registros.")

    conn.close()


if __name__ == "__main__":
    main()
