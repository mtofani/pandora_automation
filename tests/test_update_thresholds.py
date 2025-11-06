import update_thresholds


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))
        normalized = query.strip().lower()
        if not normalized.startswith("select"):
            raise AssertionError(f"Unexpected SQL during dry-run: {query}")

    def fetchall(self):
        return self._rows


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.cursor_obj = FakeCursor(rows)
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        raise AssertionError("Dry-run should not attempt to commit.")

    def close(self):
        self.closed = True


def test_main_does_not_execute_updates_in_dry_run(monkeypatch, capsys):
    sample_rows = [
        {
            "id_agente_modulo": 1,
            "agente_nombre": "dedicado-ORA demo",
            "modulo_nombre": "Free Space",
        },
        {
            "id_agente_modulo": 2,
            "agente_nombre": "generic-agent",
            "modulo_nombre": "CPU Usage",
        },
    ]

    connections = []

    def fake_connect(**kwargs):
        conn = FakeConnection(sample_rows)
        connections.append(conn)
        return conn

    monkeypatch.setattr(update_thresholds.pymysql, "connect", fake_connect)

    update_thresholds.main()

    assert connections, "Script should attempt to create at least one DB connection."
    fake_cursor = connections[0].cursor_obj
    assert len(fake_cursor.executed) == 1
    assert fake_cursor.executed[0][0].strip().lower().startswith("select")

    captured = capsys.readouterr().out
    assert "Se encontraron 2 módulos a actualizar." in captured
    assert "Modo DRY-RUN activo" in captured
    assert "UPDATE tagente_modulo" in captured
    assert "[15, 95, 1]" in captured
    assert "[10, 2]" in captured

