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

import shutil
import threading
import hmac
import hashlib
from urllib.parse import unquote

# Хранилище заказов в памяти (в продакшене - база данных!)
orders_storage = []
order_counter = 0
ORDERS_FILE = os.path.join(os.path.dirname(__file__), 'orders.json')
_orders_lock = threading.Lock()  # защита от одновременной записи


def load_orders_storage():
    """Загрузить заказы из файла при старте.
    Если основной файл повреждён — пробуем восстановить из резервной копии.
    """
    global orders_storage, order_counter

    for path in [ORDERS_FILE, ORDERS_FILE + '.bak']:
        if not os.path.exists(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            if isinstance(loaded, list):
                orders_storage = loaded
                order_counter = max((int(o.get('id', 0)) for o in orders_storage), default=0)
                if path.endswith('.bak'):
                    print("⚠️ Основной файл повреждён — восстановлено из резервной копии")
                return
        except Exception as e:
            print(f"⚠️ Ошибка чтения {path}: {e}")

    orders_storage = []
    order_counter = 0
    print("⚠️ Файл заказов не найден — начинаем с чистого листа")


def save_orders_storage():
    """Атомарное сохранение заказов в файл.
    Сначала пишем во временный файл, потом атомарно заменяем основной.
    Перед заменой делаем резервную копию предыдущей версии.
    """
    tmp_path = ORDERS_FILE + '.tmp'
    bak_path = ORDERS_FILE + '.bak'

    with _orders_lock:
        try:
            # Пишем во временный файл
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(orders_storage, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())  # гарантируем запись на диск

            # Делаем резервную копию текущего файла
            if os.path.exists(ORDERS_FILE):
                shutil.copy2(ORDERS_FILE, bak_path)

            # Атомарно заменяем основной файл
            shutil.move(tmp_path, ORDERS_FILE)

        except Exception as e:
            print(f"⚠️ Ошибка сохранения orders.json: {e}")
            # Удаляем мусорный tmp если остался
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass


load_orders_storage()

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
    try:
        data = request.json

        init_data = data.get('initData', '')
        if init_data:
            if not validate_init_data(init_data, BOT_TOKEN):
                print("⚠️ Отклонён запрос с невалидным initData")
                return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        else:
            # initData не передан — разрешаем только в режиме отладки
            if not app.debug:
                print("⚠️ Отклонён запрос без initData")
                return jsonify({'success': False, 'message': 'initData required'}), 403

        wrist_size = data.get('wristSize', 0)
        links_count = data.get('linksCount', 0)
        total_price = data.get('totalPrice', 0)
        links = data.get('links', [])
        user_name = data.get('userName', 'Аноним')
        user_phone = data.get('userPhone', 'Не указан')
        user_tg = data.get('userTg', 'Не указан')
        user_city = data.get('userCity', 'Не указан')
        user_tg_id = data.get('userTgId')  # числовой Telegram ID для отправки подтверждения
        delivery_price = data.get('deliveryPrice', 0)
        delivery_tariff = data.get('deliveryTariff')

        team_counts = {}
        for link in links:
            team = link.get('teamName', 'Unknown')
            team_counts[team] = team_counts.get(team, 0) + 1

        order_counter += 1
        order_obj = {
            'id': order_counter,
            'wristSize': wrist_size,
            'linksCount': links_count,
            'totalPrice': total_price,
            'composition': team_counts,
            'userName': user_name,
            'userPhone': user_phone,
            'userTg': user_tg,
            'userCity': user_city,
            'userTgId': user_tg_id,
            'deliveryPrice': delivery_price,
            'deliveryTariff': delivery_tariff,
            'createdAt': datetime.now().isoformat(),
            'status': 'новый'
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

        message = f"""
📦 <b>🚨 НОВЫЙ ЗАКАЗ БРАСЛЕТА F1! #{order_counter}</b>

👤 <b>Клиент:</b> {user_name}
📱 <b>Телефон:</b> <code>{user_phone}</code>
🔷 <b>Telegram:</b> {user_tg}
🏙️ <b>Город:</b> {user_city}

📏 <b>Размер запястья:</b> {wrist_size} см
🔗 <b>Всего звеньев:</b> {links_count}
💰 <b>Итоговая сумма:</b> <b>{total_price}₽</b>
🚚 <b>Доставка СДЭК:</b> {delivery_price}₽

📋 <b>СОСТАВ БРАСЛЕТА:</b>
"""
        
        for team, count in sorted(team_counts.items()):
            message += f"\n  • {team}: {count} звеньев"
        
        message += f"\n\n✅ Статус: <b>НОВЫЙ</b>"
        message += f"\n⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        admin_url = os.getenv('ADMIN_URL', 'http://127.0.0.1:8080/admin')
        message += f"\n\n<a href='{admin_url}'>📊 ПЕРЕЙТИ В АДМИНКУ</a>"

        if BOT_TOKEN and ADMIN_ID:
            send_to_telegram(BOT_TOKEN, ADMIN_ID, message)

        # Подтверждение пользователю
        if BOT_TOKEN and user_tg_id:
            composition_text = ", ".join(f"{t}: {c} шт." for t, c in sorted(team_counts.items()))
            user_message = (
                f"✅ <b>Заказ #{order_counter} принят!</b>\n\n"
                f"🔗 Звеньев: {links_count}\n"
                f"📋 Состав: {composition_text}\n"
                f"💰 Сумма: <b>{total_price}₽</b>\n\n"
                f"Мы свяжемся с вами в ближайшее время. Спасибо! 🏁"
            )
            send_to_telegram(BOT_TOKEN, user_tg_id, user_message)

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
    
    STATUS_MESSAGES = {
        'в работе':  '🔧 Ваш заказ #{id} взят в работу! Скоро начнём собирать 🏁',
        'отправлен': '🚚 Заказ #{id} отправлен! Ждите доставки.',
        'готов':     '✅ Заказ #{id} готов! Свяжемся с вами для передачи.',
        'отменён':   '❌ Заказ #{id} отменён. Если это ошибка — напишите нам.',
    }

    for order in orders_storage:
        if order['id'] == order_id:
            order['status'] = new_status
            save_orders_storage()
            print(f"✅ Заказ #{order_id} статус изменен на: {new_status}")

            tg_id = order.get('userTgId')
            if BOT_TOKEN and tg_id and new_status in STATUS_MESSAGES:
                notify_text = STATUS_MESSAGES[new_status].format(id=order_id)
                send_to_telegram(BOT_TOKEN, tg_id, notify_text)

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

def validate_init_data(init_data: str, bot_token: str) -> bool:
    """Проверяет подпись initData от Telegram WebApp."""
    if not init_data or not bot_token:
        return False
    try:
        pairs = {}
        for part in unquote(init_data).split('&'):
            if '=' in part:
                k, v = part.split('=', 1)
                pairs[k] = v

        received_hash = pairs.pop('hash', None)
        if not received_hash:
            return False

        data_check_string = '\n'.join(
            f"{k}={v}" for k, v in sorted(pairs.items())
        )

        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode('utf-8'),
            hashlib.sha256
        ).digest()

        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_hash, received_hash)
    except Exception as e:
        print(f"⚠️ Ошибка валидации initData: {e}")
        return False

