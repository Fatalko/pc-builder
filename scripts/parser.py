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

# Более реалистичные заголовки
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.5,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}

def fetch_page(url: str) -> str:
    """Скачивает страницу с обработкой ошибок и задержками."""
    print(f"  Запрос: {url}")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as response:
                html = response.read().decode('utf-8')
                print(f"  ✅ Успешно получено")
                return html
        except urllib.error.HTTPError as e:
            print(f"  ⚠ HTTP Error {e.code} (попытка {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(5)  # Ждём перед повторной попыткой
        except Exception as e:
            print(f"  ⚠ Error: {e} (попытка {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(3)
    
    print(f"  ❌ Не удалось получить страницу после {max_retries} попыток")
    return ""

def parse_price(price_text: str) -> int:
    """Извлекает цену из текста."""
    if not price_text:
        return 0
    digits = re.sub(r'\D', '', price_text)
    return int(digits) if digits else 0

def parse_cpu(html: str) -> list:
    """Парсит процессоры."""
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    
    # Пробуем разные селекторы (DNS меняет структуру)
    for card in soup.select('.catalog-product.ui-button, .product-card, [data-product]'):
        try:
            title = card.select_one('.catalog-product__name, .product-card__title, .product-title')
            price = card.select_one('.price__current-value, .price__current, .product-card__price')
            
            if not title or not price:
                continue
            
            name = title.get_text(strip=True)
            price_val = parse_price(price.get_text())
            
            if price_val == 0:
                continue
            
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
    
    print(f"  Найдено процессоров: {len(items)}")
    return items

def parse_gpu(html: str) -> list:
    """Парсит видеокарты."""
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    
    for card in soup.select('.catalog-product.ui-button, .product-card, [data-product]'):
        try:
            title = card.select_one('.catalog-product__name, .product-card__title, .product-title')
            price = card.select_one('.price__current-value, .price__current, .product-card__price')
            
            if not title or not price:
                continue
            
            name = title.get_text(strip=True)
            price_val = parse_price(price.get_text())
            
            if price_val == 0:
                continue
            
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
    
    print(f"  Найдено видеокарт: {len(items)}")
    return items

def parse_generic(html: str, category: str) -> list:
    """Универсальный парсер для остальных категорий."""
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    
    for card in soup.select('.catalog-product.ui-button, .product-card, [data-product]'):
        try:
            title = card.select_one('.catalog-product__name, .product-card__title, .product-title')
            price = card.select_one('.price__current-value, .price__current, .product-card__price')
            
            if not title or not price:
                continue
            
            name = title.get_text(strip=True)
            price_val = parse_price(price.get_text())
            
            if price_val == 0:
                continue
            
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
    
    print(f"  Найдено {category}: {len(items)}")
    return items

def update_catalog():
    """Главная функция обновления каталога."""
    # Правильный путь к файлу (от корня репозитория)
    catalog_path = Path(__file__).parent.parent / "data" / "catalog.json"
    
    print(f"Путь к каталогу: {catalog_path}")
    print(f"Каталог существует: {catalog_path.exists()}")
    
    # Загружаем существующий каталог
    if catalog_path.exists():
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        print(f"✅ Загружен существующий каталог")
    else:
        catalog = {}
        print("⚠ Создаём новый каталог")
    
    # Парсим каждую категорию
    total_items = 0
    for category, url in DNS_CATEGORIES.items():
        print(f"\nПарсинг {category}...")
        html = fetch_page(url)
        
        if not html:
            print(f"  ⚠ Не удалось получить {url}, пропускаем")
            continue
        
        # Выбираем парсер
        if category == "cpu":
            items = parse_cpu(html)
        elif category == "gpu":
            items = parse_gpu(html)
        else:
            items = parse_generic(html, category)
        
        if not items:
            print(f"  ⚠ Не найдено товаров в {category}")
            continue
        
        total_items += len(items)
        
        # Обновляем каталог
        if category not in catalog:
            catalog[category] = []
        
        # Добавляем только новые товары (не перезаписываем существующие)
        existing_names = {item.get('name') for item in catalog[category]}
        new_items = 0
        
        for item in items:
            if item['name'] not in existing_names:
                # Добавляем новый товар с ID
                item_id = f"{category[:3]}{len(catalog[category]) + 1:02d}"
                item['id'] = item_id
                catalog[category].append(item)
                new_items += 1
        
        print(f"  Добавлено новых: {new_items}")
        
        # Пауза между запросами (чтобы не блокировали)
        print(f"  Пауза 3 секунды...")
        time.sleep(3)
    
    # Сохраняем обновлённый каталог
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Каталог обновлён!")
    print(f"📊 Всего товаров: {total_items}")
    print(f"💾 Сохранено в: {catalog_path}")

if __name__ == "__main__":
    update_catalog()