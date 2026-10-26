import json
from aiohttp import web
from datetime import datetime

# Временная "база данных" (список объявлений)
ads = []


# --- 1. GET: Получить все объявления ---
async def get_ads(request):
    return web.json_response(ads, status=200, dumps=lambda x: json.dumps(x, ensure_ascii=False))


# --- 2. POST: Создать новое объявление ---
async def create_ad(request):
    try:
        body = await request.text()
        data = json.loads(body)
    except Exception as e:
        return web.json_response({"error": f"Некорректный JSON: {str(e)}"}, status=400, dumps=lambda x: json.dumps(x, ensure_ascii=False))

    if not data or 'title' not in data or 'description' not in data or 'owner' not in data:
        return web.json_response({"error": "Нужны поля: title, description, owner"}, status=400, dumps=lambda x: json.dumps(x, ensure_ascii=False))

    new_ad = {
        "id": len(ads) + 1,
        "title": data['title'],
        "description": data['description'],
        "created_at": datetime.now().isoformat(),
        "owner": data['owner']
    }

    ads.append(new_ad)
    return web.json_response(new_ad, status=201, dumps=lambda x: json.dumps(x, ensure_ascii=False))


# --- 3. DELETE: Удалить объявление по ID ---
async def delete_ad(request):
    ad_id = int(request.match_info['ad_id'])

    for ad in ads:
        if ad['id'] == ad_id:
            ads.remove(ad)
            return web.json_response({"message": f"Объявление {ad_id} удалено"}, status=200, dumps=lambda x: json.dumps(x, ensure_ascii=False))

    return web.json_response({"error": "Объявление не найдено"}, status=404, dumps=lambda x: json.dumps(x, ensure_ascii=False))


# --- 4. PATCH: Редактировать объявление ---
async def update_ad(request):
    ad_id = int(request.match_info['ad_id'])
    try:
        body = await request.text()
        data = json.loads(body)
    except Exception as e:
        return web.json_response({"error": f"Некорректный JSON: {str(e)}"}, status=400, dumps=lambda x: json.dumps(x, ensure_ascii=False))

    for ad in ads:
        if ad['id'] == ad_id:
            if 'title' in data:
                ad['title'] = data['title']
            if 'description' in data:
                ad['description'] = data['description']
            if 'owner' in data:
                ad['owner'] = data['owner']
            return web.json_response(ad, status=200, dumps=lambda x: json.dumps(x, ensure_ascii=False))

    return web.json_response({"error": "Объявление не найдено"}, status=404, dumps=lambda x: json.dumps(x, ensure_ascii=False))


# --- Создаём приложение и регистрируем маршруты ---
app = web.Application()
app.add_routes([
    web.get('/ads/', get_ads),
    web.post('/ads/', create_ad),
    web.delete('/ads/{ad_id}/', delete_ad),
    web.patch('/ads/{ad_id}/', update_ad),
])

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)