CDEK_CLIENT_ID     = os.getenv('CDEK_CLIENT_ID', '')
CDEK_CLIENT_SECRET = os.getenv('CDEK_CLIENT_SECRET', '')
CDEK_FROM_CITY     = os.getenv('CDEK_FROM_CITY_CODE', '')   # код города отправки
CDEK_WEIGHT_G      = int(os.getenv('CDEK_WEIGHT_G', '150')) # вес посылки в граммах
CDEK_API           = 'https://api.cdek.ru/v2'

# Тарифы: code → (название, тип)
CDEK_TARIFFS = {
    136: ('Посылка склад–склад', 'склад'),
    137: ('Посылка склад–дверь', 'дверь'),
    138: ('Посылка дверь–склад', 'склад'),
    139: ('Посылка дверь–дверь', 'дверь'),
    366: ('Эконом посылка',      'склад'),
}

_cdek_token = None
_cdek_token_expires = 0


def cdek_get_token():
    """Получить/обновить токен СДЭК (кэш на час)."""
    import time
    global _cdek_token, _cdek_token_expires
    if _cdek_token and time.time() < _cdek_token_expires - 60:
        return _cdek_token
    resp = requests.post(
        f'{CDEK_API}/oauth/token',
        data={'grant_type': 'client_credentials',
              'client_id': CDEK_CLIENT_ID,
              'client_secret': CDEK_CLIENT_SECRET},
        timeout=10
    )
    resp.raise_for_status()
    data = resp.json()
    _cdek_token = data['access_token']
    _cdek_token_expires = time.time() + data.get('expires_in', 3600)
    return _cdek_token


