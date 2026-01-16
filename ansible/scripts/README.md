# Deployment Scripts - OpticsERP

Набор скриптов для автоматизации развертывания OpticsERP.

## 📋 Список скриптов

### Основные скрипты

| Скрипт | Назначение | Использование |
|--------|------------|---------------|
| `deploy-wrapper.sh` | **Главный скрипт** - полная автоматизация | `./deploy-wrapper.sh production` |
| `deploy.sh` | Развертывание инфраструктуры | `./deploy.sh production full` |
| `start_app.sh` | Запуск приложений на серверах | `./start_app.sh production all` |

### Вспомогательные скрипты

| Скрипт | Назначение | Использование |
|--------|------------|---------------|
| `install_ansible.sh` | Проверка и установка Ansible | `./install_ansible.sh` |
| `check_inventory.sh` | Валидация inventory файла | `./check_inventory.sh production` |
| `validate_secrets.sh` | Проверка .env файла | `./validate_secrets.sh` |
| `health_check.sh` | Проверка состояния сервисов | `./health_check.sh production` |

## 🚀 Быстрый старт

### 1. Полное развертывание (рекомендуется)

```bash
# Один скрипт для всего процесса
cd ansible/scripts
chmod +x *.sh
./deploy-wrapper.sh production
```

Этот скрипт выполнит:
1. ✅ Проверку и установку Ansible
2. ✅ Валидацию inventory
3. ✅ Проверку secrets (.env)
4. ✅ Развертывание инфраструктуры (PostgreSQL, Redis, Nginx, Prometheus, Grafana)
5. ✅ Развертывание Odoo приложения (Odoo 17, KKT Adapter, Celery, Flower)
6. ✅ Health check

### 2. Пошаговое развертывание

```bash
# Шаг 1: Установить Ansible
./install_ansible.sh

# Шаг 2: Настроить inventory и secrets
cp ../inventories/production/hosts.yml.example \
   ../inventories/production/hosts.yml
vim ../inventories/production/hosts.yml  # ← Edit IP addresses

cp ../.env.example ../.env
vim ../.env  # ← Edit passwords

# Шаг 3: Проверить конфигурацию
./check_inventory.sh production
./validate_secrets.sh

# Шаг 4: Развернуть инфраструктуру
./deploy.sh production full

# Шаг 5: Развернуть Odoo приложение
cd ..
source .env
ansible-playbook -i inventories/production/hosts.yml deploy-odoo.yml

# Шаг 6: Проверить здоровье системы
cd scripts
./health_check.sh production
```

## 📖 Детальное описание

### deploy-wrapper.sh

**Главный скрипт** - полная автоматизация от начала до конца.

```bash
# Синтаксис
./deploy-wrapper.sh [environment] [skip-checks]

# Примеры
./deploy-wrapper.sh production          # С подтверждениями
./deploy-wrapper.sh production true     # Без подтверждений
./deploy-wrapper.sh staging             # Staging окружение
```

**Что делает:**
1. Проверяет и устанавливает Ansible
2. Валидирует inventory
3. Проверяет secrets
4. Развертывает инфраструктуру (PostgreSQL, Redis, Nginx, Prometheus, Grafana)
5. Ожидает стабилизации инфраструктуры (30s)
6. Развертывает Odoo приложение (Odoo 17, KKT Adapter, Celery Worker, Celery Flower)
7. Ожидает стабилизации приложений (30s)
8. Проводит health check

---

### deploy.sh

Развертывание инфраструктуры через Ansible playbooks.

```bash
# Синтаксис
./deploy.sh [environment] [mode]

# Modes
prepare   - Базовая подготовка сервера (common, docker, security)
full      - Полная инфраструктура (по умолчанию)
infra     - Только инфраструктура (БД, мониторинг)
app       - Только приложения
check     - Dry-run, проверка без изменений

# Примеры
./deploy.sh production prepare          # Подготовить сервер
./deploy.sh production full             # Полное развертывание
./deploy.sh staging check               # Проверка staging
./deploy.sh production infra            # Только инфраструктура
```

**Что развертывает (инфраструктура):**
- ✅ Системные пакеты и зависимости
- ✅ Docker + Docker Compose v2
- ✅ PostgreSQL 15
- ✅ Redis 7.2
- ✅ Nginx
- ✅ Prometheus + Grafana
- ✅ UFW firewall + fail2ban
- ✅ SSH hardening

**Примечание:** Odoo приложение развертывается отдельным playbook `deploy-odoo.yml`

---

### start_app.sh

