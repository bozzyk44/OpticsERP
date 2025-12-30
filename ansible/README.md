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

```bash
# 1. Настроить inventory
cp inventories/production/hosts.yml.example inventories/production/hosts.yml
vim inventories/production/hosts.yml

# 2. Проверить подключение
ansible all -i inventories/production/hosts.yml -m ping

# 3. Подготовить сервер
ansible-playbook -i inventories/production/hosts.yml prepare-server.yml

# 4. Полное развертывание
ansible-playbook -i inventories/production/hosts.yml site.yml
```

## 📁 Структура

```
ansible/
├── site.yml                      # Главный playbook
├── prepare-server.yml            # Базовая подготовка
├── inventories/
│   ├── production/hosts.yml     # Production серверы
│   └── staging/hosts.yml        # Staging серверы
├── group_vars/all.yml           # Общие переменные
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

Полная документация: [docs/deployment/ansible-guide.md](../docs/deployment/ansible-guide.md)

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

## 📞 Support

При проблемах см. Troubleshooting в [ansible-guide.md](../docs/deployment/ansible-guide.md)

## 📄 License

Proprietary - OpticsERP Project
