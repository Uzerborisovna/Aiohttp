import json
from aiohttp import web
from datetime import datetime
import aiosqlite


# --- Работа с базой данных ---

async def init_db(app):
    """Создаем таблицу при запуске сервера."""
    async with aiosqlite.connect("ads.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL,
                owner TEXT NOT NULL
            )
        """)
        await db.commit()
    # Сохраняем подключение в приложении (для доступа из хендлеров)
    app['db'] = await aiosqlite.connect("ads.db")


async def close_db(app):
    """Закрываем базу при выключении сервера."""
    await app['db'].close()


# --- 1. GET: Получить все объявления ---
async def get_ads(request):
    async with app['db'].execute("SELECT * FROM ads") as cursor:
        rows = await cursor.fetchall()

    # Превращаем строки в словари
    ads = [
        {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "created_at": row[3],
            "owner": row[4]
        }
        for row in rows
    ]
    return web.json_response(ads, status=200, dumps=lambda x: json.dumps(x, ensure_ascii=False))


# --- 2. POST: Создать новое объявление ---
async def create_ad(request):
    try:
        body = await request.text()
        data = json.loads(body)
    except Exception as e:
        return web.json_response({"error": f"Некорректный JSON: {str(e)}"}, status=400,
                                 dumps=lambda x: json.dumps(x, ensure_ascii=False))

    if not data or 'title' not in data or 'description' not in data or 'owner' not in data:
        return web.json_response({"error": "Нужны поля: title, description, owner"}, status=400,
                                 dumps=lambda x: json.dumps(x, ensure_ascii=False))

    async with app['db'].execute(
            "INSERT INTO ads (title, description, created_at, owner) VALUES (?, ?, ?, ?)",
            (data['title'], data['description'], datetime.now().isoformat(), data['owner'])
    ) as cursor:
        ad_id = cursor.lastrowid
    await app['db'].commit()

    new_ad = {
        "id": ad_id,
        "title": data['title'],
        "description": data['description'],
        "created_at": datetime.now().isoformat(),
        "owner": data['owner']
    }
    return web.json_response(new_ad, status=201, dumps=lambda x: json.dumps(x, ensure_ascii=False))


# --- 3. GET /ads/{id}/: Получить одно объявление ---
async def get_ad(request):
    ad_id = int(request.match_info['ad_id'])
    async with app['db'].execute("SELECT * FROM ads WHERE id = ?", (ad_id,)) as cursor:
        row = await cursor.fetchone()

    if not row:
        return web.json_response({"error": "Объявление не найдено"}, status=404,
                                 dumps=lambda x: json.dumps(x, ensure_ascii=False))

    ad = {
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "created_at": row[3],
        "owner": row[4]
    }
    return web.json_response(ad, status=200, dumps=lambda x: json.dumps(x, ensure_ascii=False))


# --- 4. PUT /ads/{id}/: Полное обновление объявления ---
async def update_ad_put(request):
    ad_id = int(request.match_info['ad_id'])
    try:
        body = await request.text()
        data = json.loads(body)
    except Exception as e:
        return web.json_response({"error": f"Некорректный JSON: {str(e)}"}, status=400,
                                 dumps=lambda x: json.dumps(x, ensure_ascii=False))

    # Для PUT нужны все поля
    if not data or 'title' not in data or 'description' not in data or 'owner' not in data:
        return web.json_response({"error": "Для PUT нужны поля: title, description, owner"}, status=400,
                                 dumps=lambda x: json.dumps(x, ensure_ascii=False))

    async with app['db'].execute(
            "UPDATE ads SET title = ?, description = ?, owner = ? WHERE id = ?",
            (data['title'], data['description'], data['owner'], ad_id)
    ) as cursor:
        if cursor.rowcount == 0:
            return web.json_response({"error": "Объявление не найдено"}, status=404,
                                     dumps=lambda x: json.dumps(x, ensure_ascii=False))
    await app['db'].commit()

    async with app['db'].execute("SELECT * FROM ads WHERE id = ?", (ad_id,)) as cursor:
        row = await cursor.fetchone()

    ad = {
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "created_at": row[3],
        "owner": row[4]
    }
    return web.json_response(ad, status=200, dumps=lambda x: json.dumps(x, ensure_ascii=False))


# --- 5. PATCH /ads/{id}/: Частичное обновление ---
async def update_ad_patch(request):
    ad_id = int(request.match_info['ad_id'])
    try:
        body = await request.text()
        data = json.loads(body)
    except Exception as e:
        return web.json_response({"error": f"Некорректный JSON: {str(e)}"}, status=400,
                                 dumps=lambda x: json.dumps(x, ensure_ascii=False))

    # Проверяем, что объявление существует
    async with app['db'].execute("SELECT * FROM ads WHERE id = ?", (ad_id,)) as cursor:
        row = await cursor.fetchone()
    if not row:
        return web.json_response({"error": "Объявление не найдено"}, status=404,
                                 dumps=lambda x: json.dumps(x, ensure_ascii=False))

    # Обновляем только те поля, которые пришли
    updates = []
    values = []
    if 'title' in data:
        updates.append("title = ?")
        values.append(data['title'])
    if 'description' in data:
        updates.append("description = ?")
        values.append(data['description'])
    if 'owner' in data:
        updates.append("owner = ?")
        values.append(data['owner'])

    if not updates:
        return web.json_response({"error": "Нет полей для обновления"}, status=400,
                                 dumps=lambda x: json.dumps(x, ensure_ascii=False))

    values.append(ad_id)
    await app['db'].execute(f"UPDATE ads SET {', '.join(updates)} WHERE id = ?", values)
    await app['db'].commit()

    async with app['db'].execute("SELECT * FROM ads WHERE id = ?", (ad_id,)) as cursor:
        row = await cursor.fetchone()

    ad = {
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "created_at": row[3],
        "owner": row[4]
    }
    return web.json_response(ad, status=200, dumps=lambda x: json.dumps(x, ensure_ascii=False))


# --- 6. DELETE: Удалить объявление ---
async def delete_ad(request):
    ad_id = int(request.match_info['ad_id'])
    async with app['db'].execute("DELETE FROM ads WHERE id = ?", (ad_id,)) as cursor:
        if cursor.rowcount == 0:
            return web.json_response({"error": "Объявление не найдено"}, status=404,
                                     dumps=lambda x: json.dumps(x, ensure_ascii=False))
    await app['db'].commit()

    return web.json_response({"message": f"Объявление {ad_id} удалено"}, status=200,
                             dumps=lambda x: json.dumps(x, ensure_ascii=False))


# --- Создаём приложение и регистрируем маршруты ---
app = web.Application()
app.on_startup.append(init_db)
app.on_cleanup.append(close_db)

app.add_routes([
    web.get('/ads/', get_ads),
    web.post('/ads/', create_ad),
    web.get('/ads/{ad_id}/', get_ad),
    web.put('/ads/{ad_id}/', update_ad_put),
    web.patch('/ads/{ad_id}/', update_ad_patch),
    web.delete('/ads/{ad_id}/', delete_ad),
])

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)