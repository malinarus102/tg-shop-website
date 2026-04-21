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
        data = request.json
        city = data.get('city', '').strip()
        order_price = data.get('orderPrice', 700)

        if not city:
            return jsonify({'success': False, 'message': 'Укажите город'}), 400

        cdek_client_id = os.getenv('CDEK_CLIENT_ID', '')
        cdek_client_secret = os.getenv('CDEK_CLIENT_SECRET', '')

        # Получаем токен СДЭК
        if cdek_client_id and cdek_client_secret:
            print(f"🚚 СДЭК: запрос токена для города '{city}'")
            token_resp = requests.post(
                'https://api.cdek.ru/v2/oauth/token',
                data={
                    'grant_type': 'client_credentials',
                    'client_id': cdek_client_id,
                    'client_secret': cdek_client_secret
                },
                timeout=10
            )
            print(f"🚚 СДЭК токен: status={token_resp.status_code}, body={token_resp.text[:200]}")
            if token_resp.status_code != 200:
                raise Exception(f'Не удалось получить токен СДЭК: {token_resp.text}')
            token = token_resp.json().get('access_token')
            if not token:
                raise Exception('Токен СДЭК пустой')

            # Ищем код города
            city_resp = requests.get(
                'https://api.cdek.ru/v2/location/cities',
                headers={'Authorization': f'Bearer {token}'},
                params={'city': city, 'country_codes': 'RU', 'size': 3},
                timeout=10
            )
            print(f"🚚 СДЭК города: status={city_resp.status_code}, body={city_resp.text[:300]}")
            cities = city_resp.json()
            if not cities:
                return jsonify({'success': False, 'message': f'Город «{city}» не найден в базе СДЭК'}), 200

            city_code = cities[0]['code']
            print(f"🚚 СДЭК: найден город code={city_code}, name={cities[0].get('city')}")

            # Тарифы: ПВЗ (136), Курьер (137), Экономичный ПВЗ (234), Экономичный Курьер (233)
            tariff_codes = [
                (136, 'СДЭК Экспресс — до ПВЗ', 'ПВЗ'),
                (137, 'СДЭК Экспресс — курьер', 'Курьер'),
                (234, 'СДЭК Экономичный — до ПВЗ', 'ПВЗ'),
                (233, 'СДЭК Экономичный — курьер', 'Курьер'),
            ]

            tariffs = []
            for code, name, delivery_type in tariff_codes:
                try:
                    payload = {
                        'tariff_code': code,
                        'from_location': {'city': 'Москва', 'country_code': 'RU'},
                        'to_location': {'code': city_code},
                        'packages': [{'weight': 100, 'length': 15, 'width': 10, 'height': 3}]
                    }
                    calc_resp = requests.post(
                        'https://api.cdek.ru/v2/calculator/tariff',
                        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                        json=payload,
                        timeout=10
                    )
                    print(f"🚚 Тариф {code}: status={calc_resp.status_code}, body={calc_resp.text[:300]}")
                    r = calc_resp.json()
                    # СДЭК возвращает total_sum или delivery_sum
                    price = r.get('total_sum') or r.get('delivery_sum')
                    if price:
                        tariffs.append({
                            'tariff_code': code,
                            'name': name,
                            'delivery_type': delivery_type,
                            'price': int(price),
                            'period_min': r.get('period_min', 1),
                            'period_max': r.get('period_max', 7),
                        })
                    else:
                        print(f"⚠️ Тариф {code}: нет цены в ответе: {r}")
                except Exception as e:
                    print(f"⚠️ Тариф {code}: исключение: {e}")
                    continue

            if not tariffs:
                return jsonify({'success': False, 'message': 'Не удалось рассчитать тарифы для этого города. Оформите заказ — уточним стоимость вручную.'}), 200

            tariffs.sort(key=lambda x: x['price'])
            return jsonify({'success': True, 'tariffs': tariffs})

        else:
            # СДЭК не настроен — возвращаем фиксированные тарифы-заглушки
            print("⚠️ CDEK_CLIENT_ID/SECRET не заданы — возвращаем фиксированные тарифы")
            tariffs = [
                {'tariff_code': 136, 'name': 'СДЭК — до ПВЗ', 'delivery_type': 'ПВЗ',
                 'price': 250, 'period_min': 2, 'period_max': 5},
                {'tariff_code': 137, 'name': 'СДЭК — курьер', 'delivery_type': 'Курьер',
                 'price': 350, 'period_min': 2, 'period_max': 5},
            ]
            return jsonify({'success': True, 'tariffs': tariffs})

    except Exception as e:
        print(f"❌ Ошибка расчёта доставки: {e}")
        return jsonify({'success': False, 'message': 'Ошибка расчёта доставки. Оформите заказ — менеджер уточнит стоимость.'}), 200


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
        
        wrist_size = data.get('wristSize', 0)
        links_count = data.get('linksCount', 0)
        total_price = data.get('totalPrice', 0)
        links = data.get('links', [])
        user_name = data.get('userName', 'Аноним')
        user_phone = data.get('userPhone', 'Не указан')
        user_tg = data.get('userTg', 'Не указан')
        user_city = data.get('userCity', 'Не указан')

        # Подсчитываем звенья по командам + детали дизайнов
        team_counts = {}
        design_details = {}  # "TeamName / DesignId" -> count
        for link in links:
            team = link.get('teamName', 'Unknown')
            team_counts[team] = team_counts.get(team, 0) + 1
            design_id = link.get('designId', '')
            design_image = link.get('designImage', design_id)
            key = f"{team} / {design_image}"
            design_details[key] = design_details.get(key, 0) + 1

        # Сохраняем заказ в памяти
        order_counter += 1
        order_obj = {
            'id': order_counter,
            'wristSize': wrist_size,
            'linksCount': links_count,
            'totalPrice': total_price,
            'composition': team_counts,
            'designDetails': design_details,
            'links': links,
            'userName': user_name,
            'userPhone': user_phone,
            'userTg': user_tg,
            'userCity': user_city,
            'createdAt': datetime.now().isoformat(),
            'status': 'новый',
            'deliveryPrice': data.get('deliveryPrice', 0),
            'deliveryTariff': data.get('deliveryTariff', None)
        }
        orders_storage.append(order_obj)
        save_orders_storage()
        
        print(f"\n{'='*60}")
        print(f"✅ НОВЫЙ ЗАКАЗ #{order_counter}")
        print(f"{'='*60}")
        print(f"👤 Клиент: {user_name}")
        print(f"📱 Телефон: {user_phone}")
        print(f"🔷 Telegram: {user_tg}")
        print(f"🏙️ Город: {user_city}")
        print(f"📏 Размер запястья: {wrist_size} см")
        print(f"🔗 Звеньев: {links_count}")
        print(f"💰 Сумма: {total_price}₽")
        print(f"📋 Состав: {team_counts}")
        print(f"⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        print(f"📦 Всего заказов: {len(orders_storage)}")
        print(f"{'='*60}\n")

        # Формируем сообщение для Telegram
        message = f"""
📦 <b>🚨 НОВЫЙ ЗАКАЗ БРАСЛЕТА F1! #{order_counter}</b>

👤 <b>Клиент:</b> {user_name}
📱 <b>Телефон:</b> <code>{user_phone}</code>
🔷 <b>Telegram:</b> {user_tg}
🏙️ <b>Город:</b> {user_city}

📏 <b>Размер запястья:</b> {wrist_size} см
🔗 <b>Всего звеньев:</b> {links_count}
💰 <b>Итоговая сумма:</b> <b>{total_price}₽</b>

📋 <b>СОСТАВ БРАСЛЕТА:</b>
"""
        
        for team, count in sorted(team_counts.items()):
            message += f"\n  • {team}: {count} звеньев"

        # Детальный состав по дизайнам
        if design_details:
            message += f"\n\n🎨 <b>ДИЗАЙНЫ:</b>"
            for design_key, count in sorted(design_details.items()):
                message += f"\n  · {design_key} × {count}"
        
        message += f"\n\n✅ Статус: <b>НОВЫЙ</b>"
        message += f"\n⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        admin_url = os.getenv('ADMIN_URL', 'http://127.0.0.1:8080/admin')
        message += f"\n\n<a href='{admin_url}'>📊 ПЕРЕЙТИ В АДМИНКУ</a>"

        # Отправляем в Telegram
        if BOT_TOKEN and ADMIN_ID:
            send_to_telegram(BOT_TOKEN, ADMIN_ID, message)
            return jsonify({'success': True, 'message': 'Заказ принят!', 'orderId': order_counter})
        else:
            print("⚠️ BOT_TOKEN или ADMIN_ID не установлены - заказ сохранен локально")
            return jsonify({'success': True, 'message': 'Заказ принят!', 'orderId': order_counter})

    except Exception as e:
        print(f"❌ Ошибка при обработке заказа: {e}")
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

if __name__ == '__main__':
    app.run(debug=True, port=8080, host='127.0.0.1')