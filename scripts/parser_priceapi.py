"""
Парсер PricesAPI для получения цен на комплектующие.
БЫСТРАЯ ВЕРСИЯ - использует многопоточность.
"""

import json
import time
import requests
import re
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# API ключ
PRICESAPI_KEY = "pricesapi_IdIkJT9R4ekZKCVnGb8xWXUbu8pIZfq"

# Курс доллара к рублю
USD_TO_RUB = 90.0
EUR_TO_RUB = 98.0

# Актуальные поисковые запросы (Июль 2026)
SEARCH_CATEGORIES = {
    "cpu": [
        "Intel Core i3-12100F",
        "Intel Core i5-12400F",
        "Intel Core i5-12600KF",
        "Intel Core i7-12700KF",
        "Intel Core i9-12900K",
        "Intel Core i5-13400F",
        "Intel Core i5-13600KF",
        "Intel Core i7-13700KF",
        "Intel Core i9-13900K",
        "Intel Core i5-14400F",
        "Intel Core i5-14600KF",
        "Intel Core i7-14700KF",
        "Intel Core i9-14900K",
        "AMD Ryzen 5 5600",
        "AMD Ryzen 7 5700X",
        "AMD Ryzen 7 5800X3D",
        "AMD Ryzen 9 5900X",
        "AMD Ryzen 5 7600",
        "AMD Ryzen 7 7800X3D",
        "AMD Ryzen 9 7950X",
        "AMD Ryzen 5 9600X",
        "AMD Ryzen 7 9700X",
        "AMD Ryzen 9 9950X",
    ],
    "gpu": [
        "ASUS Dual RTX 4060",
        "ASUS TUF RTX 4060",
        "MSI Ventus RTX 4060",
        "Gigabyte Eagle RTX 4060",
        "Zotac Trinity RTX 4060",
        "ASUS TUF RTX 4060 Ti",
        "MSI Gaming X RTX 4060 Ti",
        "ASUS TUF RTX 4070",
        "ASUS ROG Strix RTX 4070",
        "MSI Gaming X Trio RTX 4070",
        "Gigabyte Gaming OC RTX 4070",
        "ASUS TUF RTX 4070 Super",
        "MSI Gaming X Trio RTX 4070 Super",
        "ASUS ROG Strix RTX 4070 Ti",
        "MSI Suprim X RTX 4070 Ti",
        "ASUS TUF RTX 4070 Ti Super",
        "ASUS ROG Strix RTX 4080",
        "MSI Suprim X RTX 4080",
        "Gigabyte AORUS RTX 4080",
        "ASUS ROG Strix RTX 4090",
        "MSI Suprim X RTX 4090",
        "Gigabyte AORUS RTX 4090",
        "Zotac Trinity RTX 4090",
        "ASUS Dual RTX 5060",
        "ASUS TUF RTX 5060",
        "MSI Ventus RTX 5060",
        "ASUS TUF RTX 5060 Ti",
        "ASUS TUF RTX 5070",
        "ASUS ROG Strix RTX 5070",
        "MSI Gaming X Trio RTX 5070",
        "ASUS ROG Strix RTX 5070 Ti",
        "MSI Suprim X RTX 5070 Ti",
        "ASUS ROG Strix RTX 5080",
        "MSI Suprim X RTX 5080",
        "ASUS ROG Strix RTX 5090",
        "MSI Suprim X RTX 5090",
        "ASUS Dual RX 7600",
        "ASUS TUF RX 7600",
        "MSI Mech RX 7600",
        "Sapphire Pulse RX 7600",
        "ASUS TUF RX 7700 XT",
        "MSI Gaming X RX 7700 XT",
        "Sapphire Nitro+ RX 7700 XT",
        "ASUS TUF RX 7800 XT",
        "ASUS ROG Strix RX 7800 XT",
        "MSI Gaming X Trio RX 7800 XT",
        "Sapphire Nitro+ RX 7800 XT",
        "ASUS TUF RX 7900 GRE",
        "ASUS TUF RX 7900 XT",
        "ASUS ROG Strix RX 7900 XT",
        "MSI Gaming X Trio RX 7900 XT",
        "Sapphire Nitro+ RX 7900 XT",
        "ASUS ROG Strix RX 7900 XTX",
        "MSI Gaming X Trio RX 7900 XTX",
        "Sapphire Nitro+ RX 7900 XTX",
        "ASUS TUF RX 9070",
        "ASUS ROG Strix RX 9070 XT",
        "MSI Gaming X Trio RX 9070 XT",
        "ASUS ROG Strix RX 9080",
        "ASUS Dual Arc A750",
        "Intel Arc A750 Limited Edition",
    ],
    "motherboard": [
        "MSI PRO H610M-E",
        "ASUS PRIME B660M-K",
        "Gigabyte B760M D3AX",
        "MSI MAG B760 TOMAHAWK",
        "ASUS ROG STRIX B760-F",
        "ASUS ROG STRIX Z790-E",
        "Gigabyte Z790 AORUS MASTER",
        "MSI PRO A520M-A",
        "ASUS TUF B550M-PLUS",
        "MSI MPG B550 GAMING PLUS",
        "ASRock A620M-HDV",
        "MSI PRO B650M-P",
        "ASUS TUF B650-PLUS",
        "Gigabyte B650 AORUS ELITE",
        "ASUS ROG STRIX X670E",
        "Gigabyte X670E AORUS MASTER",
    ],
    "ram": [
        "Kingston FURY Beast 16GB DDR4 3200",
        "Kingston FURY Beast 32GB DDR4 3200",
        "G.Skill Ripjaws V 32GB DDR4 3600",
        "Corsair Vengeance LPX 32GB DDR4",
        "Kingston FURY Beast 32GB DDR5 5200",
        "G.Skill Trident Z5 32GB DDR5 6000",
        "Corsair Vengeance 32GB DDR5 5600",
        "G.Skill Trident Z5 RGB 64GB DDR5 6000",
    ],
    "storage": [
        "Kingston A400 480GB SATA",
        "Kingston NV2 500GB NVMe",
        "Kingston NV2 1TB NVMe",
        "Samsung 980 1TB NVMe",
        "WD Black SN770 1TB",
        "Samsung 990 Pro 2TB",
        "WD Black SN850X 2TB",
        "Crucial T700 4TB Gen5",
    ],
    "psu": [
        "Deepcool PF550",
        "Deepcool PK650D",
        "Deepcool PM750D",
        "be quiet Pure Power 12M 850W",
        "Corsair RM750x",
        "Corsair RM850x",
        "Seasonic Focus GX 1000",
        "Corsair HX1200",
        "be quiet Dark Power 13 1300W",
        "Corsair AX1600i",
    ],
    "case": [
        "Deepcool CH370",
        "Zalman i3 Neo",
        "Cougar Duoface Pro",
        "Fractal Design Pop XL",
        "NZXT H7 Flow",
        "Lian Li O11 Dynamic EVO",
        "Corsair 5000D Airflow",
        "be quiet Dark Base Pro 901",
    ],
    "cooler": [
        "Deepcool AG400",
        "ID-Cooling SE-224-XTS",
        "Deepcool AK620",
        "Thermalright Peerless Assassin 120",
        "be quiet Dark Rock Pro 4",
        "Noctua NH-D15",
        "Arctic Liquid Freezer III 280",
        "NZXT Kraken Elite 360",
        "Corsair iCUE LINK H150i",
    ],
}


