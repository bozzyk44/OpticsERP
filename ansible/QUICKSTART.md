# Quick Start - Развертывание OpticsERP

## 🚀 Полностью автоматическое развертывание

### Важно: Используйте WSL на Windows!

**КРИТИЧНО для Windows пользователей:**
```bash
# В PowerShell от имени администратора
wsl --install -d Ubuntu-20.04
# После установки перезагрузить и продолжить в WSL терминале
```

Все команды ниже выполняются **ТОЛЬКО в WSL терминале**!

### Шаг 1: Настройка конфигурации (2 минуты)

```bash
# 1. Перейти в директорию ansible (в WSL)
cd /mnt/d/OpticsERP/ansible

# 2. Скопировать и настроить inventory
cp inventories/production/hosts.yml.example \
   inventories/production/hosts.yml

# Отредактировать IP адреса серверов
vim inventories/production/hosts.yml
# Замените YOUR_SERVER_IP_HERE на реальные IP (например, 194.87.235.33)

# 3. Настроить SSH ключ (если еще не настроен)
ssh-copy-id YOUR_USER@YOUR_SERVER_IP
```

### Шаг 2: Запуск развертывания (5-10 минут)

```bash
# Проверить подключение
ansible all -i inventories/production/hosts.yml -m ping

# Запустить полное развертывание (рекомендуется)
ansible-playbook -i inventories/production/hosts.yml deploy-production.yml
```

**Готово!** Playbook автоматически выполнит **8 фаз** развертывания:

**Phase 1: Server Preparation**
- ✅ Устанавливает базовые пакеты
- ✅ Настраивает безопасность (UFW, SSH hardening)
- ✅ Устанавливает Docker

**Phase 2: Database & Cache**
- ✅ Устанавливает PostgreSQL 15
- ✅ Отключает system Redis (предотвращает конфликт портов)
- ✅ Устанавливает Redis 7.2 через Docker

**Phase 3: Nginx Reverse Proxy**
- ✅ Устанавливает Nginx
- ✅ Настраивает базовую конфигурацию

**Phase 4: Odoo Application**
- ✅ Разворачивает Odoo 17 через Docker Compose
- ✅ Инициализирует базу данных

**Phase 5: WebSocket Configuration** ⭐ **КРИТИЧНО!**
- ✅ Добавляет WebSocket map в nginx.conf
- ✅ Настраивает WebSocket proxy locations
- ✅ Устанавливает websocket_url в odoo.conf
- ✅ **Устраняет "Connection Lost" ошибки**

**Phase 6: Custom Modules**
- ✅ Устанавливает optics_core
- ✅ Устанавливает optics_pos_ru54fz
- ✅ Устанавливает connector_b
- ✅ Устанавливает ru_accounting_extras

**Phase 7: Mock Services** (опционально)
- Пропускается по умолчанию (только для тестирования)

**Phase 8: Monitoring** (опционально)
- Пропускается по умолчанию (установить: --tags monitoring)

**FINAL: Verification**
- ✅ Проверяет все сервисы
- ✅ Отображает итоговый статус

---

## 📊 После развертывания

### Проверка статуса

```bash
# На сервере - проверить сервисы
ansible odoo_servers -i inventories/production/hosts.yml \
  -m shell -a "systemctl status nginx docker" -b

# Проверить Docker контейнеры
ansible odoo_servers -i inventories/production/hosts.yml \
  -m shell -a "docker ps" -b

# КРИТИЧНО: Проверить WebSocket конфигурацию
ansible odoo_servers -i inventories/production/hosts.yml \
  -m shell -a "grep websocket_url /etc/opticserp/odoo.conf" -b

# Проверить порт 8072 (WebSocket)
ansible odoo_servers -i inventories/production/hosts.yml \
  -m shell -a "docker port opticserp_odoo | grep 8072" -b
# Ожидаемый результат: 8072/tcp -> 127.0.0.1:8072
```

### Доступ к сервисам

- **⭐ Odoo:** http://YOUR_SERVER_IP (через Nginx)
  - Login: admin
  - Password: (установленный при инициализации)
  - **ВАЖНО:** Проверьте отсутствие "Connection Lost" errors!

- **Grafana** (если установлен): http://YOUR_SERVER_IP:3000
  - Login: admin
  - Password: (из .env файла, GRAFANA_PASSWORD)

- **Prometheus** (если установлен): http://YOUR_SERVER_IP:9090

### ✅ Проверка WebSocket (ОБЯЗАТЕЛЬНО!)

После открытия Odoo в браузере:

1. **Откройте Browser Console (F12 → Console)**
   - ✅ Должно быть: "WebSocket connection established"
   - ❌ НЕ должно быть: WebSocket errors или 500 status

