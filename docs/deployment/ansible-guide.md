# Ansible Deployment Guide - OpticsERP

> **Версия:** 1.0
> **Дата:** 2025-01-31
> **Базовый документ:** CLAUDE.md §10-11

## 📋 Оглавление

1. [Введение](#введение)
2. [Предварительные требования](#предварительные-требования)
3. [Структура проекта](#структура-проекта)
4. [Быстрый старт](#быстрый-старт)
5. [Конфигурация](#конфигурация)
6. [Развертывание](#развертывание)
7. [Управление](#управление)
8. [Troubleshooting](#troubleshooting)

---

## Введение

Ansible playbooks для автоматизированного развертывания OpticsERP на production/staging серверах.

**Что автоматизируется:**
- ✅ Установка системных пакетов и зависимостей
- ✅ Настройка Docker и Docker Compose
- ✅ Установка PostgreSQL 15 и Redis
- ✅ Настройка NTP (chrony) для HLC
- ✅ Nginx reverse proxy
- ✅ Monitoring stack (Prometheus + Grafana)
- ✅ Security hardening (UFW, fail2ban, SSH)
- ✅ Автоматические бэкапы

---

## Предварительные требования

### Control Node (ваша машина)

```bash
# Установка Ansible
sudo apt update
sudo apt install ansible

# Проверка версии (требуется >= 2.12)
ansible --version

# Установка дополнительных коллекций
ansible-galaxy collection install community.docker
ansible-galaxy collection install community.postgresql
```

### Target Servers (целевые серверы)

**Минимальные требования:**
- Ubuntu 20.04/22.04 LTS или Debian 11/12
- SSH доступ с публичным ключом
- Пользователь с sudo правами
- Python 3.8+
- 4 GB RAM, 2 CPU cores, 50 GB disk

**Network:**
- Открытый SSH порт (по умолчанию 22)
- Доступ в интернет для загрузки пакетов

---

## Структура проекта

```
ansible/
├── ansible.cfg                    # Ansible конфигурация
├── site.yml                       # Главный playbook (все серверы)
├── prepare-server.yml             # Playbook для базовой подготовки
├── inventories/
│   ├── production/
│   │   └── hosts.yml             # Production инвентарь
│   └── staging/
│       └── hosts.yml             # Staging инвентарь
├── group_vars/
│   └── all.yml                   # Общие переменные
├── host_vars/                    # Переменные для отдельных хостов
└── roles/
    ├── common/                   # Базовая настройка системы
    ├── docker/                   # Docker + Docker Compose
    ├── postgresql/               # PostgreSQL 15
    ├── redis/                    # Redis 7.2
    ├── nginx/                    # Nginx reverse proxy
    ├── monitoring/               # Prometheus + Grafana
    └── security/                 # Firewall + SSH hardening
```

---

## Быстрый старт

### Вариант A: Автоматическое развертывание (рекомендуется)

**Один скрипт для полной автоматизации:**

```bash
cd ansible/scripts

# Сделать скрипты исполняемыми (Linux/macOS)
chmod +x *.sh

# Запустить полное развертывание
./deploy-wrapper.sh production
```

Этот скрипт выполнит:
- ✅ Проверку и установку Ansible
- ✅ Валидацию inventory и secrets
- ✅ Развертывание инфраструктуры
- ✅ Запуск приложений
- ✅ Health check

**Другие полезные скрипты:**

```bash
# Только развертывание инфраструктуры
./deploy.sh production full

# Запуск приложений
./start_app.sh production all

# Проверка здоровья системы
./health_check.sh production

# Показать логи
./start_app.sh production logs odoo 100
```

**Полная документация скриптов:** `ansible/scripts/README.md`

---

### Вариант B: Ручное развертывание через Ansible

### 1. Настройка SSH доступа

```bash
# Скопировать публичный ключ на сервер
ssh-copy-id -i ~/.ssh/id_rsa.pub deploy@YOUR_SERVER_IP

# Проверить доступ
ssh deploy@YOUR_SERVER_IP
```

### 2. Настройка inventory

Отредактируйте `ansible/inventories/production/hosts.yml`:

```yaml
all:
  children:
    odoo_servers:
      hosts:
        odoo-prod-01:
          ansible_host: 192.168.1.10  # ← Ваш IP
          ansible_user: deploy         # ← Ваш пользователь
          ansible_port: 22
```

### 3. Проверка подключения

```bash
cd ansible

# Ping всех хостов
ansible all -i inventories/production/hosts.yml -m ping

# Вывод информации о системе
ansible all -i inventories/production/hosts.yml -m setup
```

### 4. Подготовка сервера

```bash
# Базовая подготовка (common + docker + security)
ansible-playbook -i inventories/production/hosts.yml prepare-server.yml

# Или с verbose выводом
ansible-playbook -i inventories/production/hosts.yml prepare-server.yml -vv

# Для staging окружения
ansible-playbook -i inventories/staging/hosts.yml prepare-server.yml
```

### 5. Полное развертывание

```bash
# Развертывание всего стека
ansible-playbook -i inventories/production/hosts.yml site.yml

# Только для определенного хоста
ansible-playbook -i inventories/production/hosts.yml site.yml --limit odoo-prod-01

# Только определенные роли
ansible-playbook -i inventories/production/hosts.yml site.yml --tags "docker,nginx"
```

---

## Конфигурация

### Переменные окружения

**КРИТИЧНО:** Создайте `.env` файл для паролей:

```bash
# ansible/.env
export POSTGRES_PASSWORD='your_strong_password_here'
export REDIS_PASSWORD='your_redis_password_here'
export GRAFANA_PASSWORD='your_grafana_password_here'
```

Загрузите переменные:
```bash
source .env
ansible-playbook -i inventories/production/hosts.yml site.yml
```

### Настройка портов

В `group_vars/all.yml`:

```yaml
# Стандартные порты (НЕ МЕНЯТЬ без крайней необходимости!)
postgresql_port: 5432
redis_port: 6379
odoo_port: 8069
kkt_adapter_port: 8000
prometheus_port: 9090
grafana_port: 3000
```

### Настройка firewall

По умолчанию открыты:
- 22 (SSH)
- 80 (HTTP)
- 443 (HTTPS)
- 8069 (Odoo, только внутренний через Nginx)
- 8000 (KKT Adapter, только внутренний)

Для добавления портов отредактируйте `group_vars/all.yml`:

```yaml
allowed_tcp_ports:
  - 22
  - 80
  - 443
  - 9090  # Prometheus (если нужен внешний доступ)
```

### Настройка NTP серверов

В `group_vars/all.yml`:

```yaml
ntp_servers:
  - 0.ru.pool.ntp.org
  - 1.ru.pool.ntp.org
  - 2.ru.pool.ntp.org
```

### PostgreSQL настройки

В `roles/postgresql/defaults/main.yml`:

```yaml
postgresql_max_connections: 200
postgresql_shared_buffers: "256MB"
postgresql_effective_cache_size: "1GB"
postgresql_work_mem: "16MB"
```

---

## Развертывание

### Сценарий 1: Новый production сервер

```bash
# 1. Подготовка сервера (базовые зависимости)
ansible-playbook -i inventories/production/hosts.yml prepare-server.yml

# 2. Установка баз данных
ansible-playbook -i inventories/production/hosts.yml site.yml --tags "postgresql,redis"

# 3. Установка мониторинга
ansible-playbook -i inventories/production/hosts.yml site.yml --tags "monitoring"

# 4. Полное развертывание
ansible-playbook -i inventories/production/hosts.yml site.yml
```

### Сценарий 2: Обновление конфигурации

```bash
# Обновить только Nginx конфигурацию
ansible-playbook -i inventories/production/hosts.yml site.yml --tags "nginx"

# Обновить PostgreSQL настройки
ansible-playbook -i inventories/production/hosts.yml site.yml --tags "postgresql"
```

### Сценарий 3: Staging развертывание

```bash
# Использовать staging inventory
ansible-playbook -i inventories/staging/hosts.yml site.yml
```

### Сценарий 4: Dry-run (проверка без изменений)

```bash
# Check mode - показывает что будет сделано
ansible-playbook -i inventories/production/hosts.yml site.yml --check

# Diff mode - показывает изменения в файлах
ansible-playbook -i inventories/production/hosts.yml site.yml --check --diff
```

---

## Управление

### Проверка статуса сервисов

```bash
# Ansible ad-hoc команды
ansible odoo_servers -i inventories/production/hosts.yml -m shell -a "systemctl status docker"
ansible odoo_servers -i inventories/production/hosts.yml -m shell -a "systemctl status postgresql"
ansible odoo_servers -i inventories/production/hosts.yml -m shell -a "systemctl status nginx"

# Проверка UFW
ansible all -i inventories/production/hosts.yml -m shell -a "ufw status"

# Проверка NTP
ansible all -i inventories/production/hosts.yml -m shell -a "timedatectl status"
```

### Перезапуск сервисов

```bash
# Nginx
ansible-playbook -i inventories/production/hosts.yml site.yml --tags "nginx" --extra-vars "nginx_force_restart=yes"

# PostgreSQL (ОСТОРОЖНО!)
ansible odoo_servers -i inventories/production/hosts.yml -m systemd -a "name=postgresql state=restarted" --become
```

### Бэкапы

PostgreSQL бэкапы настраиваются автоматически:
- **Время:** 03:00 ежедневно
- **Путь:** `/var/backups/opticserp/postgresql/`
- **Retention:** 90 дней

Проверка бэкапов:
```bash
ansible db_servers -i inventories/production/hosts.yml -m shell -a "ls -lh /var/backups/opticserp/postgresql/"
```

Ручной бэкап:
```bash
ansible db_servers -i inventories/production/hosts.yml -m shell -a "/usr/local/bin/pg_backup.sh" --become-user postgres
```

---

## Troubleshooting

### Проблема: Ansible не может подключиться к серверу

**Симптомы:**
```
fatal: [odoo-prod-01]: UNREACHABLE!
```

**Решение:**
```bash
# 1. Проверить SSH доступ вручную
ssh deploy@192.168.1.10

# 2. Проверить inventory файл
cat ansible/inventories/production/hosts.yml

# 3. Проверить SSH ключ
ssh-add -l
ssh-add ~/.ssh/id_rsa

# 4. Использовать verbose mode
ansible-playbook -i inventories/production/hosts.yml site.yml -vvv
```

### Проблема: PostgreSQL не устанавливается

**Симптомы:**
```
TASK [postgresql : Add PostgreSQL repository] *******
failed: [odoo-prod-01]
```

**Решение:**
```bash
# 1. Проверить интернет на сервере
ansible odoo_servers -i inventories/production/hosts.yml -m shell -a "ping -c 3 google.com"

# 2. Обновить apt cache
ansible odoo_servers -i inventories/production/hosts.yml -m apt -a "update_cache=yes" --become

# 3. Повторить установку
ansible-playbook -i inventories/production/hosts.yml site.yml --tags "postgresql"
```

### Проблема: UFW блокирует SSH после применения

**Решение:**
```bash
# ВАЖНО: Всегда открывайте SSH порт ПЕРЕД включением UFW!
# Security роль это делает автоматически

# Если потеряли доступ, используйте консоль VPS провайдера:
sudo ufw allow 22/tcp
sudo ufw reload
```

### Проблема: Prometheus не стартует

**Симптомы:**
```
TASK [monitoring : Wait for Prometheus to be ready] ***
FAILED - RETRYING
```

**Решение:**
```bash
# 1. Проверить логи
ansible monitoring_servers -i inventories/production/hosts.yml -m shell \
  -a "docker logs prometheus" --become-user deploy

# 2. Проверить permissions
ansible monitoring_servers -i inventories/production/hosts.yml -m shell \
  -a "ls -la /opt/monitoring/prometheus/data" --become

# 3. Пересоздать контейнер
ansible monitoring_servers -i inventories/production/hosts.yml -m shell \
  -a "cd /opt/monitoring && docker-compose down && docker-compose up -d" --become-user deploy
```

### Проблема: Chrony не синхронизирует время

**Решение:**
```bash
# 1. Проверить статус chrony
ansible all -i inventories/production/hosts.yml -m shell -a "chronyc tracking"

# 2. Проверить доступность NTP серверов
ansible all -i inventories/production/hosts.yml -m shell -a "chronyc sources"

# 3. Принудительная синхронизация
ansible all -i inventories/production/hosts.yml -m shell \
  -a "chronyc makestep" --become
```

---

## Best Practices

### 1. Тестирование на staging

**ВСЕГДА** тестируйте изменения на staging перед production:

```bash
# 1. Staging
ansible-playbook -i inventories/staging/hosts.yml site.yml

# 2. Проверка
# ... тесты ...

# 3. Production
ansible-playbook -i inventories/production/hosts.yml site.yml
```

### 2. Git workflow

```bash
# 1. Commit изменений в Ansible
cd ansible
git add .
git commit -m "feat(ansible): add monitoring role"

# 2. Push
git push origin feature/ansible-deployment
```

### 3. Secrets management

**НЕ КОММИТИТЬ:**
- `.env` файлы
- Пароли в plain text
- Приватные SSH ключи

**Использовать:**
```bash
# ansible-vault для паролей
ansible-vault encrypt group_vars/production/vault.yml

# Или environment variables
export POSTGRES_PASSWORD='...'
```

### 4. Мониторинг после deployment

После каждого deployment проверяйте:

```bash
# 1. Сервисы запущены
ansible all -i inventories/production/hosts.yml -m shell \
  -a "systemctl status docker nginx postgresql redis chrony"

# 2. Firewall активен
ansible all -i inventories/production/hosts.yml -m shell \
  -a "ufw status | grep Status"

# 3. Prometheus scrape targets
# Открыть http://YOUR_SERVER:9090/targets

# 4. Grafana dashboards
# Открыть http://YOUR_SERVER:3000
```

---

## Следующие шаги

После успешного развертывания инфраструктуры:

1. **Развернуть приложение:** См. `docs/deployment/application-deployment.md`
2. **Настроить мониторинг:** Импортировать Grafana dashboards
3. **Настроить алерты:** Подключить Alertmanager
4. **Backup strategy:** Настроить offsite бэкапы
5. **DR plan:** Протестировать recovery процедуры

---

## Ссылки

- **CLAUDE.md** - Основные инструкции
- **docs/5. Офлайн-режим.md** - Архитектура системы
- [Ansible Documentation](https://docs.ansible.com/)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/15/)