def fetch_pricesapi(search_query: str) -> list:
    """Запрашивает товары через PricesAPI."""
    url = "https://api.pricesapi.io/api/v1/products/search"
    
    params = {
        "q": search_query,
        "country": "us",
        "limit": 10,
        "offers_limit": 3
    }
    
    headers = {"Authorization": f"Bearer {PRICESAPI_KEY}"}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=95)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success") and data.get("data", {}).get("products"):
                products = data["data"]["products"]
                results = []
                
                for product in products:
                    all_prices = []
                    
                    if product.get("price") and product.get("price") > 0:
                        all_prices.append(product["price"])
                    
                    for offer in product.get("offers", []):
                        if offer.get("price") and offer.get("price") > 0:
                            all_prices.append(offer["price"])
                    
                    if all_prices:
                        min_price = min(all_prices)
                        currency = product.get("currency", "USD")
                        
                        if currency == "USD":
                            price_rub = int(min_price * USD_TO_RUB)
                        else:
                            price_rub = int(min_price * EUR_TO_RUB)
                        
                        results.append({
                            "name": product.get("name", "Unknown"),
                            "price_rub": price_rub,
                            "category": product.get("category", ""),
                        })
                
                return results
        
        return []
    
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return []


def extract_specifications(product_name: str, category: str) -> dict:
    """Извлекает характеристики из названия."""
    specs = {}
    name_upper = product_name.upper()
    
    if category == "cpu":
        if "LGA1700" in name_upper or ("INTEL" in name_upper and any(x in name_upper for x in ["12TH", "13TH", "14TH"])):
            specs["socket"] = "LGA1700"
        elif "AM5" in name_upper or ("RYZEN" in name_upper and any(x in name_upper for x in ["7000", "9000"])):
            specs["socket"] = "AM5"
        else:
            specs["socket"] = "AM4"
        
        if "I9" in name_upper or "RYZEN 9" in name_upper:
            specs["tdp"] = 170
        elif "I7" in name_upper or "RYZEN 7" in name_upper:
            specs["tdp"] = 105
        else:
            specs["tdp"] = 89
    
    elif category == "gpu":
        if "4090" in name_upper or "5090" in name_upper:
            specs["length"] = 358
            specs["tdp"] = 450
        elif "4080" in name_upper or "5080" in name_upper:
            specs["length"] = 336
            specs["tdp"] = 320
        elif "4070" in name_upper or "5070" in name_upper:
            specs["length"] = 300
            specs["tdp"] = 220
        else:
            specs["length"] = 250
            specs["tdp"] = 150
    
    elif category == "ram":
        specs["type"] = "DDR5" if "DDR5" in name_upper else "DDR4"
        capacity_match = re.search(r'(\d{1,3})\s*GB', name_upper)
        specs["capacity"] = int(capacity_match.group(1)) if capacity_match else 32
    
    elif category == "motherboard":
        if any(x in name_upper for x in ["B660", "B760", "Z790"]):
            specs["socket"] = "LGA1700"
        elif any(x in name_upper for x in ["B650", "X670"]):
            specs["socket"] = "AM5"
        else:
            specs["socket"] = "AM4"
        
        specs["ram_type"] = "DDR5" if "DDR5" in name_upper else "DDR4"
        specs["form"] = "mATX" if "MATX" in name_upper else "ATX"
    
    elif category == "psu":
        wattage_match = re.search(r'(\d{3,4})\s*W', name_upper)
        specs["wattage"] = int(wattage_match.group(1)) if wattage_match else 750
    
    elif category == "case":
        specs["max_gpu"] = 350
        specs["max_cooler"] = 170
    
    elif category == "cooler":
        specs["height"] = 60 if "LIQUID" in name_upper else 160
        specs["sockets"] = ["LGA1700", "AM4", "AM5"]
    
    return specs


