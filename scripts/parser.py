"""
Парсер DNS для обновления каталога комплектующих.
Запускается через GitHub Actions раз в день.
"""

import json
import re
import time
import urllib.request
import urllib.error
from bs4 import BeautifulSoup
from pathlib import Path

# URL категорий DNS (актуальные на 2026)
DNS_CATEGORIES = {
    "cpu": "https://www.dns-shop.ru/catalog/17a899cd16404e77/processory/",
    "motherboard": "https://www.dns-shop.ru/catalog/17a89a2f16404e77/materinskie-platy/",
    "ram": "https://www.dns-shop.ru/catalog/17a89aab16404e77/operativnaya-pamyat/",
    "gpu": "https://www.dns-shop.ru/catalog/17a89cec16404e77/videokarty/",
    "psu": "https://www.dns-shop.ru/catalog/17a8a04316404e77/bloki-pitaniya/",
    "case": "https://www.dns-shop.ru/catalog/17a89c5616404e77/korpusa/",
    "cooler": "https://www.dns-shop.ru/catalog/17a89cd216404e77/sistemy-ohlazhdeniya/",
    "storage": "https://www.dns-shop.ru/catalog/17a89c3916404e77/zhestkie-diski-i-ssd/",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

def fetch_page(url: str) -> str:
    """Скачивает страницу с обработкой ошибок."""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code} for {url}")
        return ""
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

def parse_price(price_text: str) -> int:
    """Извлекает цену из текста."""
    digits = re.sub(r'\D', '', price_text)
    return int(digits) if digits else 0

def parse_cpu(html: str) -> list:
    """Парсит процессоры."""
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    
    for card in soup.select('.catalog-product.ui-button'):
        try:
            title = card.select_one('.catalog-product__name')
            price = card.select_one('.price__current-value')
            if not title or not price:
                continue
            
            name = title.get_text(strip=True)
            price_val = parse_price(price.get_text())
            
            # Определяем сокет из названия
            socket = None
            if 'LGA1700' in name or '1700' in name:
                socket = 'LGA1700'
            elif 'AM5' in name:
                socket = 'AM5'
            elif 'AM4' in name:
                socket = 'AM4'
            
            # Определяем TDP (примерно)
            tdp = 65
            if 'i9' in name or 'Ryzen 9' in name:
                tdp = 170
            elif 'i7' in name or 'Ryzen 7' in name:
                tdp = 105
            elif 'i5' in name or 'Ryzen 5' in name:
                tdp = 89
            
            items.append({
                "name": name,
                "socket": socket,
                "tdp": tdp,
                "price": price_val
            })
        except Exception as e:
            continue
    
    return items

def parse_gpu(html: str) -> list:
    """Парсит видеокарты."""
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    
    for card in soup.select('.catalog-product.ui-button'):
        try:
            title = card.select_one('.catalog-product__name')
            price = card.select_one('.price__current-value')
            if not title or not price:
                continue
            
            name = title.get_text(strip=True)
            price_val = parse_price(price.get_text())
            
            # Определяем длину (примерно по серии)
            length = 250
            if '4090' in name or '5090' in name:
                length = 358
            elif '4080' in name or '5080' in name:
                length = 336
            elif '4070' in name or '5070' in name:
                length = 300
            
            # TDP
            tdp = 150
            if '4090' in name or '5090' in name:
                tdp = 450
            elif '4080' in name or '5080' in name:
                tdp = 320
            elif '4070' in name or '5070' in name:
                tdp = 220
            
            items.append({
                "name": name,
                "length": length,
                "tdp": tdp,
                "price": price_val
            })
        except Exception as e:
            continue
    
    return items

def parse_generic(html: str, category: str) -> list:
    """Универсальный парсер для остальных категорий."""
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    
    for card in soup.select('.catalog-product.ui-button'):
        try:
            title = card.select_one('.catalog-product__name')
            price = card.select_one('.price__current-value')
            if not title or not price:
                continue
            
            name = title.get_text(strip=True)
            price_val = parse_price(price.get_text())
            
            item = {"name": name, "price": price_val}
            
            # Добавляем специфичные поля по категории
            if category == "motherboard":
                socket = None
                ram_type = "DDR4"
                if 'AM5' in name:
                    socket = 'AM5'
                    ram_type = 'DDR5'
                elif 'LGA1700' in name:
                    socket = 'LGA1700'
                elif 'AM4' in name:
                    socket = 'AM4'
                
                form = 'ATX'
                if 'mATX' in name or 'MATX' in name:
                    form = 'mATX'
                elif 'ITX' in name:
                    form = 'ITX'
                
                item.update({"socket": socket, "ram_type": ram_type, "form": form})
            
            elif category == "ram":
                ram_type = "DDR4"
                capacity = 16
                if 'DDR5' in name:
                    ram_type = 'DDR5'
                if '32GB' in name or '32 Гб' in name:
                    capacity = 32
                elif '64GB' in name or '64 Гб' in name:
                    capacity = 64
                
                item.update({"type": ram_type, "capacity": capacity})
            
            elif category == "psu":
                wattage = 500
                match = re.search(r'(\d{3,4})\s*[Ww]', name)
                if match:
                    wattage = int(match.group(1))
                item["wattage"] = wattage
            
            elif category == "case":
                max_gpu = 300
                max_cooler = 160
                match_gpu = re.search(r'(\d{3})\s*мм', name)
                if match_gpu:
                    max_gpu = int(match_gpu.group(1))
                item.update({"max_gpu": max_gpu, "max_cooler": max_cooler})
            
            elif category == "cooler":
                height = 150
                sockets = ["LGA1700", "AM4", "AM5"]
                match_h = re.search(r'(\d{3})\s*мм', name)
                if match_h:
                    height = int(match_h.group(1))
                item.update({"height": height, "sockets": sockets})
            
            items.append(item)
        except Exception as e:
            continue
    
    return items

def update_catalog():
    """Главная функция обновления каталога."""
    catalog_path = Path("data/catalog.json")
    
    # Загружаем существующий каталог
    if catalog_path.exists():
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
    else:
        catalog = {}
    
    # Парсим каждую категорию
    for category, url in DNS_CATEGORIES.items():
        print(f"Парсинг {category}...")
        html = fetch_page(url)
        
        if not html:
            print(f"  ⚠ Не удалось получить {url}")
            continue
        
        # Выбираем парсер
        if category == "cpu":
            items = parse_cpu(html)
        elif category == "gpu":
            items = parse_gpu(html)
        else:
            items = parse_generic(html, category)
        
        print(f"  Найдено {len(items)} товаров")
        
        # Обновляем каталог (добавляем новые, обновляем цены существующих)
        if category not in catalog:
            catalog[category] = []
        
        for item in items:
            # Ищем существующий товар по названию
            existing = next((x for x in catalog[category] if x.get('name') == item['name']), None)
            
            if existing:
                # Обновляем цену
                existing['price'] = item['price']
            else:
                # Добавляем новый товар с ID
                item_id = f"{category[:3]}{len(catalog[category]) + 1:02d}"
                item['id'] = item_id
                catalog[category].append(item)
        
        # Пауза между запросами
        time.sleep(2)
    
    # Сохраняем обновлённый каталог
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Каталог обновлён: {catalog_path}")

if __name__ == "__main__":
    update_catalog()