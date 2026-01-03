# Руководство по настройке сервера для Digital Secretary

Следуйте этой инструкции для подготовки нового сервера (Ubuntu 22.04) к развертыванию проекта.

## 1. Подготовка сервера

Вам понадобится чистый сервер с Ubuntu 22.04 LTS (рекомендуется).
Зайдите на сервер по SSH:
```bash
ssh root@<IP-адрес-вашего-сервера>
```

## 2. Установка Docker и Docker Compose

Выполните следующие команды одну за одной, чтобы установить Docker:

```bash
# Обновление пакетов
sudo apt update && sudo apt upgrade -y

# Установка зависимостей
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Добавление ключа GPG Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Добавление репозитория Docker
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установка Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Проверка установки
sudo docker --version
```

Установка Docker Compose (Plugin):
```bash
sudo apt install -y docker-compose-plugin
docker compose version
```

## 3. Настройка GitHub Secrets

Перейдите в ваш репозиторий на GitHub: `Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`.

Добавьте следующие секреты:

| Имя секрета | Значение |
|-------------|----------|
| `HOST` | IP-адрес вашего нового сервера (например, `95.217.X.X`) |
| `SSH_PRIVATE_KEY` | Ваш приватный SSH ключ (содержимое файла `~/.ssh/id_ed25519` или того, который вы используете для доступа к серверу). **Важно:** Публичный ключ (`.pub`) должен быть добавлен в `~/.ssh/authorized_keys` на сервере. |
| `GEMINI_API_KEY` | Ваш API ключ для Google Gemini |
| `SENTRY_DSN` | (Опционально) Ключ для мониторинга ошибок (Sentry.io) |

## 4. Настройка DNS (Если IP изменился)

Если вы используете новый сервер, не забудьте обновить **A-запись** вашего домена (`link-it.tech`) у регистратора домена на новый IP адрес.

## 5. Генерация SSH ключей (если у вас нет)

Если у вас нет отдельного ключа для GitHub Actions, сгенерируйте его на своем компьютере:
```bash
ssh-keygen -t ed25519 -C "github-actions"
```
Содержимое файла `id_ed25519` (приватный ключ) добавьте в **GitHub Secrets** (`SSH_PRIVATE_KEY`).
Содержимое файла `id_ed25519.pub` (публичный ключ) добавьте на **НА СЕРВЕР** в файл `/root/.ssh/authorized_keys`.

## 5. Запуск деплоя

После того как сервер настроен и секреты добавлены:
1. Перейдите во вкладку **Actions** в GitHub репозитории.
2. Выберите workflow **CI/CD Pipeline**.
3. Нажмите **Run workflow** (или сделайте пуш в ветку `main`, чтобы триггернуть его автоматически).

## Проверка

После успешного деплоя сайт будет доступен по адресу: `https://link-it.tech`