def process_query(category: str, query: str, existing_names: set) -> list:
    """Обрабатывает один поисковый запрос."""
    print(f"  🔍 {query}...")
    products = fetch_pricesapi(query)
    
    new_items = []
    for product in products:
        name = product["name"]
        
        if name.lower() in existing_names:
            continue
        
        specs = extract_specifications(name, category)
        item_id = f"{category[:3]}{len(new_items) + 1:02d}"
        
        new_item = {
            "id": item_id,
            "name": name,
            "price": product["price_rub"],
            "source": "PricesAPI",
            "last_updated": datetime.now().isoformat(),
            **specs
        }
        
        new_items.append(new_item)
        existing_names.add(name.lower())
        print(f"    ➕ {name}: {product['price_rub']} ₽")
    
    return new_items


def update_catalog_with_api():
    """Быстрое обновление каталога с многопоточностью."""
    catalog_path = Path(__file__).parent.parent / "data" / "catalog.json"
    
    print(f"📁 Путь: {catalog_path}")
    
    if catalog_path.exists():
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        print("✅ Загружен каталог")
    else:
        catalog = {}
    
    total_new = 0
    start_time = time.time()
    
    # Обрабатываем категории параллельно
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        
        for category, queries in SEARCH_CATEGORIES.items():
            if category not in catalog:
                catalog[category] = []
            
            existing_names = {item.get("name", "").lower() for item in catalog[category]}
            
            print(f"\n📦 {category.upper()}")
            
            # Отправляем все запросы категории параллельно
            for query in queries:
                future = executor.submit(process_query, category, query, existing_names)
                futures[future] = (category, query)
        
        # Собираем результаты
        for future in as_completed(futures):
            category, query = futures[future]
            try:
                new_items = future.result()
                catalog[category].extend(new_items)
                total_new += len(new_items)
            except Exception as e:
                print(f"  ✗ Ошибка: {e}")
    
    # Сохраняем
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"✅ ГОТОВО!")
    print(f"📊 Добавлено: {total_new} товаров")
    print(f"⏱️  Время: {elapsed:.1f} секунд ({elapsed/60:.1f} минут)")
    print(f"{'='*60}")


if __name__ == "__main__":
    if PRICESAPI_KEY == "YOUR_PRICESAPI_KEY_HERE":
        print("❌ Вставьте API ключ!")
        exit(1)
    
    print("🚀 Быстрый парсер PricesAPI")
    update_catalog_with_api()