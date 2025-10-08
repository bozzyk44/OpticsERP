#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate deterministic test datasets for OpticsERP

Author: AI Bootstrap
Date: 2025-10-08
Purpose: Create reproducible test data for POC, UAT, and load tests

Usage:
    # Generate 10k product catalog with 3% errors
    python generate_test_data.py --catalog 10000 --output catalog.xlsx

    # Generate supplier price list
    python generate_test_data.py --supplier OptMarket --output supplier_a.csv

    # Generate test prescriptions
    python generate_test_data.py --prescriptions 1000 --output prescriptions.json

    # Generate all test data with seed for reproducibility
    python generate_test_data.py --all --seed 42 --output-dir ./test_data
"""

import argparse
import random
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import sys

# Try importing optional dependencies
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("⚠️  pandas not installed, XLSX/CSV export disabled", file=sys.stderr)

try:
    from faker import Faker
    HAS_FAKER = True
except ImportError:
    HAS_FAKER = False
    print("⚠️  faker not installed, using simple generators", file=sys.stderr)


class TestDataGenerator:
    """Generate deterministic test data for OpticsERP"""

    def __init__(self, seed=42, locale='ru_RU'):
        """
        Initialize generator with seed for reproducibility

        Args:
            seed: Random seed
            locale: Faker locale
        """
        self.seed = seed
        random.seed(seed)

        if HAS_FAKER:
            self.faker = Faker(locale)
            self.faker.seed_instance(seed)
        else:
            self.faker = None

        self.error_log = []

    def generate_catalog(
        self,
        size=10000,
        error_rate=0.03,
        categories=None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Generate product catalog with controlled errors

        Args:
            size: Number of products
            error_rate: Percentage of intentional errors (0-1)
            categories: List of product categories

        Returns:
            Tuple of (catalog_data, error_log)
        """
        if categories is None:
            categories = [
                'Оправы',
                'Линзы',
                'Солнцезащитные очки',
                'Контактные линзы',
                'Аксессуары',
                'Средства ухода'
            ]

        catalog = []
        errors = []
        error_count = int(size * error_rate)

        # Generate base products
        for i in range(size):
            product_id = f"PROD-{i+1:05d}"
            ean = self._generate_ean13()
            category = random.choice(categories)

            # Base product data
            product = {
                'sku': product_id,
                'ean': ean,
                'name': self._generate_product_name(category),
                'category': category,
                'price': round(random.uniform(500, 15000), 2),
                'cost': round(random.uniform(200, 7000), 2),
                'stock_qty': random.randint(0, 100),
                'supplier': self._generate_supplier_name(),
                'brand': self._generate_brand_name(),
                'active': True,
            }

            # Inject errors
            if i < error_count:
                error_type, error_product = self._inject_catalog_error(product, i)
                product = error_product
                errors.append({
                    'row': i + 2,  # +2 for header row and 1-based indexing
                    'sku': product_id,
                    'error_type': error_type,
                    'error_detail': self._get_error_detail(error_type, product)
                })

            catalog.append(product)

        self.error_log = errors
        return catalog, errors

    def generate_supplier_pricelist(
        self,
        supplier_name='OptMarket',
        size=5000,
        format='csv'
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Generate supplier price list with specific format

        Args:
            supplier_name: Supplier name (OptMarket, LensMaster, etc.)
            size: Number of items
            format: Output format (csv, xlsx)

        Returns:
            Tuple of (pricelist_data, format)
        """
        # Different suppliers have different column mappings
        supplier_mappings = {
            'OptMarket': ['Артикул', 'Наименование', 'Цена', 'Остаток'],
            'LensMaster': ['Code', 'Product', 'Price', 'Qty', 'Supplier Code'],
            'GlassWorld': ['SKU', 'Name', 'Category', 'Net Price', 'Stock']
        }

        columns = supplier_mappings.get(supplier_name, supplier_mappings['OptMarket'])
        pricelist = []

        for i in range(size):
            item = {}

            # Map to supplier columns
            if 'Артикул' in columns:
                item['Артикул'] = f"SUP-{i+1:05d}"
                item['Наименование'] = self._generate_product_name('Линзы')
                item['Цена'] = round(random.uniform(1000, 8000), 2)
                item['Остаток'] = random.randint(0, 50)
            elif 'Code' in columns:
                item['Code'] = f"LM-{i+1:05d}"
                item['Product'] = self._generate_product_name('Оправы')
                item['Price'] = round(random.uniform(2000, 12000), 2)
                item['Qty'] = random.randint(0, 30)
                item['Supplier Code'] = f"SUPP-{random.randint(1000,9999)}"
            else:  # GlassWorld
                item['SKU'] = f"GW-{i+1:05d}"
                item['Name'] = self._generate_product_name('Солнцезащитные очки')
                item['Category'] = random.choice(['Premium', 'Standard', 'Economy'])
                item['Net Price'] = round(random.uniform(3000, 20000), 2)
                item['Stock'] = random.randint(0, 25)

            pricelist.append(item)

        return pricelist, format

    def generate_prescriptions(
        self,
        count=1000
    ) -> List[Dict[str, Any]]:
        """
        Generate optical prescriptions with valid values

        Args:
            count: Number of prescriptions

        Returns:
            List of prescription dictionaries
        """
        prescriptions = []

        for i in range(count):
            # Generate realistic prescription values
            prescription = {
                'id': f"RX-{i+1:06d}",
                'patient_name': self._generate_patient_name(),
                'date': (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat(),

                # Right eye (OD)
                'od_sph': round(random.uniform(-10, +6), 0.25),
                'od_cyl': round(random.uniform(-4, 0), 0.25) if random.random() > 0.3 else 0,
                'od_axis': random.randint(1, 180) if random.random() > 0.3 else None,
                'od_add': round(random.uniform(0.75, 3.0), 0.25) if random.random() > 0.6 else None,

                # Left eye (OS)
                'os_sph': round(random.uniform(-10, +6), 0.25),
                'os_cyl': round(random.uniform(-4, 0), 0.25) if random.random() > 0.3 else 0,
                'os_axis': random.randint(1, 180) if random.random() > 0.3 else None,
                'os_add': round(random.uniform(0.75, 3.0), 0.25) if random.random() > 0.6 else None,

                # Pupillary distance
                'pd': round(random.uniform(56, 72), 1),

                # Notes
                'notes': self._generate_prescription_notes() if random.random() > 0.7 else None,
            }

            prescriptions.append(prescription)

        return prescriptions

    def generate_receipts(
        self,
        count=50,
        pos_id='POS-001'
    ) -> List[Dict[str, Any]]:
        """
        Generate fiscal receipts for testing

        Args:
            count: Number of receipts
            pos_id: POS terminal ID

        Returns:
            List of receipt dictionaries
        """
        receipts = []

        for i in range(count):
            items_count = random.randint(1, 5)
            items = []
            total = 0

            for j in range(items_count):
                price = round(random.uniform(500, 10000), 2)
                qty = random.randint(1, 3)
                amount = round(price * qty, 2)
                total += amount

                items.append({
                    'product_id': f"PROD-{random.randint(1, 1000):05d}",
                    'name': self._generate_product_name(random.choice(['Оправы', 'Линзы'])),
                    'qty': qty,
                    'price': price,
                    'amount': amount,
                })

            receipt = {
                'id': f"RECEIPT-{i+1:06d}",
                'pos_id': pos_id,
                'type': random.choice(['sale'] * 9 + ['refund']),  # 90% sales, 10% refunds
                'timestamp': (datetime.now() - timedelta(hours=random.randint(0, 72))).isoformat(),
                'items': items,
                'total': round(total, 2),
                'payments': [
                    {
                        'method': random.choice(['card', 'cash', 'card', 'card']),  # 75% card
                        'amount': round(total, 2)
                    }
                ],
            }

            receipts.append(receipt)

        return receipts

    # Helper methods

    def _generate_ean13(self) -> str:
        """Generate valid EAN-13 barcode"""
        code = ''.join([str(random.randint(0, 9)) for _ in range(12)])
        # Calculate check digit
        odd_sum = sum(int(code[i]) for i in range(0, 12, 2))
        even_sum = sum(int(code[i]) for i in range(1, 12, 2))
        total = odd_sum + even_sum * 3
        check_digit = (10 - (total % 10)) % 10
        return code + str(check_digit)

    def _generate_product_name(self, category: str) -> str:
        """Generate realistic product name"""
        if self.faker:
            return f"{category} {self.faker.company()} {self.faker.color_name()}"

        # Fallback without faker
        brands = ['Premium', 'Classic', 'Modern', 'Elite', 'Standard']
        colors = ['Black', 'Brown', 'Blue', 'Red', 'Gray']
        return f"{category} {random.choice(brands)} {random.choice(colors)}"

    def _generate_supplier_name(self) -> str:
        """Generate supplier name"""
        suppliers = ['OptMarket', 'LensMaster', 'GlassWorld', 'VisionPlus', 'OpticsPro']
        return random.choice(suppliers)

    def _generate_brand_name(self) -> str:
        """Generate brand name"""
        brands = ['RayBan', 'Oakley', 'Prada', 'Gucci', 'Tom Ford', 'Persol', 'Versace']
        return random.choice(brands)

    def _generate_patient_name(self) -> str:
        """Generate patient name"""
        if self.faker:
            return self.faker.name()

        # Fallback
        first_names = ['Иван', 'Петр', 'Мария', 'Елена', 'Алексей']
        last_names = ['Иванов', 'Петров', 'Сидоров', 'Смирнов', 'Кузнецов']
        return f"{random.choice(first_names)} {random.choice(last_names)}"

    def _generate_prescription_notes(self) -> str:
        """Generate prescription notes"""
        notes = [
            'Для постоянного ношения',
            'Для работы за компьютером',
            'Прогрессивные линзы',
            'Фотохромные линзы рекомендованы',
            'Антибликовое покрытие'
        ]
        return random.choice(notes)

    def _inject_catalog_error(
        self,
        product: Dict[str, Any],
        index: int
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Inject controlled error into product data

        Returns:
            Tuple of (error_type, modified_product)
        """
        error_types = [
            'missing_ean',
            'negative_price',
            'missing_category',
            'duplicate_sku',
            'invalid_stock',
            'price_cost_inconsistency',
        ]

        error_type = error_types[index % len(error_types)]

        if error_type == 'missing_ean':
            product['ean'] = None
        elif error_type == 'negative_price':
            product['price'] = -random.uniform(100, 1000)
        elif error_type == 'missing_category':
            product['category'] = None
        elif error_type == 'duplicate_sku':
            product['sku'] = f"PROD-{(index // 2) + 1:05d}"  # Duplicate previous
        elif error_type == 'invalid_stock':
            product['stock_qty'] = -random.randint(1, 100)
        elif error_type == 'price_cost_inconsistency':
            product['cost'] = product['price'] * 1.5  # Cost > Price (invalid)

        return error_type, product

    def _get_error_detail(self, error_type: str, product: Dict[str, Any]) -> str:
        """Get human-readable error description"""
        descriptions = {
            'missing_ean': 'Missing EAN barcode',
            'negative_price': f"Negative price: {product.get('price')}",
            'missing_category': 'Category not specified',
            'duplicate_sku': f"Duplicate SKU: {product.get('sku')}",
            'invalid_stock': f"Negative stock: {product.get('stock_qty')}",
            'price_cost_inconsistency': f"Cost ({product.get('cost')}) > Price ({product.get('price')})",
        }
        return descriptions.get(error_type, 'Unknown error')


def main():
    parser = argparse.ArgumentParser(description='Generate test data for OpticsERP')
    parser.add_argument('--catalog', type=int, help='Generate product catalog (specify size)')
    parser.add_argument('--supplier', type=str, help='Generate supplier pricelist (OptMarket, LensMaster, GlassWorld)')
    parser.add_argument('--prescriptions', type=int, help='Generate prescriptions (specify count)')
    parser.add_argument('--receipts', type=int, help='Generate receipts (specify count)')
    parser.add_argument('--all', action='store_true', help='Generate all test data')
    parser.add_argument('--seed', type=int, default=42, help='Random seed (default: 42)')
    parser.add_argument('--output', type=str, help='Output file path')
    parser.add_argument('--output-dir', type=str, default='./test_data', help='Output directory for --all')
    parser.add_argument('--format', type=str, choices=['json', 'csv', 'xlsx'], default='json', help='Output format')
    parser.add_argument('--error-rate', type=float, default=0.03, help='Error rate for catalog (default: 0.03)')

    args = parser.parse_args()

    generator = TestDataGenerator(seed=args.seed)
    output_dir = Path(args.output_dir)

    if args.all:
        print(f"🔄 Generating all test data (seed: {args.seed})...")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate catalog
        print("   📦 Generating catalog (10k products)...")
        catalog, errors = generator.generate_catalog(size=10000, error_rate=args.error_rate)
        _save_data(catalog, output_dir / 'catalog.json', 'json')
        _save_data(errors, output_dir / 'catalog_errors.json', 'json')

        # Generate supplier pricelists
        for supplier in ['OptMarket', 'LensMaster', 'GlassWorld']:
            print(f"   📄 Generating {supplier} pricelist...")
            pricelist, _ = generator.generate_supplier_pricelist(supplier, size=3000)
            _save_data(pricelist, output_dir / f'supplier_{supplier.lower()}.csv', 'csv')

        # Generate prescriptions
        print("   👓 Generating prescriptions (1k)...")
        prescriptions = generator.generate_prescriptions(count=1000)
        _save_data(prescriptions, output_dir / 'prescriptions.json', 'json')

        # Generate receipts
        print("   🧾 Generating receipts (500)...")
        receipts = generator.generate_receipts(count=500)
        _save_data(receipts, output_dir / 'receipts.json', 'json')

        print(f"✅ All test data generated in {output_dir}/")

    elif args.catalog:
        print(f"📦 Generating catalog ({args.catalog} products, error_rate={args.error_rate})...")
        catalog, errors = generator.generate_catalog(size=args.catalog, error_rate=args.error_rate)
        output = args.output or f'catalog_{args.catalog}.json'
        _save_data(catalog, output, args.format)
        _save_data(errors, output.replace('.', '_errors.'), 'json')
        print(f"✅ Generated {len(catalog)} products ({len(errors)} with errors) → {output}")

    elif args.supplier:
        print(f"📄 Generating {args.supplier} pricelist...")
        pricelist, _ = generator.generate_supplier_pricelist(args.supplier, size=5000)
        output = args.output or f'supplier_{args.supplier.lower()}.csv'
        _save_data(pricelist, output, args.format)
        print(f"✅ Generated {len(pricelist)} items → {output}")

    elif args.prescriptions:
        print(f"👓 Generating {args.prescriptions} prescriptions...")
        prescriptions = generator.generate_prescriptions(count=args.prescriptions)
        output = args.output or f'prescriptions_{args.prescriptions}.json'
        _save_data(prescriptions, output, args.format)
        print(f"✅ Generated {len(prescriptions)} prescriptions → {output}")

    elif args.receipts:
        print(f"🧾 Generating {args.receipts} receipts...")
        receipts = generator.generate_receipts(count=args.receipts)
        output = args.output or f'receipts_{args.receipts}.json'
        _save_data(receipts, output, args.format)
        print(f"✅ Generated {len(receipts)} receipts → {output}")

    else:
        parser.print_help()
        sys.exit(1)


def _save_data(data: List[Dict[str, Any]], output: str, format: str):
    """Save data to file"""
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if format == 'json' or not HAS_PANDAS:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    elif format == 'csv' and HAS_PANDAS:
        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False, encoding='utf-8')

    elif format == 'xlsx' and HAS_PANDAS:
        df = pd.DataFrame(data)
        df.to_excel(output_path, index=False, engine='openpyxl')


if __name__ == '__main__':
    main()
