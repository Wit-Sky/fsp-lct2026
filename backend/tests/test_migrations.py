"""Существующая БД обновляется без потери профиля; номера миграций не конфликтуют."""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_upgrade_0003_to_head_preserves_profile(tmp_path):
    db = tmp_path / "old.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{db}", "PYTHONDONTWRITEBYTECODE": "1"}
    backend = Path(__file__).resolve().parents[1]

    def upgrade(revision):
        r = subprocess.run([sys.executable, "-m", "alembic", "upgrade", revision], cwd=backend,
                           env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr

    upgrade("0003")
    with sqlite3.connect(db) as c:
        c.execute("INSERT INTO users (id,email,password_hash,role,email_verified,is_demo,created_at) "
                  "VALUES (1,'old@example.ru','unused','candidate',1,0,CURRENT_TIMESTAMP)")
        c.execute("INSERT INTO candidate_profiles "
                  "(user_id,full_name,skills,roles,soft_skills,consent_pd,parent_consent,visible_fields,updated_at) "
                  "VALUES (1,'Существующий профиль','[\"Python\"]','[]','[]',1,0,'{}',CURRENT_TIMESTAMP)")
    upgrade("head")
    with sqlite3.connect(db) as c:
        assert c.execute("SELECT full_name,skills,fsp_skipped FROM candidate_profiles").fetchone() == (
            "Существующий профиль", '["Python"]', 0)
        assert c.execute("SELECT version_num FROM alembic_version").fetchone() == ("0004",)
        assert c.execute("SELECT count(*) FROM fsp_authorizations").fetchone() == (0,)
