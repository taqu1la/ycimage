from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "backend" / "data" / "app.db"

sys.path.insert(0, str(ROOT / "backend" / "scripts"))

from init_db import apply_schema, insert_asset, insert_model_routes, json_dumps, now, slugify  # noqa: E402


VIDEO_CATEGORY_ID = "cat_video_generation"
SOURCE_ID = "src_apimart_video_templates"


VIDEO_MEDIA = [
    ("asset_apimart_og", "template_cover", "assets/apimart-video-promos/apimart-og.png"),
    ("asset_apimart_omni_flash_ext", "other", "assets/apimart-video-promos/omni-flash-ext.webm"),
    ("asset_apimart_kling_motion", "other", "assets/apimart-video-promos/kling-motion-control.webm"),
    ("asset_apimart_happyhorse", "other", "assets/apimart-video-promos/happyhorse.webm"),
    ("asset_apimart_skyreels_v4", "other", "assets/apimart-video-promos/skyreels-v4.mp4"),
]


VIDEO_TEMPLATES = [
    {
        "id": "tpl_video_product_dolly_in",
        "title": "商品主图轻推近",
        "description": "把静态商品主图变成 5-8 秒电商展示短片，适合朋友圈、小红书和店铺首屏。",
        "category": "电商视频",
        "route": "route_wan26_i2v_flash",
        "cover": "assets/awesome-gpt-image-2/data/images/case475.jpg",
        "promo": "assets/apimart-video-promos/kling-motion-control.webm",
        "featured": 1,
        "cost": 20,
        "ratio": "9:16",
        "size": "720p",
        "allow_ref": 1,
        "prompt": "以参考图中的商品为唯一主体，生成一段竖版电商短视频。镜头从中景缓慢推近，商品保持清晰稳定，背景出现柔和光影和轻微景深变化，突出{卖点}。整体风格为{风格}，画面干净高级，不添加多余文字，不改变商品结构。",
        "params": [
            {"key": "selling_point", "label": "卖点", "token": "{卖点}", "default": "质感、细节和使用场景", "type": "text"},
            {"key": "style", "label": "风格", "token": "{风格}", "default": "高端商业广告", "type": "text"},
        ],
    },
    {
        "id": "tpl_video_pet_memory",
        "title": "宠物照片治愈动效",
        "description": "让宠物照片自然动起来，适合纪念卡、头像视频和短视频封面。",
        "category": "生活视频",
        "route": "route_wan26_i2v_flash",
        "cover": "assets/awesome-gpt-image-2/data/images/case417.jpg",
        "promo": "assets/apimart-video-promos/happyhorse.webm",
        "featured": 1,
        "cost": 18,
        "ratio": "9:16",
        "size": "720p",
        "allow_ref": 1,
        "prompt": "根据参考图生成一段治愈宠物短视频。宠物保持原本外观和身份特征，出现轻微眨眼、抬头和柔和呼吸感，镜头轻微环绕，背景是{背景氛围}，光线温暖自然，整体情绪{情绪}，不要夸张变形。",
        "params": [
            {"key": "mood", "label": "情绪", "token": "{情绪}", "default": "温柔、陪伴感强", "type": "text"},
            {"key": "background", "label": "背景氛围", "token": "{背景氛围}", "default": "阳光洒进室内的安静场景", "type": "text"},
        ],
    },
    {
        "id": "tpl_video_local_ad",
        "title": "门店宣传短片",
        "description": "为咖啡店、美甲店、服装店和本地商户生成 6-8 秒宣传视频。",
        "category": "商户宣传",
        "route": "route_sora_2",
        "cover": "assets/awesome-gpt-image-2/data/images/case366.jpg",
        "promo": "assets/apimart-video-promos/skyreels-v4.mp4",
        "featured": 1,
        "cost": 35,
        "ratio": "16:9",
        "size": "720p",
        "allow_ref": 0,
        "prompt": "生成一段{门店类型}宣传短片，画面包含真实自然的门店环境、产品特写和顾客使用场景。镜头节奏清晰，有开场建立镜头、产品细节和收尾氛围镜头。风格为{风格}，适合社交媒体投放，不出现虚假品牌标识和不可读文字。",
        "params": [
            {"key": "store_type", "label": "门店类型", "token": "{门店类型}", "default": "精品咖啡店", "type": "text"},
            {"key": "style", "label": "视频风格", "token": "{风格}", "default": "温暖真实、轻商业广告感", "type": "text"},
        ],
    },
    {
        "id": "tpl_video_character_turn",
        "title": "人物转身微笑",
        "description": "把头像、写真或模特图转成自然人物短动效，适合服装和形象展示。",
        "category": "人物视频",
        "route": "route_wan26_i2v_flash",
        "cover": "assets/awesome-gpt-image-2/data/images/case378.jpg",
        "promo": "assets/apimart-video-promos/omni-flash-ext.webm",
        "featured": 1,
        "cost": 22,
        "ratio": "9:16",
        "size": "720p",
        "allow_ref": 1,
        "prompt": "基于参考图生成一段自然人物短视频。人物保持脸部身份、发型和服装一致，做轻微转身并自然微笑，镜头稳定推近，光线柔和，背景保持{背景}。动作真实克制，不改变五官，不出现额外人物。",
        "params": [
            {"key": "background", "label": "背景", "token": "{背景}", "default": "干净的杂志棚拍背景", "type": "text"},
        ],
    },
    {
        "id": "tpl_video_poster_motion",
        "title": "海报氛围动效",
        "description": "把海报、活动图、城市宣传图做成有层次的动态开屏视频。",
        "category": "海报动效",
        "route": "route_wan26_i2v_flash",
        "cover": "assets/awesome-gpt-image-2/data/images/case111.jpg",
        "promo": "assets/apimart-video-promos/skyreels-v4.mp4",
        "featured": 1,
        "cost": 20,
        "ratio": "16:9",
        "size": "720p",
        "allow_ref": 1,
        "prompt": "将参考海报转成动态视频开屏。保持核心版式、主体和色彩关系，加入轻微前后景层次、飘动粒子、柔和镜头推进和环境光变化。主题是{主题}，整体质感{质感}，不要破坏文字可读性。",
        "params": [
            {"key": "theme", "label": "主题", "token": "{主题}", "default": "城市活动宣传", "type": "text"},
            {"key": "texture", "label": "质感", "token": "{质感}", "default": "高级、干净、有电影感", "type": "text"},
        ],
    },
    {
        "id": "tpl_video_cyber_city",
        "title": "赛博城市文生视频",
        "description": "不上传图片也能从文字生成短视频，适合概念片、广告气氛片和提案素材。",
        "category": "概念视频",
        "route": "route_grok_imagine_video",
        "cover": "assets/awesome-gpt-image-2/data/images/case191.jpg",
        "promo": "assets/apimart-video-promos/omni-flash-ext.webm",
        "featured": 1,
        "cost": 20,
        "ratio": "16:9",
        "size": "720p",
        "allow_ref": 0,
        "prompt": "生成一段{城市主题}概念短视频，夜晚街道、霓虹反光、轻微雨雾、慢镜头穿行，画面有真实摄影质感和电影级光影。镜头从低角度进入城市空间，最后停在{收尾画面}。不要出现乱码文字。",
        "params": [
            {"key": "city_theme", "label": "城市主题", "token": "{城市主题}", "default": "未来赛博商业街区", "type": "text"},
            {"key": "ending", "label": "收尾画面", "token": "{收尾画面}", "default": "一块发光但无文字的品牌屏幕前", "type": "text"},
        ],
    },
]


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_video_category(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO template_categories(id, source_value, name_zh, name_en, slug, description, sort_order, is_active)
        VALUES (?, 'Video Generation', '视频生成', 'Video Generation', 'video-generation',
                '图生视频、文生视频和宣传动效模板', 18, 1)
        ON CONFLICT(id) DO UPDATE SET
            name_zh = excluded.name_zh,
            name_en = excluded.name_en,
            slug = excluded.slug,
            description = excluded.description,
            is_active = 1
        """,
        (VIDEO_CATEGORY_ID,),
    )


def ensure_source(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO template_sources(id, name, source_type, repository_url, license, synced_at, metadata_json)
        VALUES (?, 'APIMart 视频模板', 'manual', 'https://docs.apimart.ai', NULL, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            repository_url = excluded.repository_url,
            synced_at = excluded.synced_at,
            metadata_json = excluded.metadata_json
        """,
        (
            SOURCE_ID,
            now(),
            json_dumps({
                "provider": "APIMart",
                "docs": [
                    "/v1/videos/generations",
                    "/v1/tasks/{task_id}",
                    "/v1/uploads/images",
                ],
                "localPromoDir": "assets/apimart-video-promos",
            }),
        ),
    )


