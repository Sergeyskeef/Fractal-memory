#!/bin/bash
# ═══════════════════════════════════════════════════════
# Автоматическая настройка ВМ для Fractal Memory System
# ═══════════════════════════════════════════════════════
# Устанавливает: Docker, Docker Compose, настраивает пользователя
# Использование: bash scripts/setup_vm.sh

set -e

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Настройка ВМ для Fractal Memory System${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""

# Проверка что скрипт запущен от root или с sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}⚠️  Скрипт требует прав root. Используй: sudo bash scripts/setup_vm.sh${NC}"
    exit 1
fi

# ═══════════════════════════════════════════════════════
# 1. Обновление системы
# ═══════════════════════════════════════════════════════
echo -e "${CYAN}[1/5] Обновление системы...${NC}"
apt update
apt upgrade -y
echo -e "${GREEN}✅ Система обновлена${NC}"
echo ""

# ═══════════════════════════════════════════════════════
# 2. Установка зависимостей
# ═══════════════════════════════════════════════════════
echo -e "${CYAN}[2/5] Установка зависимостей...${NC}"
apt install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    python3 \
    python3-pip \
    build-essential
echo -e "${GREEN}✅ Зависимости установлены${NC}"
echo ""

# ═══════════════════════════════════════════════════════
# 3. Установка Docker
# ═══════════════════════════════════════════════════════
echo -e "${CYAN}[3/5] Установка Docker...${NC}"

if command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠️  Docker уже установлен, пропускаем...${NC}"
else
    # Добавить официальный GPG ключ Docker
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Добавить репозиторий Docker
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Установить Docker
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    echo -e "${GREEN}✅ Docker установлен${NC}"
fi

# Проверить версию
DOCKER_VERSION=$(docker --version)
echo "  Версия: ${DOCKER_VERSION}"
echo ""

# ═══════════════════════════════════════════════════════
# 4. Настройка пользователя для Docker
# ═══════════════════════════════════════════════════════
echo -e "${CYAN}[4/5] Настройка пользователя для Docker...${NC}"

# Определить текущего пользователя (если не root)
if [ -n "$SUDO_USER" ]; then
    DOCKER_USER="$SUDO_USER"
else
    # Если запущено от root, попробовать найти обычного пользователя
    DOCKER_USER=$(getent passwd | grep -v nologin | grep -v /bin/false | awk -F: '$3 >= 1000 {print $1; exit}')
    if [ -z "$DOCKER_USER" ]; then
        echo -e "${YELLOW}⚠️  Не найден обычный пользователь. Docker будет работать только от root.${NC}"
        echo -e "${YELLOW}   Рекомендуется создать пользователя и добавить его в группу docker:${NC}"
        echo -e "${YELLOW}   sudo usermod -aG docker USERNAME${NC}"
    fi
fi

if [ -n "$DOCKER_USER" ]; then
    # Создать группу docker (если ещё нет)
    groupadd -f docker
    
    # Добавить пользователя в группу docker
    usermod -aG docker "$DOCKER_USER"
    
    echo -e "${GREEN}✅ Пользователь ${DOCKER_USER} добавлен в группу docker${NC}"
    echo -e "${YELLOW}⚠️  Выйди и войди снова, чтобы изменения вступили в силу${NC}"
    echo -e "${YELLOW}   Или выполни: newgrp docker${NC}"
fi

echo ""

# ═══════════════════════════════════════════════════════
# 5. Проверка Docker Compose
# ═══════════════════════════════════════════════════════
echo -e "${CYAN}[5/5] Проверка Docker Compose...${NC}"

if docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version)
    echo "  Версия: ${COMPOSE_VERSION}"
    echo -e "${GREEN}✅ Docker Compose установлен${NC}"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    echo "  Версия: ${COMPOSE_VERSION}"
    echo -e "${GREEN}✅ Docker Compose установлен (legacy)${NC}"
else
    echo -e "${YELLOW}⚠️  Docker Compose не найден, устанавливаем...${NC}"
    # Установить Docker Compose (legacy)
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✅ Docker Compose установлен${NC}"
fi

echo ""

# ═══════════════════════════════════════════════════════
# Итоги
# ═══════════════════════════════════════════════════════
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Настройка завершена!${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✅ Docker установлен${NC}"
echo -e "${GREEN}✅ Docker Compose установлен${NC}"
if [ -n "$DOCKER_USER" ]; then
    echo -e "${GREEN}✅ Пользователь ${DOCKER_USER} настроен${NC}"
fi
echo ""
echo -e "${CYAN}Следующие шаги:${NC}"
echo "  1. Выйди и войди снова (или выполни: newgrp docker)"
echo "  2. Склонируй проект: git clone <repo-url>"
echo "  3. Настрой .env файл: cp .env.example .env"
echo "  4. Запусти проверку: bash scripts/check_vm_resources.sh"
echo "  5. Запусти контейнеры: docker compose up -d"
echo ""