def cdek_city_code(city_name: str):
    """Найти код города СДЭК по названию."""
    token = cdek_get_token()
    resp = requests.get(
        f'{CDEK_API}/location/cities',
        params={'city': city_name, 'size': 1},
        headers={'Authorization': f'Bearer {token}'},
        timeout=10
    )
    resp.raise_for_status()
    cities = resp.json()
    return cities[0].get('code') if cities else None


def cdek_calculate(to_city_code: int, order_price: int) -> list:
    """Рассчитать все тарифы и вернуть отсортированный список."""
    token = cdek_get_token()
    results = []
    for tariff_code, (name, delivery_type) in CDEK_TARIFFS.items():
        try:
            resp = requests.post(
                f'{CDEK_API}/calculator/tariff',
                json={
                    'tariff_code':   tariff_code,
                    'from_location': {'code': int(CDEK_FROM_CITY)},
                    'to_location':   {'code': to_city_code},
                    'packages':      [{'weight': CDEK_WEIGHT_G,
                                       'length': 15, 'width': 10, 'height': 5}],
                    'services':      [{'code': 'INSURANCE',
                                       'parameter': str(order_price)}],
                },
                headers={'Authorization': f'Bearer {token}'},
                timeout=10
            )
            if resp.status_code == 200:
                d = resp.json()
                if not d.get('errors'):
                    results.append({
                        'tariff_code':   tariff_code,
                        'name':          name,
                        'delivery_type': delivery_type,
                        'price':         int(d.get('delivery_sum', 0)),
                        'period_min':    d.get('period_min', '?'),
                        'period_max':    d.get('period_max', '?'),
                    })
        except Exception as e:
            print(f'⚠️ СДЭК тариф {tariff_code}: {e}')
    results.sort(key=lambda x: x['price'])
    return results


@app.route('/api/delivery/calculate', methods=['POST'])
def calculate_delivery():
    """Рассчитать стоимость доставки СДЭК."""
    if not CDEK_CLIENT_ID or not CDEK_CLIENT_SECRET or not CDEK_FROM_CITY:
        return jsonify({'success': False, 'message': 'СДЭК не настроен на сервере'}), 503

    data = request.json
    city_name   = (data.get('city') or '').strip()
    order_price = int(data.get('orderPrice', 0))

    if not city_name:
        return jsonify({'success': False, 'message': 'Укажите город'}), 400

    try:
        city_code = cdek_city_code(city_name)
        if not city_code:
            return jsonify({'success': False,
                            'message': f'Город «{city_name}» не найден в базе СДЭК'}), 404
        tariffs = cdek_calculate(city_code, order_price)
        if not tariffs:
            return jsonify({'success': False,
                            'message': 'Не удалось рассчитать доставку в этот город'}), 404
        return jsonify({'success': True, 'tariffs': tariffs, 'city': city_name})
    except Exception as e:
        print(f'❌ СДЭК ошибка: {e}')
        return jsonify({'success': False, 'message': 'Ошибка расчёта доставки'}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, port=port, host='0.0.0.0')