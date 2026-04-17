from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Product:
    product_id: str
    name: str
    price: float
    category: str
    image_url: Optional[str] = None
    description: Optional[str] = None

@dataclass
class BraceletLink:
    """Звено для браслета"""
    link_id: str
    name: str
    driver: str  # Пилот
    image_path: str
    price: float = 500

@dataclass
class CustomBracelet:
    """Кастомный браслет пользователя"""
    user_id: int
    wrist_size: int  # Размер запястья в см
    links: List[BraceletLink]  # Выбранные звенья
    
    def required_links_count(self):
        """Необходимое количество звеньев"""
        return self.wrist_size + 1
    
    def current_links_count(self):
        """Текущее количество звеньев"""
        return len(self.links)
    
    def links_remaining(self):
        """Осталось звеньев до нужного количества"""
        return self.required_links_count() - self.current_links_count()
    
    def is_complete(self):
        """Браслет завершён?"""
        return self.current_links_count() == self.required_links_count()
    
    def total_price(self):
        """Общая стоимость браслета"""
        return sum(link.price for link in self.links)