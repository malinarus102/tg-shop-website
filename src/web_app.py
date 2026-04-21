import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from flask import Flask, render_template, jsonify, send_from_directory, request
from src.services.shop import get_all_teams, get_team_designs
import requests
from dotenv import load_dotenv
from datetime import datetime
import json

load_dotenv()

from src.config import Config
Config.validate()

app = Flask(__name__, template_folder='templates')

BOT_TOKEN = Config.BOT_TOKEN
ADMIN_ID = Config.ADMIN_CHAT_ID
ADMIN_PASSWORD = Config.ADMIN_PASSWORD

# Хранилище заказов в памяти (в продакшене - база данных!)
orders_storage = []
order_counter = 0
ORDERS_FILE = os.path.join(os.path.dirname(__file__), 'orders.json')


def load_orders_storage():
    """Загрузить заказы из файла при старте."""
    global orders_storage, order_counter
    if not os.path.exists(ORDERS_FILE):
        orders_storage = []
        order_counter = 0
        return

    try:
        with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        if isinstance(loaded, list):
            orders_storage = loaded
            order_counter = max((int(o.get('id', 0)) for o in orders_storage), default=0)
        else:
            orders_storage = []
            order_counter = 0
    except Exception as e:
        print(f"⚠️ Ошибка загрузки orders.json: {e}")
        orders_storage = []
        order_counter = 0


