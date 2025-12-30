# WSL Setup для Ansible (Windows)

> **КРИТИЧНО:** Ansible НЕ работает нативно на Windows! Этот гайд обязателен для всех Windows разработчиков.

## Зачем WSL?

Ansible разработан для Unix/Linux систем и использует:
- `os.get_blocking()` - не существует на Windows
- POSIX-совместимые пути и права доступа
- Unix-специфичные системные вызовы

**Результат:** Ansible падает с `AttributeError` на нативном Windows.

**Решение:** WSL (Windows Subsystem for Linux) - полноценное Linux окружение внутри Windows.

---

## Установка WSL

### Шаг 1: Проверка версии Windows

WSL2 требует:
- Windows 10 версии 2004+ (Build 19041+)
- Windows 11 (любая версия)

```powershell
# Проверить версию
winver
```

### Шаг 2: Установка WSL

```powershell
# В PowerShell от имени администратора (Win+X → Windows PowerShell (Admin))
wsl --install -d Ubuntu-20.04
```

**Что происходит:**
1. Включается функция WSL2
2. Устанавливается Ubuntu 20.04
3. Создается виртуальное окружение Linux

**После установки:** Перезагрузить Windows (обязательно!)

### Шаг 3: Первый запуск

После перезагрузки:
1. Откроется терминал Ubuntu
2. Создайте пользователя (username)
3. Установите пароль (password)

```bash
# Проверка установки
lsb_release -a
# Должно быть: Ubuntu 20.04.x LTS
```

---

## Установка Ansible в WSL

### Обновление системы

```bash
sudo apt update && sudo apt upgrade -y
```

### Установка зависимостей

```bash
sudo apt install -y \
  python3 \
  python3-pip \
  python3-venv \
  python3-dev \
  build-essential \
  git \
  openssh-client \
  sshpass
```

### Установка Ansible

```bash
# Установка стабильной версии
pip3 install --user ansible-core==2.16.3 ansible==9.2.0

# Добавить в PATH (добавить в ~/.bashrc)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Проверка
ansible --version
```

**Ожидаемый вывод:**
```
ansible [core 2.16.3]
  config file = None
  configured module search path = ['/home/user/.ansible/plugins/modules', ...]
  ansible python module location = /home/user/.local/lib/python3.8/site-packages/ansible
  ...
```

---

## Доступ к проекту из WSL

### Windows диски в WSL

Windows диски автоматически монтируются в `/mnt/`:

```bash
# D:\OpticsERP → /mnt/d/OpticsERP
cd /mnt/d/OpticsERP/ansible

# C:\Users\username → /mnt/c/Users/username
cd /mnt/c/Users/username
```

### Настройка SSH ключей

```bash
# Скопировать SSH ключи из Windows
cp /mnt/c/Users/<ваш_username>/.ssh/id_rsa ~/.ssh/
cp /mnt/c/Users/<ваш_username>/.ssh/id_rsa.pub ~/.ssh/

# Установить правильные права (КРИТИЧНО!)
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub

# Или создать новые ключи
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

### Проверка подключения к серверу

```bash
# Из директории проекта
cd /mnt/d/OpticsERP/ansible

# Тест SSH
ssh bozzyk44@194.87.235.33

# Тест Ansible ping
ansible all -i inventories/production/hosts.yml -m ping
```

---

## Workflow разработки

### Ежедневная работа

```bash
# 1. Открыть WSL терминал
#    Способ 1: Пуск → Ubuntu 20.04
#    Способ 2: Windows Terminal → Ubuntu
#    Способ 3: wsl в PowerShell

# 2. Перейти в проект
cd /mnt/d/OpticsERP/ansible

# 3. Загрузить переменные окружения
source .env

# 4. Запустить deployment
bash scripts/deploy-wrapper.sh
```

### Редактирование файлов

**Можно использовать любой редактор на Windows:**

1. **VS Code:**
   - Установить расширение "Remote - WSL"
   - Открыть папку: `\\wsl$\Ubuntu-20.04\mnt\d\OpticsERP`

2. **Windows Explorer:**
   - Адрес: `\\wsl$\Ubuntu-20.04\mnt\d\OpticsERP`

3. **Любой редактор:**
   - Путь: `D:\OpticsERP\` (работает напрямую)

**Важно:** Файлы в `/mnt/d/OpticsERP` - это те же файлы, что и в `D:\OpticsERP` на Windows!

---

## Troubleshooting

### Ansible не найден после установки

```bash
# Проверить PATH
echo $PATH

# Добавить в ~/.bashrc
export PATH="$HOME/.local/bin:$PATH"
source ~/.bashrc
```

### Permission denied для SSH ключей

```bash
# Права должны быть строгими
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub
```

### "line 4: $'\r': command not found"

Файл содержит Windows line endings (CRLF вместо LF):

```bash
# Конвертация
sed -i 's/\r$//' filename.sh

# Или для всех .sh файлов
find /mnt/d/OpticsERP/ansible/scripts -name "*.sh" -exec sed -i 's/\r$//' {} \;
```

### WSL медленно работает с файлами на /mnt/d

**Проблема:** Файлы на Windows дисках (/mnt/d) медленнее, чем в Linux файловой системе.

**Решение для production:**
```bash
# Скопировать проект в Linux FS
cp -r /mnt/d/OpticsERP ~/OpticsERP
cd ~/OpticsERP/ansible
```

**Для разработки:** Оставить на /mnt/d для удобства редактирования из Windows.

### Проверка, что запущено в WSL

```bash
# Должно содержать "microsoft" или "WSL"
cat /proc/version

# Ожидаемый вывод:
# Linux version 5.10.x-microsoft-standard ...
```

---

## Альтернативы WSL

Если WSL недоступен (старая Windows, корпоративные ограничения):

### 1. Docker Desktop + Ansible контейнер

```bash
docker run --rm -it \
  -v D:/OpticsERP/ansible:/ansible \
  -w /ansible \
  cytopia/ansible:2.16 \
  ansible-playbook -i inventories/production/hosts.yml site.yml
```

### 2. Linux VM (VirtualBox, VMware)

1. Установить Ubuntu 20.04 в VM
2. Настроить shared folder: `D:\OpticsERP`
3. Запускать Ansible из VM

### 3. Удалённый Linux сервер

```bash
# С Windows клиента
ssh dev-server
cd /opt/OpticsERP/ansible
ansible-playbook ...
```

---

## Checklist готовности

Перед первым deployment убедитесь:

- [ ] WSL установлен и запущен
- [ ] `ansible --version` работает
- [ ] SSH ключи скопированы и права `chmod 600`
- [ ] `ssh bozzyk44@194.87.235.33` работает
- [ ] `cd /mnt/d/OpticsERP/ansible` открывает проект
- [ ] `.env` файл загружен: `source .env`
- [ ] Ansible ping работает: `ansible all -m ping`

**Всё работает?** → Запускайте `bash scripts/deploy-wrapper.sh`

---

## Дополнительные ресурсы

- [Официальная документация WSL](https://docs.microsoft.com/en-us/windows/wsl/)
- [Ansible на WSL](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html#installing-ansible-on-windows)
- [CLAUDE.md раздел 2.1](../../CLAUDE.md#21-ansible-и-wsl-критично-для-windows)
- [ansible/README.md](../../ansible/README.md#️-важно-wsl-для-windows)
