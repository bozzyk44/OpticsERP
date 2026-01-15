# Ansible Automation - OpticsERP

Автоматизация развертывания инфраструктуры OpticsERP.

## ⚠️ Важно: WSL для Windows

**КРИТИЧНО для Windows пользователей:**

Ansible **НЕ работает нативно на Windows**. Используйте WSL (Windows Subsystem for Linux).

### Установка WSL:

```powershell
# В PowerShell от имени администратора
wsl --install -d Ubuntu-20.04
# Перезагрузить Windows
```

### Установка Ansible в WSL:

```bash
# В WSL терминале
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv
pip3 install ansible-core==2.16.3 ansible==9.2.0

# Проверка
ansible --version
```

### Доступ к проекту:

```bash
# Проект в D:\OpticsERP доступен в WSL как:
cd /mnt/d/OpticsERP/ansible
```

**Все команды ниже выполняются ТОЛЬКО в WSL терминале!**

---

## 🚀 Quick Start

### Полное развертывание с нуля (РЕКОМЕНДУЕТСЯ)

```bash
# 1. Настроить inventory
cp inventories/production/hosts.yml.example inventories/production/hosts.yml
vim inventories/production/hosts.yml

# 2. Проверить подключение
ansible all -i inventories/production/hosts.yml -m ping

# 3. Полное развертывание (включая WebSocket конфигурацию)
ansible-playbook -i inventories/production/hosts.yml deploy-production.yml
```

**Этот playbook автоматически:**
- ✅ Устанавливает все зависимости (Docker, PostgreSQL, Redis, Nginx)
- ✅ Настраивает WebSocket для Odoo (критично!)
- ✅ Устанавливает кастомные модули
- ✅ Проверяет корректность развертывания

### Обновление существующей инфраструктуры

```bash
# Только для обновления существующих серверов
ansible-playbook -i inventories/production/hosts.yml site.yml

# Применить только WebSocket конфигурацию
ansible-playbook -i inventories/production/hosts.yml site.yml --tags websocket
```

### Загрузка тестовых данных (опционально)

```bash
# Загрузить тестовые данные для разработки/тестирования
ansible-playbook -i inventories/production/hosts.yml load-test-data.yml
```

**Тестовые данные включают:**
- 4 тестовых пользователя (менеджер, 2 кассира, оптик)
- 5 клиентов
- 3 поставщика
- ~20 продуктов (линзы, оправы, аксессуары)
- 5 рецептов
- 4 заказа на изготовление
- 5 заказов продаж

**Важно:**
- ⚠️ Playbook запросит подтверждение перед загрузкой
- 💾 Автоматически создаст backup базы данных
- ✅ Проверит установку модуля optics_core
- 🔒 Только для development/staging окружений!

**Тестовые учетные данные:**
- manager@optics.ru / manager123
- cashier1@optics.ru / cashier123
- cashier2@optics.ru / cashier123
- optician@optics.ru / optician123

## 📁 Структура

```
ansible/
├── site.yml                      # Главный playbook
├── deploy-production.yml         # ⭐ Master deployment playbook
├── load-test-data.yml            # Загрузка тестовых данных
├── prepare-server.yml            # Базовая подготовка
├── inventories/
│   ├── production/hosts.yml     # Production серверы
│   └── staging/hosts.yml        # Staging серверы
├── group_vars/all.yml           # Общие переменные
├── test_data/                   # Тестовые данные
│   ├── sample_data.sql          # SQL с тестовыми данными
│   └── README.md                # Документация тестовых данных
└── roles/                       # Ansible роли
    ├── common/                  # Система (Python, NTP, пользователи)
    ├── docker/                  # Docker + Docker Compose
    ├── postgresql/              # PostgreSQL 15
    ├── redis/                   # Redis 7.2
    ├── nginx/                   # Nginx reverse proxy
    ├── monitoring/              # Prometheus + Grafana
    └── security/                # UFW + fail2ban + SSH hardening
```

## 📖 Документация

**Основная документация:**
- [Ansible Guide](../docs/deployment/ansible-guide.md) - Полное руководство по Ansible
- **[WebSocket Configuration](WEBSOCKET_CONFIG_README.md)** ⭐ **ВАЖНО** - Настройка WebSocket для устранения "Connection Lost"
- [Playbooks Index](PLAYBOOKS_INDEX.md) - Индекс всех playbooks с описанием

**Deployment Playbooks:**
- `deploy-production.yml` ⭐ **Рекомендуется** - Полное развертывание с WebSocket
- `site.yml` - Обновление существующей инфраструктуры
- `configure-odoo-websocket.yml` - Только WebSocket конфигурация
- `load-test-data.yml` - Загрузка тестовых данных (dev/staging only)

## 🔑 Переменные окружения

Создайте `.env` файл (не коммитить в git!):

```bash
export POSTGRES_PASSWORD='your_password'
export REDIS_PASSWORD='your_password'
export GRAFANA_PASSWORD='your_password'
```

Загрузите перед запуском:
```bash
source .env
ansible-playbook ...
```

## 🎯 Основные команды

### Проверка
```bash
# Ping всех хостов
ansible all -i inventories/production/hosts.yml -m ping

# Информация о системе
ansible all -i inventories/production/hosts.yml -m setup

# Check mode (без изменений)
ansible-playbook -i inventories/production/hosts.yml site.yml --check --diff
```

### Развертывание
```bash
# Только базовая подготовка
ansible-playbook -i inventories/production/hosts.yml prepare-server.yml

# Полное развертывание
ansible-playbook -i inventories/production/hosts.yml site.yml

# Только определенные роли
ansible-playbook -i inventories/production/hosts.yml site.yml --tags "docker,nginx"

# Только определенный хост
ansible-playbook -i inventories/production/hosts.yml site.yml --limit odoo-prod-01
```

### Управление
```bash
# Ad-hoc команды
ansible all -i inventories/production/hosts.yml -m shell -a "systemctl status docker"
ansible all -i inventories/production/hosts.yml -m shell -a "ufw status"
ansible all -i inventories/production/hosts.yml -m shell -a "timedatectl status"

# Перезапуск сервиса
ansible odoo_servers -i inventories/production/hosts.yml -m systemd \
  -a "name=nginx state=restarted" --become
```

## 🏷️ Tags

Доступные теги для выборочного выполнения:

- `common` - Базовая система
- `docker` - Docker + Docker Compose
- `postgresql` - PostgreSQL
- `redis` - Redis
- `nginx` - Nginx
- `monitoring` - Prometheus + Grafana
- `security` - Firewall + SSH

## ⚠️ ВАЖНО

1. **SSH доступ:** Убедитесь, что публичный ключ добавлен на сервер
2. **Порты:** НЕ меняйте стандартные порты (см. CLAUDE.md §3)
3. **NTP:** Chrony критичен для HLC - не отключайте
4. **Firewall:** Security роль автоматически открывает SSH перед включением UFW
5. **Staging first:** Тестируйте на staging перед production
6. **⭐ WebSocket:** `deploy-production.yml` ОБЯЗАТЕЛЬНО включает WebSocket конфигурацию
   - Без этого Odoo будет показывать "Connection Lost" errors
   - Если деплоили без WebSocket: `ansible-playbook site.yml --tags websocket`
   - Проверка: `grep websocket_url /etc/opticserp/odoo.conf`
7. **System Redis:** Автоматически отключается для предотвращения конфликта портов

## 📞 Support

При проблемах см. Troubleshooting в [ansible-guide.md](../docs/deployment/ansible-guide.md)

## 📄 License

Proprietary - OpticsERP Project
