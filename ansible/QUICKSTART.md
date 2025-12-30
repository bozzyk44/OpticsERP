# Quick Start - Развертывание OpticsERP за 5 минут

## 🚀 Полностью автоматическое развертывание

### Шаг 1: Настройка конфигурации (2 минуты)

```bash
# 1. Перейти в директорию ansible
cd ansible

# 2. Скопировать и настроить inventory
cp inventories/production/hosts.yml.example \
   inventories/production/hosts.yml

# Отредактировать IP адреса серверов
vim inventories/production/hosts.yml
# Замените YOUR_SERVER_IP_HERE на реальные IP

# 3. Скопировать и настроить secrets
cp .env.example .env

# Отредактировать пароли
vim .env
# Установите сильные пароли для PostgreSQL, Redis, Grafana
```

### Шаг 2: Запуск развертывания (3 минуты + время на сервере)

```bash
# Перейти в scripts
cd scripts

# Сделать скрипты исполняемыми (Linux/macOS)
chmod +x *.sh

# Запустить полное развертывание
./deploy-wrapper.sh production
```

**Готово!** Скрипт автоматически:
1. ✅ Проверит и установит Ansible (если нужно)
2. ✅ Проверит inventory и SSH подключение
3. ✅ Проверит secrets (.env файл)
4. ✅ Развернет всю инфраструктуру (Docker, PostgreSQL, Redis, Nginx, Monitoring)
5. ✅ Запустит приложения
6. ✅ Проведет health check

---

## 📊 После развертывания

### Проверка статуса

```bash
# Общий статус
./health_check.sh production

# Статус приложений
./start_app.sh production status

# Логи
./start_app.sh production logs odoo 100
```

### Доступ к сервисам

- **Grafana:** http://YOUR_SERVER_IP:3000
  - Login: admin
  - Password: (из .env файла, GRAFANA_PASSWORD)

- **Prometheus:** http://YOUR_SERVER_IP:9090

- **Odoo:** http://YOUR_SERVER_IP (через Nginx)

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
