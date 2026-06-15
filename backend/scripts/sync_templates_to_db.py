from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "backend" / "data" / "app.db"

sys.path.insert(0, str(ROOT / "backend" / "scripts"))

from init_db import (  # noqa: E402
    apply_schema,
    insert_all_case_images,
    insert_model_routes,
    insert_style_templates,
    insert_template_taxonomy,
    insert_templates,
    load_local_db,
    now,
)


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync GitHub template data into SQLite without deleting users, orders, jobs, or manual templates."
    )
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()

    db = load_local_db()
    conn = connect(args.db)
    try:
        with conn:
            apply_schema(conn)
            category_ids = insert_template_taxonomy(conn, db)
            insert_model_routes(conn)
            source_id = "src_awesome_gpt_image_2"
            repo_template_ids = [
                f"tpl_{item['id'].replace('-', '_')}"
                for item in db.get("templates", [])
            ]
            if repo_template_ids:
                placeholders = ",".join("?" for _ in repo_template_ids)
                conn.execute(
                    f"""
                    UPDATE templates
                    SET status = 'archived', updated_at = ?
                    WHERE source_id = ? AND id NOT IN ({placeholders})
                    """,
                    [now(), source_id, *repo_template_ids],
                )
                conn.execute(
                    f"DELETE FROM template_params WHERE template_id IN ({placeholders})",
                    repo_template_ids,
                )
                conn.execute(
                    f"DELETE FROM template_scene_map WHERE template_id IN ({placeholders})",
                    repo_template_ids,
                )
                conn.execute(
                    f"DELETE FROM template_tag_map WHERE template_id IN ({placeholders})",
                    repo_template_ids,
                )

            template_ids = insert_templates(conn, db, category_ids)
            insert_all_case_images(conn)
            conn.execute("DELETE FROM style_templates WHERE source_id = ?", (source_id,))
            insert_style_templates(conn, db, category_ids)
            conn.execute(
                """
                INSERT INTO app_settings(key, value, value_type, description, updated_at)
                VALUES ('site.home_template_limit', '30', 'number', '首页热门模板数量', ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    value_type = excluded.value_type,
                    description = excluded.description,
                    updated_at = excluded.updated_at
                """,
                (now(),),
            )
            conn.execute(
                """
                INSERT INTO admin_audit_logs(
                    id, actor_user_id, action, entity_type, entity_id, before_json, after_json,
                    ip_address, user_agent, created_at
                )
                VALUES (?, 'user_admin', 'template.sync_preserve_business_data', 'template_source',
                        ?, NULL, ?, '127.0.0.1', 'sync_templates_to_db.py', ?)
                """,
                (
                    f"audit_sync_{now().replace(':', '').replace('-', '').replace('+', '_')}",
                    source_id,
                    f'{{"templates":{len(template_ids)},"styles":{len(db.get("styleTemplates", []))}}}',
                    now(),
                ),
            )
    finally:
        conn.close()

    print(f"Synced templates: {len(db.get('templates', []))}")
    print(f"Synced style templates: {len(db.get('styleTemplates', []))}")
    print(f"Database preserved: users, orders, generation_jobs, manual templates")


if __name__ == "__main__":
    main()