2. **Проверьте Network Tab (F12 → Network → WS filter)**
   - ✅ Connection к: `ws://YOUR_SERVER_IP/websocket`
   - ✅ Status: `101 Switching Protocols`
   - ✅ Connection: Active (green)

3. **Используйте интерфейс**
   - ❌ НЕ должно быть всплывающих окон "Connection Lost"
   - ✅ Real-time updates работают smoothly

**Если видите "Connection Lost" errors:**
```bash
# Применить WebSocket конфигурацию заново
ansible-playbook -i inventories/production/hosts.yml \
  configure-odoo-websocket.yml

# Или применить через site.yml
ansible-playbook -i inventories/production/hosts.yml \
  site.yml --tags websocket
```

См. подробнее: `ansible/WEBSOCKET_CONFIG_README.md`

---

## 🧪 Загрузка тестовых данных (опционально)

Для разработки и тестирования вы можете загрузить готовый набор тестовых данных.

### Что включено:

- ✅ 4 тестовых пользователя (менеджер, 2 кассира, оптик)
- ✅ 5 клиентов с контактами
- ✅ 3 поставщика
- ✅ ~20 продуктов (линзы, оправы Ray-Ban/Gucci/Oakley, аксессуары)
- ✅ 5 оптических рецептов
- ✅ 4 заказа на изготовление
- ✅ 5 заказов продаж

### Загрузка:

```bash
# ВАЖНО: Только для development/staging окружений!
ansible-playbook -i inventories/production/hosts.yml load-test-data.yml
```

**Playbook:**
1. Запросит подтверждение (введите "yes")
2. Создаст автоматический backup базы данных
3. Проверит установку модуля optics_core
4. Загрузит данные
5. Проверит корректность
6. Покажет тестовые учетные данные

### Тестовые учетные данные:

После загрузки войдите в Odoo:

| Роль | Email | Пароль |
|------|-------|--------|
| Менеджер | manager@optics.ru | manager123 |
| Кассир 1 | cashier1@optics.ru | cashier123 |
| Кассир 2 | cashier2@optics.ru | cashier123 |
| Оптик | optician@optics.ru | optician123 |

**URL:** http://YOUR_SERVER_IP

### Восстановление из backup:

Если нужно откатить тестовые данные:

```bash
# Backup находится в /tmp/odoo_production_before_testdata_*.sql.gz
gunzip < /tmp/odoo_production_before_testdata_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i opticserp_postgres psql -U odoo -d odoo_production
```

**Подробнее:** `ansible/test_data/README.md`

---

## 🛠️ Управление

### Перезапуск сервисов

```bash
./start_app.sh production restart
```

### Остановка сервисов

```bash
./start_app.sh production stop
```

### Обновление конфигурации

```bash
# Обновить только Nginx
ansible-playbook -i inventories/production/hosts.yml \
  site.yml --tags nginx

# Обновить только мониторинг
ansible-playbook -i inventories/production/hosts.yml \
  site.yml --tags monitoring
```

---

## 🔧 Troubleshooting

### Ansible не установлен

```bash
./install_ansible.sh
```

### SSH не подключается

```bash
# Добавить SSH ключ
ssh-copy-id YOUR_USER@YOUR_SERVER_IP

# Проверить вручную
ssh YOUR_USER@YOUR_SERVER_IP
```

### Проверить инфраструктуру

```bash
./check_inventory.sh production
```

### Проверить secrets

```bash
./validate_secrets.sh
```

---

## 📚 Полная документация

- **Скрипты:** `scripts/README.md`
- **Ansible:** `docs/deployment/ansible-guide.md`
- **Проект:** `CLAUDE.md`

---

## ⚠️ Важно перед запуском

1. **SSH доступ настроен:**
   ```bash
   ssh-copy-id YOUR_USER@YOUR_SERVER_IP
   ```

2. **Inventory настроен:**
   - Реальные IP адреса в `inventories/production/hosts.yml`
   - Правильный пользователь (с sudo правами)

3. **Secrets настроены:**
   - Сильные пароли в `.env` файле
   - Минимум 12 символов
   - Не placeholder значения

4. **Сервер требования:**
   - Ubuntu 20.04/22.04 или Debian 11/12
   - 4 GB RAM, 2 CPU, 50 GB disk
   - Порт 22 (SSH) открыт

---

## 🎯 Следующие шаги

После успешного развертывания:

1. **Импорт Grafana dashboards**
2. **Настройка alerting**
3. **Тестирование POS функциональности**
4. **Настройка backup verification**
5. **Документирование runbook**

Полная документация: `docs/deployment/ansible-guide.md`
