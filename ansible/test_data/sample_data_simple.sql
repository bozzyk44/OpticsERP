-- ============================================================================
-- OpticsERP Sample Test Data
-- ============================================================================
-- Purpose: Populate database with realistic test data for development/testing
-- Database: odoo_production
-- Modules: optics_core, optics_pos_ru54fz, connector_b, ru_accounting_extras
-- ============================================================================

-- Начинаем транзакцию
BEGIN;

-- ============================================================================
-- 1. USERS & AUTHENTICATION
-- ============================================================================

-- Партнеры для пользователей (СНАЧАЛА partners, потом users из-за FK constraint)
INSERT INTO res_partner (id, name, email, phone, active, is_company, company_id, create_date, write_date)
VALUES
    (100, '{"en_US": "Менеджер Иванов"}'::jsonb, 'manager@optics.ru', '+7-495-111-22-33', true, false, 1, now(), now()),
    (101, '{"en_US": "Кассир Петрова"}'::jsonb, 'cashier1@optics.ru', '+7-495-111-22-34', true, false, 1, now(), now()),
    (102, '{"en_US": "Кассир Сидорова"}'::jsonb, 'cashier2@optics.ru', '+7-495-111-22-35', true, false, 1, now(), now()),
    (103, '{"en_US": "Оптик Смирнов"}'::jsonb, 'optician@optics.ru', '+7-495-111-22-36', true, false, 1, now(), now())
ON CONFLICT (id) DO NOTHING;

-- Создаем тестовых пользователей (помимо admin)
INSERT INTO res_users (id, login, password, active, create_date, write_date, company_id, partner_id, notification_type, share)
VALUES
    (100, 'manager@optics.ru', 'manager123', true, now(), now(), 1, 100, 'inbox', false),
    (101, 'cashier1@optics.ru', 'cashier123', true, now(), now(), 1, 101, 'inbox', false),
    (102, 'cashier2@optics.ru', 'cashier123', true, now(), now(), 1, 102, 'inbox', false),
    (103, 'optician@optics.ru', 'optician123', true, now(), now(), 1, 103, 'inbox', false)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 2. CUSTOMERS (Клиенты)
-- ============================================================================

INSERT INTO res_partner (id, name, email, phone, mobile, street, city, zip, active, is_company, company_id)
VALUES
    (200, '{"en_US": "Алексей Петрович Волков"}'::jsonb, 'a.volkov@example.com', '+7-926-123-45-67', NULL, 'ул. Ленина, д. 15', 'Москва', '101000', true, false, 1),
    (201, '{"en_US": "Мария Ивановна Соколова"}'::jsonb, 'm.sokolova@example.com', '+7-916-234-56-78', '+7-926-345-67-89', 'ул. Гагарина, д. 23', 'Москва', '102000', true, false, 1),
    (202, '{"en_US": "Дмитрий Сергеевич Орлов"}'::jsonb, 'd.orlov@example.com', '+7-903-456-78-90', NULL, 'ул. Мира, д. 8', 'Москва', '103000', true, false, 1),
    (203, '{"en_US": "Елена Александровна Жукова"}'::jsonb, 'e.zhukova@example.com', NULL, '+7-915-567-89-01', 'пр. Победы, д. 45', 'Москва', '104000', true, false, 1),
    (204, '{"en_US": "Сергей Владимирович Медведев"}'::jsonb, 's.medvedev@example.com', '+7-925-678-90-12', NULL, 'ул. Кирова, д. 12', 'Москва', '105000', true, false, 1)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 3. SUPPLIERS (Поставщики)
-- ============================================================================

INSERT INTO res_partner (id, name, email, phone, street, city, zip, active, is_company, supplier_rank, company_id, vat)
VALUES
    (300, '{"en_US": "ООО Линза Плюс"}'::jsonb, 'sales@linzaplus.ru', '+7-495-789-01-23', 'ул. Промышленная, д. 5', 'Москва', '106000', true, true, 5, 1, '7701234567'),
    (301, '{"en_US": "ООО Оптика Сервис"}'::jsonb, 'info@optikaservice.ru', '+7-495-890-12-34', 'пр. Ленинский, д. 78', 'Москва', '107000', true, true, 4, 1, '7702345678'),
    (302, '{"en_US": "ООО Мировое Зрение"}'::jsonb, 'order@worldvision.ru', '+7-495-901-23-45', 'ул. Складская, д. 33', 'Москва', '108000', true, true, 3, 1, '7703456789')
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 4. PRODUCT CATEGORIES (Категории товаров)
-- ============================================================================