Управление приложениями на удаленных серверах.

```bash
# Синтаксис
./start_app.sh [environment] [component]

# Components
all         - Все компоненты (default)
odoo        - Только Odoo
kkt-adapter - KKT Adapter + Celery stack
monitoring  - Только Prometheus + Grafana
status      - Показать статус
logs        - Показать логи
restart     - Перезапустить все
stop        - Остановить все

# Примеры
./start_app.sh production all                # Запустить всё
./start_app.sh production odoo               # Только Odoo
./start_app.sh production kkt-adapter        # KKT + Celery + Flower
./start_app.sh production status             # Статус сервисов
./start_app.sh production logs odoo 100      # 100 строк логов Odoo
./start_app.sh production logs kkt-adapter   # Логи KKT Adapter
./start_app.sh production logs celery 50     # 50 строк логов Celery
./start_app.sh production logs flower 50     # Логи Flower
./start_app.sh production restart            # Перезапуск
./start_app.sh production stop               # Остановка
```

---

### install_ansible.sh

Проверяет наличие Ansible, устанавливает если нужно.

```bash
./install_ansible.sh
```

**Что делает:**
- Проверяет версию Ansible (требуется >= 2.12)
- Предлагает установить если не найден
- Определяет OS автоматически (Ubuntu/Debian/macOS/Windows)
- Устанавливает Ansible collections (community.docker, community.postgresql)
- Устанавливает Python зависимости (docker, psycopg2-binary)

---

### check_inventory.sh

Валидация inventory файла.

```bash
# Синтаксис
./check_inventory.sh [environment]

# Примеры
./check_inventory.sh production
./check_inventory.sh staging
```

**Проверки:**
- ✅ Существование файла
- ✅ Placeholder IP адреса
- ✅ SSH connectivity
- ✅ Информация о серверах (OS, RAM, CPU)

---

### validate_secrets.sh

Проверка .env файла с паролями.

```bash
./validate_secrets.sh
```

**Проверки:**
- ✅ Существование .env файла
- ✅ Наличие обязательных переменных
- ✅ Длина паролей (минимум 8 символов)
- ✅ Слабые пароли (placeholder значения)
- ✅ .env в .gitignore

---

### health_check.sh

Проверка состояния развернутых сервисов.

```bash
# Синтаксис
./health_check.sh [environment]

# Примеры
./health_check.sh production
./health_check.sh staging
```

**Проверяет:**
- ✅ System services (docker, nginx, postgresql, redis, chrony)
- ✅ Network ports (5432, 6379, 8069, 8072, 8000, 5555, 9090, 3000, 80)
- ✅ Docker containers (odoo, kkt_adapter, celery_worker, celery_flower, prometheus, grafana)
- ✅ Database connectivity (PostgreSQL, Redis)
- ✅ NTP sync status

---

## 🎯 Типичные сценарии

### Сценарий 1: Первое развертывание на новом сервере

```bash
# 1. Настроить конфигурацию
cp ../inventories/production/hosts.yml.example \
   ../inventories/production/hosts.yml
vim ../inventories/production/hosts.yml

cp ../.env.example ../.env
vim ../.env

# 2. Запустить полное развертывание
./deploy-wrapper.sh production
```

### Сценарий 2: Обновление только инфраструктуры

```bash
./deploy.sh production infra
./health_check.sh production
```

### Сценарий 3: Перезапуск приложений

```bash
./start_app.sh production restart
./start_app.sh production status
```

### Сценарий 4: Troubleshooting

```bash
# Проверить статус
./start_app.sh production status

# Посмотреть логи
./start_app.sh production logs odoo 200
./start_app.sh production logs kkt-adapter 100
./start_app.sh production logs celery 100
./start_app.sh production logs flower 50

# Health check
./health_check.sh production

# Проверить инфраструктуру
ansible all -i ../inventories/production/hosts.yml \
  -m shell -a "systemctl status docker nginx postgresql"
```

### Сценарий 5: Staging → Production

```bash
# 1. Deploy на staging
./deploy-wrapper.sh staging

# 2. Тестирование на staging
./health_check.sh staging
# ... тесты ...

# 3. Deploy на production
./deploy-wrapper.sh production
```

## ⚠️ Важные замечания

1. **Первый запуск:**
   - Сначала настроить inventory (IP адреса)
   - Сначала настроить .env (пароли)
   - Проверить SSH доступ к серверам

2. **Безопасность:**
   - НЕ коммитить .env файл
   - Использовать сильные пароли (12+ символов)
   - Проверить .env в .gitignore

