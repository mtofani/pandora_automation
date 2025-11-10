import json
import pymysql
import configparser
from pathlib import Path
import html
import argparse
import logging
import os


def load_config():
    """Lee configuración de base y opciones generales."""
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
    log_path = config.get("options", "log_path", fallback=str(Path(__file__).parent / "update_thresholds.log"))

    return db_cfg, dry_run, log_path


def setup_logger(log_path: str):
    """Configura logging fijo (ideal para usar con logrotate)."""
    os.makedirs(Path(log_path).parent, exist_ok=True)

    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger().addHandler(console)
    return log_path


def load_thresholds_config():
    """Lee reglas, defaults y grupos desde thresholds_config.json."""
    path = Path(__file__).parent / "thresholds_config.json"
    with open(path, "r") as f:
        data = json.load(f)
    return data.get("rules", []), data.get("default", {}), data.get("groups", [])


def normalize(text: str) -> str:
    """Limpia texto (minúsculas y decode HTML)."""
    return html.unescape(text or "").strip().lower()


def match_rule(agent, module, description, rules):
    """Devuelve la primera regla que coincida con los patrones."""
    a, m, d = map(normalize, [agent, module, description])
    for rule in rules:
        inc = [normalize(s) for s in rule.get("agent_name_includes", [])]
        exc = [normalize(s) for s in rule.get("agent_name_excludes", [])]
        if (p := normalize(rule.get("module_name_pattern", ""))) and p not in m:
            continue
        if (p := normalize(rule.get("agent_name_pattern", ""))) and p not in a:
            continue
        if (p := normalize(rule.get("module_description_pattern", ""))) and p not in d:
            continue
        if inc and not any(x in a for x in inc):
            continue
        if exc and any(x in a for x in exc):
            continue
        return rule
    return None


def should_update(current, new, force):
    """Determina si debe actualizarse un valor."""
    if force:
        return True
    if current in (None, ""):
        return True
    if isinstance(current, (int, float)) and current == 0 and new != 0:
        return True
    return current != new


def main():
    parser = argparse.ArgumentParser(description="Actualiza umbrales según reglas.")
    parser.add_argument("--force", action="store_true", help="Pisa valores existentes.")
    args = parser.parse_args()

    db_cfg, dry_run, log_path = load_config()
    rules, defaults, groups = load_thresholds_config()
    setup_logger(log_path)

    conn = pymysql.connect(**db_cfg)
    cur = conn.cursor()

    query = """
        SELECT am.id_agente_modulo, a.nombre AS agente_nombre, am.nombre AS modulo_nombre,
               am.descripcion AS module_description,
               am.min_critical, am.max_critical, am.min_warning, am.max_warning,
               am.critical_instructions, a.id_grupo
        FROM tagente_modulo am
        JOIN tagente a ON a.id_agente = am.id_agente
        WHERE am.disabled = 0 AND a.disabled = 0
    """
    if groups:
        query += f" AND a.id_grupo IN ({', '.join(map(str, groups))})"

    logging.info(f"📋 Procesando grupos: {groups if groups else 'todos los activos'}")
    cur.execute(query)
    rows = cur.fetchall()

    updates = []
    for row in rows:
        agent, module, desc = (
            html.unescape(row[k] or "").strip()
            for k in ["agente_nombre", "modulo_nombre", "module_description"]
        )
        rule = match_rule(agent, module, desc, rules)
        if not rule and not defaults:
            continue

        fields = rule or defaults
        set_parts, values, changes = [], [], []

        for k, v in fields.items():
            if k in (
                "name", "agent_name_pattern", "agent_name_includes",
                "agent_name_excludes", "module_name_pattern", "module_description_pattern"
            ):
                continue
            if should_update(row.get(k), v, args.force):
                set_parts.append(f"{k} = %s")
                values.append(v)
                changes.append((k, row.get(k), v))

        if set_parts:
            sql = f"UPDATE tagente_modulo SET {', '.join(set_parts)} WHERE id_agente_modulo = %s"
            values.append(row["id_agente_modulo"])
            updates.append((sql, values, agent, module, rule, row["id_grupo"], changes))

    logging.info(f"🔍 {len(updates)} módulos a actualizar.")

    if not updates:
        logging.info("✅ No hay cambios pendientes.")
        conn.close()
        return

    mode = "FORCE" if args.force else ("DRY-RUN" if dry_run else "NORMAL")
    logging.info(f"🚀 Modo {mode}: aplicando {'simulación' if dry_run else 'actualizaciones'}.")

    for sql, vals, agent, module, rule, group, changes in updates:
        rule_name = rule.get("name") if rule else "default"
        logging.info(f"• Grupo {group} → {agent} / {module} ({rule_name})")
        for k, old, new in changes:
            logging.info(f"   - {k}: {old} → {new}")
        if not dry_run:
            cur.execute(sql, vals)

    if not dry_run:
        conn.commit()
        logging.info(f"✅ Actualizados {len(updates)} registros.")
    else:
        logging.info(f"💡 DRY-RUN activo, sin aplicar cambios.")

    conn.close()
    logging.info(f"📝 Log en: {log_path}\n")


if __name__ == "__main__":
    main()