def upsert_media_assets(conn: sqlite3.Connection) -> None:
    for asset_id, asset_type, path in VIDEO_MEDIA:
        insert_asset(conn, asset_id, asset_type, path)


def upsert_video_template(conn: sqlite3.Connection, item: dict, index: int) -> None:
    cover_asset_id = f"asset_video_cover_{slugify(item['id']).replace('-', '_')}"
    insert_asset(conn, cover_asset_id, "template_cover", item["cover"])
    route = conn.execute("SELECT id FROM model_routes WHERE id = ? OR route_code = ?", (item["route"], item["route"])).fetchone()
    route_id = route["id"] if route else item["route"]
    metadata = {
        "modality": "video",
        "templateKind": "video",
        "provider": "APIMart",
        "promoVideo": item["promo"],
        "tags": ["视频", item["category"], "APIMart"],
        "scenes": ["Commerce", "Social", "Advertising"],
    }
    conn.execute(
        """
        INSERT INTO templates(
            id, source_id, source_template_id, case_id, category_id, title, description,
            prompt_template, negative_prompt, cover_asset_id, cover_url, image_alt,
            source_label, source_url, original_url, status, featured, credit_cost,
            default_model_route_id, default_quality, default_aspect_ratio, default_size,
            allow_reference_image, sort_score, usage_count, conversion_rate, metadata_json,
            created_by, created_at, updated_at
        )
        VALUES (?, ?, ?, NULL, ?, ?, ?, ?, NULL, ?, ?, ?, 'APIMart 视频模板',
                'https://docs.apimart.ai', NULL, 'enabled', ?, ?, ?, '720p', ?, ?,
                ?, ?, ?, ?, ?, 'user_admin', ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            source_id = excluded.source_id,
            category_id = excluded.category_id,
            title = excluded.title,
            description = excluded.description,
            prompt_template = excluded.prompt_template,
            cover_asset_id = excluded.cover_asset_id,
            cover_url = excluded.cover_url,
            image_alt = excluded.image_alt,
            source_label = excluded.source_label,
            source_url = excluded.source_url,
            status = excluded.status,
            featured = excluded.featured,
            credit_cost = excluded.credit_cost,
            default_model_route_id = excluded.default_model_route_id,
            default_quality = excluded.default_quality,
            default_aspect_ratio = excluded.default_aspect_ratio,
            default_size = excluded.default_size,
            allow_reference_image = excluded.allow_reference_image,
            sort_score = excluded.sort_score,
            usage_count = excluded.usage_count,
            conversion_rate = excluded.conversion_rate,
            metadata_json = excluded.metadata_json,
            updated_at = excluded.updated_at
        """,
        (
            item["id"],
            SOURCE_ID,
            item["id"],
            VIDEO_CATEGORY_ID,
            item["title"],
            item["description"],
            item["prompt"],
            cover_asset_id,
            item["cover"],
            item["title"],
            item["featured"],
            item["cost"],
            route_id,
            item["ratio"],
            item["size"],
            item["allow_ref"],
            1200 - index,
            86 - index * 4,
            14.2 - index,
            json_dumps(metadata),
            now(),
            now(),
        ),
    )
    conn.execute("DELETE FROM template_params WHERE template_id = ?", (item["id"],))
    for param_index, param in enumerate(item["params"]):
        conn.execute(
            """
            INSERT INTO template_params(
                id, template_id, param_key, label, token, default_value, param_type, required, options_json, sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, '[]', ?)
            """,
            (
                f"tparam_{item['id']}_{param_index + 1}",
                item["id"],
                param["key"],
                param["label"],
                param["token"],
                param["default"],
                param["type"],
                param_index,
            ),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync APIMart video templates and promotional media into SQLite.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()

    conn = connect(args.db)
    try:
        with conn:
            apply_schema(conn)
            insert_model_routes(conn)
            ensure_video_category(conn)
            ensure_source(conn)
            upsert_media_assets(conn)
            for index, item in enumerate(VIDEO_TEMPLATES):
                upsert_video_template(conn, item, index)
            conn.execute(
                """
                INSERT INTO admin_audit_logs(
                    id, actor_user_id, action, entity_type, entity_id, before_json, after_json,
                    ip_address, user_agent, created_at
                )
                VALUES (?, 'user_admin', 'template.sync_video_apimart', 'template_source',
                        ?, NULL, ?, '127.0.0.1', 'sync_video_templates.py', ?)
                """,
                (
                    f"audit_video_sync_{now().replace(':', '').replace('-', '').replace('+', '_')}",
                    SOURCE_ID,
                    json_dumps({"templates": len(VIDEO_TEMPLATES), "media": len(VIDEO_MEDIA)}),
                    now(),
                ),
            )
    finally:
        conn.close()

    print(f"Synced video templates: {len(VIDEO_TEMPLATES)}")
    print(f"Synced APIMart promo media: {len(VIDEO_MEDIA)}")


if __name__ == "__main__":
    main()