INSERT INTO product_category (id, name, parent_id, create_date, write_date)
VALUES
    (100, '{"en_US": "Очковые линзы"}'::jsonb, NULL, now(), now()),
    (101, 'Однофокальные линзы', 100, now(), now()),
    (102, 'Прогрессивные линзы', 100, now(), now()),
    (103, 'Бифокальные линзы', 100, now(), now()),
    (104, '{"en_US": "Оправы"}'::jsonb, NULL, now(), now()),
    (105, 'Мужские оправы', 104, now(), now()),
    (106, 'Женские оправы', 104, now(), now()),
    (107, 'Детские оправы', 104, now(), now()),
    (108, '{"en_US": "Солнцезащитные очки"}'::jsonb, NULL, now(), now()),
    (109, '{"en_US": "Аксессуары"}'::jsonb, NULL, now(), now())
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 5. PRODUCTS (Товары)
-- ============================================================================

-- Линзы (СНАЧАЛА templates, потом products с product_tmpl_id)
INSERT INTO product_template (id, name, type, categ_id, list_price, uom_id, uom_po_id, sale_ok, purchase_ok, active, detailed_type, tracking, sale_line_warn, create_date, write_date)
VALUES
    (1000, '{"en_US": "Линза однофокальная 1.5 AR"}'::jsonb, 'product', 101, 3500.00, 1, 1, true, true, true, 'consu', 'none', 'no-message', now(), now()),
    (1001, '{"en_US": "Линза однофокальная 1.6 AR"}'::jsonb, 'product', 101, 4500.00, 1, 1, true, true, true, 'consu', 'none', 'no-message', now(), now()),
    (1002, '{"en_US": "Линза однофокальная 1.67 AR"}'::jsonb, 'product', 101, 5500.00, 1, 1, true, true, true, 'consu', 'none', 'no-message', now(), now()),
    (1003, '{"en_US": "Линза прогрессивная 1.5 AR"}'::jsonb, 'product', 102, 8500.00, 1, 1, true, true, true, 'consu', 'none', 'no-message', now(), now()),
    (1004, '{"en_US": "Линза прогрессивная 1.6 AR"}'::jsonb, 'product', 102, 9500.00, 1, 1, true, true, true, 'consu', 'none', 'no-message', now(), now()),
    (1005, '{"en_US": "Линза бифокальная 1.5 AR"}'::jsonb, 'product', 103, 5500.00, 1, 1, true, true, true, 'consu', 'none', 'no-message', now(), now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO product_product (id, product_tmpl_id, default_code, active, create_date, write_date)
VALUES
    (1000, 1000, 'LENS-SF-1.5-AR', true, now(), now()),
    (1001, 1001, 'LENS-SF-1.6-AR', true, now(), now()),
    (1002, 1002, 'LENS-SF-1.67-AR', true, now(), now()),
    (1003, 1003, 'LENS-PROG-1.5-AR', true, now(), now()),
    (1004, 1004, 'LENS-PROG-1.6-AR', true, now(), now()),
    (1005, 1005, 'LENS-BF-1.5-AR', true, now(), now())
ON CONFLICT (id) DO NOTHING;

-- Оправы
INSERT INTO product_template (id, name, type, categ_id, list_price, uom_id, uom_po_id, sale_ok, purchase_ok, active, detailed_type, tracking, sale_line_warn, create_date, write_date)
VALUES
    (2000, '{"en_US": "Оправа муж. Ray-Ban RB5228"}'::jsonb, 'product', 105, 12500.00, 1, 1, true, true, true, 'consu', 'none', 'no-message', now(), now()),
    (2001, '{"en_US": "Оправа жен. Gucci GG0123O"}'::jsonb, 'product', 106, 18500.00, 1, 1, true, true, true, 'consu', 'none', 'no-message', now(), now()),
    (2002, '{"en_US": "Оправа муж. Oakley OX8150"}'::jsonb, 'product', 105, 9500.00, 1, 1, true, true, true, 'consu', 'none', 'no-message', now(), now()),
    (2003, '{"en_US": "Оправа жен. Prada VPR16T"}'::jsonb, 'product', 106, 15500.00, 1, 1, true, true, true, 'consu', 'none', 'no-message', now(), now()),
    (2004, '{"en_US": "Оправа дет. LEGO Kids LK01"}'::jsonb, 'product', 107, 4500.00, 1, 1, true, true, true, 'consu', 'none', 'no-message', now(), now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO product_product (id, product_tmpl_id, default_code, active, create_date, write_date)
VALUES
    (2000, 2000, 'FRAME-M-RAY-001', true, now(), now()),
    (2001, 2001, 'FRAME-W-GUC-001', true, now(), now()),
    (2002, 2002, 'FRAME-M-OAK-001', true, now(), now()),
    (2003, 2003, 'FRAME-W-PRA-001', true, now(), now()),
    (2004, 2004, 'FRAME-K-LEGO-001', true, now(), now())
ON CONFLICT (id) DO NOTHING;

-- Солнцезащитные очки
INSERT INTO product_template (id, name, type, categ_id, list_price, uom_id, uom_po_id, sale_ok, purchase_ok, active, detailed_type, tracking, sale_line_warn, create_date, write_date)
VALUES
    (3000, '{"en_US": "Очки солн. Ray-Ban Aviator"}'::jsonb, 'product', 108, 14500.00, 1, 1, true, true, true, 'consu', 'none', 'no-message', now(), now()),
    (3001, '{"en_US": "Очки солн. Oakley Holbrook"}'::jsonb, 'product', 108, 11500.00, 1, 1, true, true, true, 'consu', 'none', 'no-message', now(), now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO product_product (id, product_tmpl_id, default_code, active, create_date, write_date)
VALUES
    (3000, 3000, 'SUN-RAY-AVI-001', true, now(), now()),
    (3001, 3001, 'SUN-OAK-HOLB-001', true, now(), now())
ON CONFLICT (id) DO NOTHING;

-- Аксессуары
INSERT INTO product_template (id, name, type, categ_id, list_price, uom_id, uom_po_id, sale_ok, purchase_ok, active, detailed_type, tracking, sale_line_warn, create_date, write_date)
VALUES
    (4000, '{"en_US": "Футляр жесткий"}'::jsonb, 'product', 109, 850.00, 1, 1, true, true, true, 'consu', 'none', 'no-message', now(), now()),
    (4001, '{"en_US": "Спрей для очистки 50мл"}'::jsonb, 'product', 109, 450.00, 1, 1, true, true, true, 'consu', 'none', 'no-message', now(), now()),
    (4002, '{"en_US": "Салфетка микрофибра"}'::jsonb, 'product', 109, 250.00, 1, 1, true, true, true, 'consu', 'none', 'no-message', now(), now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO product_product (id, product_tmpl_id, default_code, active, create_date, write_date)
VALUES
    (4000, 4000, 'ACC-CASE-HARD', true, now(), now()),
    (4001, 4001, 'ACC-CLEAN-SPRAY', true, now(), now()),
    (4002, 4002, 'ACC-CLOTH-MICRO', true, now(), now())
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 6. STOCK (Склад - устанавливаем начальные остатки)
-- ============================================================================

-- Примечание: В реальной системе это делается через stock.quant
-- Здесь упрощенный вариант для примера

-- ============================================================================
-- 7. OPTICS CORE - PRESCRIPTIONS (Рецепты)
-- ============================================================================

-- Таблица optics.prescription должна быть создана модулем optics_core
-- Вставляем тестовые рецепты


-- ============================================================================
-- VERIFICATION QUERIES (для проверки загруженных данных)
-- ============================================================================

-- Подсчет загруженных записей
DO $$
BEGIN
    RAISE NOTICE '✅ Test data loaded successfully!';
    RAISE NOTICE '';
    RAISE NOTICE 'Summary:';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Users: %', (SELECT COUNT(*) FROM res_users WHERE id >= 100 AND id < 200);
    RAISE NOTICE 'Customers: %', (SELECT COUNT(*) FROM res_partner WHERE id >= 200 AND id < 300);
    RAISE NOTICE 'Suppliers: %', (SELECT COUNT(*) FROM res_partner WHERE id >= 300 AND id < 400);
    RAISE NOTICE 'Product Categories: %', (SELECT COUNT(*) FROM product_category WHERE id >= 100);
    RAISE NOTICE 'Products: %', (SELECT COUNT(*) FROM product_product WHERE id >= 1000);
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Test credentials:';
    RAISE NOTICE 'Manager: manager@optics.ru / manager123';
    RAISE NOTICE 'Cashier 1: cashier1@optics.ru / cashier123';
    RAISE NOTICE 'Cashier 2: cashier2@optics.ru / cashier123';
    RAISE NOTICE 'Optician: optician@optics.ru / optician123';
END $$;

-- Commit transaction
COMMIT;