3. **Staging first:**
   - Тестировать на staging перед production
   - Использовать check mode для dry-run

4. **Permissions:**
   - Скрипты должны быть исполняемыми: `chmod +x *.sh`
   - Windows: использовать Git Bash или WSL

## 🔧 Troubleshooting

### Проблема: "Ansible not found"

```bash
# Решение: Установить Ansible
./install_ansible.sh
```

### Проблема: "Inventory file not found"

```bash
# Решение: Создать из примера
cp ../inventories/production/hosts.yml.example \
   ../inventories/production/hosts.yml
vim ../inventories/production/hosts.yml
```

### Проблема: "SSH connection failed"

```bash
# Решение: Добавить SSH ключ
ssh-copy-id deploy@YOUR_SERVER_IP

# Проверить вручную
ssh deploy@YOUR_SERVER_IP
```

### Проблема: "Required variable missing"

```bash
# Решение: Настроить .env
cp ../.env.example ../.env
vim ../.env
source ../.env
```

## 📚 Дополнительная информация

**Документация:**
- [Ansible Guide](../../docs/deployment/ansible-guide.md)
- [CLAUDE.md](../../CLAUDE.md) - §10, §11

**Ansible playbooks:**
- `../site.yml` - Главный playbook (инфраструктура)
- `../deploy-odoo.yml` - Odoo приложение
- `../prepare-server.yml` - Базовая подготовка

**Inventories:**
- `../inventories/production/hosts.yml` - Production
- `../inventories/staging/hosts.yml` - Staging

**Roles:**
- `../roles/common/` - Базовая система
- `../roles/docker/` - Docker + Docker Compose v2
- `../roles/postgresql/` - PostgreSQL 15
- `../roles/redis/` - Redis 7.2
- `../roles/nginx/` - Nginx reverse proxy
- `../roles/monitoring/` - Prometheus + Grafana
- `../roles/security/` - Security hardening (UFW, fail2ban, SSH)
- `../roles/odoo/` - Odoo 17 + KKT Adapter + Celery stack

## 🏗️ Архитектура развертывания

### Docker Compose v2 Stack

Все приложения развертываются в единый `docker-compose.yml` на сервере:

```
/opt/opticserp/
├── docker-compose.yml          # Единый compose файл для всех сервисов
├── addons/                     # Кастомные Odoo модули
│   ├── optics_core/
│   ├── optics_pos_ru54fz/
│   ├── connector_b/
│   └── ru_accounting_extras/
├── kkt_adapter/                # KKT Adapter код
│   ├── app/
│   ├── data/buffer.db
│   ├── Dockerfile
│   └── requirements.txt
└── data/                       # Odoo filestore
```

### Сервисы в Docker Compose:

| Сервис | Контейнер | Порты | Назначение |
|--------|-----------|-------|------------|
| `odoo` | opticserp_odoo | 8069, 8072 | Odoo 17 ERP/POS |
| `kkt_adapter` | opticserp_kkt_adapter | 8000 | FastAPI для фискализации |
| `celery_worker` | opticserp_celery | - | Celery Worker (4 очереди) |
| `celery_flower` | opticserp_flower | 5555 | Celery monitoring UI |

### Сетевая архитектура:

- **Режим:** Bridge network (не host mode)
- **Доступ к хосту:** Через `host.docker.internal` (extra_hosts)
- **PostgreSQL:** На хосте (localhost:5432), доступен через host.docker.internal
- **Redis:** На хосте (localhost:6379), доступен через host.docker.internal

### Команды Docker Compose v2:

```bash
# ✅ Правильно (v2)
docker compose up -d
docker compose ps
docker compose logs odoo
docker compose restart

# ❌ Неправильно (устаревший v1)
docker-compose up -d      # Не используется
```

## 📊 Порты и URL сервисов

После развертывания доступны следующие сервисы:

| Сервис | URL | Порт | Описание |
|--------|-----|------|----------|
| Odoo | http://SERVER:8069 | 8069 | Web UI Odoo |
| Odoo Longpolling | http://SERVER:8072 | 8072 | Websockets |
| KKT Adapter | http://SERVER:8000 | 8000 | REST API |
| Celery Flower | http://SERVER:5555 | 5555 | Celery мониторинг |
| Prometheus | http://SERVER:9090 | 9090 | Метрики |
| Grafana | http://SERVER:3000 | 3000 | Дашборды |
| PostgreSQL | SERVER:5432 | 5432 | База данных |
| Redis | SERVER:6379 | 6379 | Cache/Broker |