def save_orders_storage():
    """Сохранить заказы в файл."""
    try:
        with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(orders_storage, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Ошибка сохранения orders.json: {e}")


load_orders_storage()

# Состояние магазина — открыт/закрыт
shop_is_open = True

@app.route('/api/shop/status')
def shop_status():
    """Текущий статус магазина — открыт или закрыт."""
    return jsonify({'is_open': shop_is_open})

@app.route('/api/delivery/calculate', methods=['POST'])
def calculate_delivery():
    """Рассчитать стоимость доставки СДЭК."""
    try:
        data = request.get_json(silent=True) or {}
        city = str(data.get('city', '')).strip()
        order_price = data.get('orderPrice', 700)

        if not city:
            return jsonify({'success': False, 'message': 'Укажите город'}), 400

        cdek_client_id = os.getenv('CDEK_CLIENT_ID', '').strip()
        cdek_client_secret = os.getenv('CDEK_CLIENT_SECRET', '').strip()

        if not cdek_client_id or not cdek_client_secret:
            print("⚠️ CDEK_CLIENT_ID/SECRET не заданы — возвращаем фиксированные тарифы")
            tariffs = [
                {'tariff_code': 136, 'name': 'СДЭК — до ПВЗ', 'delivery_type': 'ПВЗ',
                 'price': 250, 'period_min': 2, 'period_max': 5},
                {'tariff_code': 137, 'name': 'СДЭК — курьер', 'delivery_type': 'Курьер',
                 'price': 350, 'period_min': 2, 'period_max': 5},
            ]
            return jsonify({'success': True, 'tariffs': tariffs})

        print(f"🚚 СДЭК: расчёт для города '{city}', сумма заказа {order_price}")

        token_resp = requests.post(
            'https://api.cdek.ru/v2/oauth/token',
            data={
                'grant_type': 'client_credentials',
                'client_id': cdek_client_id,
                'client_secret': cdek_client_secret
            },
            timeout=15
        )
        print(f"🚚 СДЭК токен: status={token_resp.status_code}, body={token_resp.text[:300]}")

        if token_resp.status_code != 200:
            return jsonify({
                'success': False,
                'message': 'Ошибка авторизации в СДЭК. Проверьте CDEK_CLIENT_ID и CDEK_CLIENT_SECRET.'
            }), 200

        token = token_resp.json().get('access_token')
        if not token:
            return jsonify({'success': False, 'message': 'СДЭК не вернул access_token'}), 200

        headers = {'Authorization': f'Bearer {token}'}

        city_resp = requests.get(
            'https://api.cdek.ru/v2/location/cities',
            headers=headers,
            params={'city': city, 'country_codes': 'RU', 'size': 10},
            timeout=15
        )
        print(f"🚚 СДЭК города: status={city_resp.status_code}, body={city_resp.text[:500]}")

        if city_resp.status_code != 200:
            return jsonify({'success': False, 'message': 'Ошибка поиска города в базе СДЭК'}), 200

        cities = city_resp.json()
        if not isinstance(cities, list) or not cities:
            return jsonify({'success': False, 'message': f'Город «{city}» не найден в базе СДЭК'}), 200

        city_code = cities[0].get('code')
        if not city_code:
            return jsonify({'success': False, 'message': f'Для города «{city}» не найден код СДЭК'}), 200

        print(f"🚚 СДЭК: найден город code={city_code}, name={cities[0].get('city')}")

        tariff_codes = [
            (136, 'СДЭК Экспресс — до ПВЗ', 'ПВЗ'),
            (137, 'СДЭК Экспресс — курьер', 'Курьер'),
            (234, 'СДЭК Экономичный — до ПВЗ', 'ПВЗ'),
            (233, 'СДЭК Экономичный — курьер', 'Курьер'),
        ]

        tariffs = []
        for code, name, delivery_type in tariff_codes:
            payload = {
                'tariff_code': code,
                'from_location': {'city': 'Москва', 'country_code': 'RU'},
                'to_location': {'code': city_code},
                'packages': [{'weight': 300, 'length': 15, 'width': 10, 'height': 3}]
            }

            try:
                calc_resp = requests.post(
                    'https://api.cdek.ru/v2/calculator/tariff',
                    headers={**headers, 'Content-Type': 'application/json'},
                    json=payload,
                    timeout=15
                )
                print(f"🚚 Тариф {code}: status={calc_resp.status_code}, body={calc_resp.text[:500]}")

                if calc_resp.status_code != 200:
                    continue

                r = calc_resp.json()
                price = r.get('total_sum') or r.get('delivery_sum')
                if price is None:
                    print(f"⚠️ Тариф {code}: нет цены в ответе: {r}")
                    continue

                tariffs.append({
                    'tariff_code': code,
                    'name': name,
                    'delivery_type': delivery_type,
                    'price': int(float(price)),
                    'period_min': r.get('period_min', 1),
                    'period_max': r.get('period_max', 7),
                })
            except Exception as tariff_error:
                print(f"⚠️ Тариф {code}: исключение: {repr(tariff_error)}")
                continue

        if not tariffs:
            return jsonify({
                'success': False,
                'message': 'СДЭК не вернул ни одного тарифа. Проверьте лог сервера.'
            }), 200

        tariffs.sort(key=lambda x: x['price'])
        return jsonify({'success': True, 'tariffs': tariffs})

    except Exception as e:
        print(f"❌ Ошибка расчёта доставки: {repr(e)}")
        return jsonify({
            'success': False,
            'message': 'Ошибка расчёта доставки. Подробности смотрите в логе сервера.'
        }), 200


@app.route('/api/admin/shop/toggle', methods=['POST'])
def toggle_shop():
    """Открыть или закрыть приём заказов."""
    global shop_is_open
    shop_is_open = not shop_is_open
    status = 'открыт' if shop_is_open else 'закрыт'
    print(f"🏁 Магазин {status}")
    return jsonify({'is_open': shop_is_open})

@app.route('/')
def index():
    return render_template('catalog.html')

@app.route('/admin')
def admin_panel():
    return render_template('admin.html')

@app.route('/api/pic/<team_id>/<filename>')
def serve_pic(team_id, filename):
    try:
        pic_path = os.path.join(os.path.dirname(__file__), 'pics', team_id)
        return send_from_directory(pic_path, filename)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return '', 404

@app.route('/api/teams')
def get_teams():
    teams = get_all_teams()
    return jsonify([{
        'id': team_id,
        'name': team_data['name'],
        'color': team_data['color'],
        'drivers': team_data['drivers'],
        'designsCount': len(team_data['designs'])
    } for team_id, team_data in teams.items()])

@app.route('/api/teams/<team_id>/designs')
def get_designs(team_id):
    designs = get_team_designs(team_id)
    return jsonify([{
        'id': design['id'],
        'name': design['name'],
        'image': design['image']
    } for design in designs])

@app.route('/api/order', methods=['POST'])
def submit_order():
    global order_counter
    if not shop_is_open:
        return jsonify({'success': False, 'message': 'Магазин временно закрыт'}), 503
    try:
        data = request.json

        user_name  = data.get('userName', 'Аноним')
        user_phone = data.get('userPhone', 'Не указан')
        user_tg    = data.get('userTg', 'Не указан')
        user_city  = data.get('userCity', 'Не указан')
        total_price     = data.get('totalPrice', 0)
        delivery_price  = data.get('deliveryPrice', 0)
        delivery_tariff = data.get('deliveryTariff', None)

        # Поддержка нескольких браслетов
        bracelets_raw = data.get('bracelets', None)
        if not bracelets_raw:
            # старый формат — один браслет
            links = data.get('links', [])
            team_counts   = {}
            design_details = {}
            for link in links:
                team = link.get('teamName', 'Unknown')
                team_counts[team] = team_counts.get(team, 0) + 1
                key = f"{team} / {link.get('designImage', link.get('designId',''))}"
                design_details[key] = design_details.get(key, 0) + 1
            bracelets_raw = [{
                'braceletIndex': 1,
                'wristSize':  data.get('wristSize', 0),
                'linksCount': data.get('linksCount', 0),
                'price': total_price - delivery_price,
                'composition': team_counts,
                'designDetails': design_details,
                'links': links,
                'referencePhoto': None,
            }]

        # Сохраняем референс-фото на диск (если есть)
        refs_dir = os.path.join(os.path.dirname(__file__), 'reference_photos')
        os.makedirs(refs_dir, exist_ok=True)
        reference_photo_paths = []
        for b in bracelets_raw:
            ref_data_url = b.get('referencePhoto')
            if ref_data_url and ref_data_url.startswith('data:image'):
                try:
                    import base64
                    header, encoded = ref_data_url.split(',', 1)
                    ext = 'jpg'
                    if 'png' in header: ext = 'png'
                    elif 'gif' in header: ext = 'gif'
                    fname = f"ref_{datetime.now().strftime('%Y%m%d_%H%M%S')}_br{b.get('braceletIndex',1)}.{ext}"
                    fpath = os.path.join(refs_dir, fname)
                    with open(fpath, 'wb') as f:
                        f.write(base64.b64decode(encoded))
                    b['referencePhotoPath'] = fname
                    reference_photo_paths.append((b.get('braceletIndex', 1), fpath))
                    b['referencePhoto'] = None  # не храним base64 в orders.json
                except Exception as e:
                    print(f"⚠️ Не удалось сохранить референс: {e}")

        order_counter += 1
        bracelets_count = len(bracelets_raw)
        total_links = sum(b.get('linksCount', 0) for b in bracelets_raw)

        order_obj = {
            'id': order_counter,
            # legacy поля (первый браслет)
            'wristSize':  bracelets_raw[0].get('wristSize', 0),
            'linksCount': bracelets_raw[0].get('linksCount', 0),
            'composition': bracelets_raw[0].get('composition', {}),
            'designDetails': bracelets_raw[0].get('designDetails', {}),
            # полные данные
            'bracelets': bracelets_raw,
            'braceletsCount': bracelets_count,
            'totalPrice':    total_price,
            'userName':  user_name,
            'userPhone': user_phone,
            'userTg':    user_tg,
            'userCity':  user_city,
            'createdAt': datetime.now().isoformat(),
            'status':    'новый',
            'deliveryPrice':  delivery_price,
            'deliveryTariff': delivery_tariff,
        }
        orders_storage.append(order_obj)
        save_orders_storage()

        print(f"\n{'='*60}")
        print(f"✅ НОВЫЙ ЗАКАЗ #{order_counter} ({bracelets_count} браслет(ов))")
        print(f"👤 {user_name} | 📱 {user_phone} | 🔷 {user_tg} | 🏙️ {user_city}")
        print(f"💰 {total_price}₽ | 🔗 {total_links} звеньев суммарно")
        print(f"{'='*60}\n")

        # ── Telegram сообщение ──
        plural_br = 'браслет' if bracelets_count == 1 else ('браслета' if bracelets_count < 5 else 'браслетов')
        message = (
            f"📦 <b>🚨 НОВЫЙ ЗАКАЗ F1! #{order_counter}</b>"
            f" — {bracelets_count} {plural_br}\n\n"
            f"👤 <b>Клиент:</b> {user_name}\n"
            f"📱 <b>Телефон:</b> <code>{user_phone}</code>\n"
            f"🔷 <b>Telegram:</b> {user_tg}\n"
            f"🏙️ <b>Город:</b> {user_city}\n"
            f"💰 <b>Итого:</b> <b>{total_price}₽</b>"
        )
        if delivery_price:
            message += f"\n🚚 <b>Доставка СДЭК:</b> {delivery_price}₽"

        for b in bracelets_raw:
            idx   = b.get('braceletIndex', 1)
            br_price = b.get('price', 0)
            wrist = b.get('wristSize', '?')
            lc    = b.get('linksCount', 0)
            has_ref = bool(b.get('referencePhotoPath'))
            message += f"\n\n{'─'*30}\n🔗 <b>Браслет {idx}</b>  {br_price}₽"
            if has_ref: message += "  📎 <i>есть референс</i>"
            message += f"\n📏 Запястье: {wrist} см · {lc} звеньев"
            comp = b.get('composition', {})
            if comp:
                message += "\n📋 Состав: " + ", ".join(f"{t}: {c}" for t, c in sorted(comp.items()))
            dd = b.get('designDetails', {})
            if dd:
                message += "\n🎨 Дизайны:"
                for dk, dc in sorted(dd.items()):
                    message += f"\n  · {dk} ×{dc}"

        message += f"\n\n⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        admin_url = os.getenv('ADMIN_URL', 'http://127.0.0.1:8080/admin')
        message += f"\n<a href='{admin_url}'>📊 Открыть админку</a>"

        if BOT_TOKEN and ADMIN_ID:
            send_to_telegram(BOT_TOKEN, ADMIN_ID, message)
            # Отправляем референс-фото отдельными сообщениями
            for br_idx, fpath in reference_photo_paths:
                try:
                    send_photo_to_telegram(BOT_TOKEN, ADMIN_ID, fpath,
                        caption=f"📎 Референс к заказу #{order_counter}, браслет {br_idx}")
                except Exception as e:
                    print(f"⚠️ Не удалось отправить фото: {e}")
        else:
            print("⚠️ BOT_TOKEN или ADMIN_ID не установлены — заказ сохранён локально")

        return jsonify({'success': True, 'message': 'Заказ принят!', 'orderId': order_counter})

    except Exception as e:
        print(f"❌ Ошибка при обработке заказа: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Вход администратора"""
    data = request.json
    password = data.get('password', '')
    
    if password == ADMIN_PASSWORD:
        return jsonify({'success': True, 'message': 'Вход выполнен'})
    else:
        return jsonify({'success': False, 'message': 'Неверный пароль'}), 401

@app.route('/api/admin/orders')
def get_orders():
    """Получить все заказы"""
    return jsonify(sorted(orders_storage, key=lambda x: x['id'], reverse=True))

@app.route('/api/admin/order/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Обновить статус заказа"""
    data = request.json
    new_status = data.get('status', '')
    
    for order in orders_storage:
        if order['id'] == order_id:
            order['status'] = new_status
            save_orders_storage()
            print(f"✅ Заказ #{order_id} статус изменен на: {new_status}")
            return jsonify({'success': True, 'order': order})
    
    return jsonify({'success': False, 'message': 'Заказ не найден'}), 404

@app.route('/api/admin/order/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    """Удалить заказ"""
    global orders_storage
    orders_storage = [o for o in orders_storage if o['id'] != order_id]
    save_orders_storage()
    print(f"✅ Заказ #{order_id} удален")
    return jsonify({'success': True})

def send_to_telegram(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Заказ отправлен администратору (ID: {chat_id})")
        else:
            print(f"❌ Ошибка отправки: {response.text}")
    except Exception as e:
        print(f"❌ Ошибка подключения к Telegram: {e}")


def send_photo_to_telegram(token, chat_id, photo_path, caption=''):
    """Отправить фото-референс в Telegram."""
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo_file:
            response = requests.post(url, data={
                'chat_id': chat_id,
                'caption': caption,
                'parse_mode': 'HTML'
            }, files={'photo': photo_file}, timeout=30)
        if response.status_code == 200:
            print(f"✅ Референс-фото отправлено")
        else:
            print(f"❌ Ошибка отправки фото: {response.text}")
    except Exception as e:
        print(f"❌ Ошибка отправки фото: {e}")

if __name__ == '__main__':
    app.run(debug=True, port=8080, host='127.0.0.1')