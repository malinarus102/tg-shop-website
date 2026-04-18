import os
from src.models.product import Product, BraceletLink

DRIVERS = {
    "max": {"name": "Max Verstappen", "number": 1, "team": "Red Bull"},
    "lando": {"name": "Lando Norris", "number": 4, "team": "McLaren"},
    "oscar": {"name": "Oscar Piastri", "number": 81, "team": "McLaren"},
    "charles": {"name": "Charles Leclerc", "number": 16, "team": "Ferrari"},
    "carlos": {"name": "Carlos Sainz", "number": 55, "team": "Ferrari"},
    "lewis": {"name": "Lewis Hamilton", "number": 44, "team": "Mercedes"},
    "george": {"name": "George Russell", "number": 63, "team": "Mercedes"},
    "fernando": {"name": "Fernando Alonso", "number": 14, "team": "Aston Martin"},
    "lance": {"name": "Lance Stroll", "number": 18, "team": "Aston Martin"},
    "yuki": {"name": "Yuki Tsunoda", "number": 22, "team": "AlphaTauri"},
    "nico": {"name": "Nico Hulkenberg", "number": 27, "team": "Haas"},
}

PRODUCTS = [
    Product("1", "Браслет Max Verstappen #1", 2500, "Браслеты", description="Официальный браслет Red Bull Racing"),
    Product("2", "Браслет Charles Leclerc #16", 2500, "Браслеты", description="Официальный браслет Ferrari"),
    Product("3", "Браслет Lewis Hamilton #44", 2500, "Браслеты", description="Официальный браслет Mercedes"),
    Product("4", "Браслет Lando Norris #4", 2500, "Браслеты", description="Официальный браслет McLaren"),
]

BRACELET_LINKS = [
    BraceletLink("max", "Max Verstappen", "max", "src/pics/redbull/max.jpg", price=500),
    BraceletLink("charles", "Charles Leclerc", "charles", "src/pics/ferrari/charles.jpg", price=500),
    BraceletLink("lewis", "Lewis Hamilton", "lewis", "src/pics/mercedes/lewis.jpg", price=500),
    BraceletLink("lando", "Lando Norris", "lando", "src/pics/mclaren/lando.jpg", price=500),
    BraceletLink("oscar", "Oscar Piastri", "oscar", "src/pics/mclaren/oscar.jpg", price=500),
    BraceletLink("carlos", "Carlos Sainz", "carlos", "src/pics/williams/carlos.jpg", price=500),
    BraceletLink("george", "George Russell", "george", "src/pics/mercedes/george.jpg", price=500),
    BraceletLink("fernando", "Fernando Alonso", "fernando", "src/pics/astonmartin/fernando.jpg", price=500),
    BraceletLink("lance", "Lance Stroll", "lance", "src/pics/astonmartin/lance.jpg", price=500),
    BraceletLink("yuki", "Yuki Tsunoda", "yuki", "src/pics/redbull/yuki.jpg", price=500),
    BraceletLink("nico", "Nico Hulkenberg", "nico", "src/pics/haas/nico.jpg", price=500),
]

def get_all_products():
    return PRODUCTS

def get_products_by_category(category: str):
    return [p for p in PRODUCTS if p.category == category]

def get_categories():
    return list(set(p.category for p in PRODUCTS))

def get_product_by_id(product_id: str):
    for p in PRODUCTS:
        if p.product_id == product_id:
            return p
    return None

def get_all_links():
    """Получить все звенья браслета"""
    return BRACELET_LINKS

def get_link_by_id(link_id: str):
    """Получить звено по ID"""
    for link in BRACELET_LINKS:
        if link.link_id == link_id:
            return link
    return None

def get_driver_info(driver_key: str):
    """Получить информацию о пилоте"""
    return DRIVERS.get(driver_key)

def can_add_duplicate_links():
    """Можно ли добавлять дубликаты звеньев?"""
    return True

class Shop:
    def __init__(self):
        self.products = []

    def add_product(self, product: Product):
        self.products.append(product)

    def get_product_list(self):
        return self.products

    def get_product_details(self, product_id):
        for product in self.products:
            if product.id == product_id:
                return product
        return None

    def remove_product(self, product_id):
        self.products = [product for product in self.products if product.id != product_id]

PICS_BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "pics")


def _load_team_designs(team_folder: str, prefix: str):
    """Автоматически загрузить все дизайны команды из src/pics/<team_folder>."""
    folder_path = os.path.join(PICS_BASE_DIR, team_folder)
    if not os.path.isdir(folder_path):
        return []

    image_files = []
    for filename in os.listdir(folder_path):
        lower_name = filename.lower()
        if lower_name.endswith((".jpg", ".jpeg", ".png", ".webp")):
            image_files.append(filename)

    def sort_key(name: str):
        stem = os.path.splitext(name)[0]
        return (0, int(stem)) if stem.isdigit() else (1, stem)

    image_files.sort(key=sort_key)
    return [
        {
            "id": f"{prefix}{index}",
            "name": f"Дизайн {index}",
            "image": f"{team_folder}/{filename}",
        }
        for index, filename in enumerate(image_files, start=1)
    ]


TEAMS = {
    "ferrari": {
        "name": "Scuderia Ferrari",
        "color": "#DC0000",
        "textColor": "#FFFFFF",
        "drivers": ["Charles Leclerc", "Lewis Hamilton"],
        "designs": _load_team_designs("ferrari", "f"),
    },
    "mercedes": {
        "name": "Mercedes",
        "color": "#00D2BE",
        "textColor": "#111111",
        "drivers": ["George Russell", "Kimi Antonelli"],
        "designs": _load_team_designs("mercedes", "m"),
    },
    "williams": {
        "name": "Williams",
        "color": "#005AFF",
        "textColor": "#FFFFFF",
        "drivers": ["Alex Albon", "Carlos Sainz"],
        "designs": _load_team_designs("williams", "w"),
    },
}

PRICE_BASE = 700
PRICE_EXTRA = 40

def calculate_price(links_count):
    """Рассчитать цену браслета"""
    if links_count <= 20:
        return PRICE_BASE
    else:
        extra_links = links_count - 20
        return PRICE_BASE + (extra_links * PRICE_EXTRA)

def get_all_teams():
    """Получить все команды"""
    return TEAMS

def get_team_by_id(team_id: str):
    """Получить команду по ID"""
    return TEAMS.get(team_id)

def get_team_designs(team_id: str):
    """Получить все дизайны команды"""
    team = TEAMS.get(team_id)
    if team:
        return team["designs"]
    return []

def get_design_by_id(team_id: str, design_id: str):
    """Получить дизайн по ID"""
    team = TEAMS.get(team_id)
    if team:
        for design in team["designs"]:
            if design["id"] == design_id:
                return design
    return None