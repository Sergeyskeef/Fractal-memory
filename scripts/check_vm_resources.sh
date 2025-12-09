#!/bin/bash
# ═══════════════════════════════════════════════════════
# Проверка ресурсов ВМ для Fractal Memory System
# ═══════════════════════════════════════════════════════
# Проверяет: RAM, CPU, диск, Docker, порты
# Рекомендуемые ресурсы: 2 CPU, 6GB RAM, 20GB+ диск

set -e

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Флаги проверки
PASSED=0
FAILED=0
WARNINGS=0

echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Проверка ресурсов ВМ для Fractal Memory System${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""

# ═══════════════════════════════════════════════════════
# 1. Проверка RAM
# ═══════════════════════════════════════════════════════
echo -e "${CYAN}[1/6] Проверка RAM...${NC}"

TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
TOTAL_RAM_GB=$((TOTAL_RAM_KB / 1024 / 1024))
AVAILABLE_RAM_KB=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
AVAILABLE_RAM_GB=$((AVAILABLE_RAM_KB / 1024 / 1024))

echo "  Всего RAM: ${TOTAL_RAM_GB}GB"
echo "  Доступно RAM: ${AVAILABLE_RAM_GB}GB"

if [ "$TOTAL_RAM_GB" -ge 6 ]; then
    echo -e "  ${GREEN}✅ RAM достаточно (≥6GB)${NC}"
    ((PASSED++))
elif [ "$TOTAL_RAM_GB" -ge 4 ]; then
    echo -e "  ${YELLOW}⚠️  RAM минимально (4-6GB), рекомендуется 6GB+${NC}"
    ((WARNINGS++))
else
    echo -e "  ${RED}❌ RAM недостаточно (<4GB), требуется минимум 6GB${NC}"
    ((FAILED++))
fi

echo ""

# ═══════════════════════════════════════════════════════
# 2. Проверка CPU
# ═══════════════════════════════════════════════════════
echo -e "${CYAN}[2/6] Проверка CPU...${NC}"

CPU_CORES=$(nproc)
CPU_MODEL=$(grep -m 1 "model name" /proc/cpuinfo | cut -d ':' -f 2 | xargs)

echo "  Ядер CPU: ${CPU_CORES}"
echo "  Модель: ${CPU_MODEL}"

if [ "$CPU_CORES" -ge 2 ]; then
    echo -e "  ${GREEN}✅ CPU достаточно (≥2 ядра)${NC}"
    ((PASSED++))
else
    echo -e "  ${RED}❌ CPU недостаточно (<2 ядра), требуется минимум 2${NC}"
    ((FAILED++))
fi

echo ""

# ═══════════════════════════════════════════════════════
# 3. Проверка диска
# ═══════════════════════════════════════════════════════
echo -e "${CYAN}[3/6] Проверка диска...${NC}"

DISK_TOTAL=$(df -h / | awk 'NR==2 {print $2}' | sed 's/G//')
DISK_AVAILABLE=$(df -h / | awk 'NR==2 {print $4}' | sed 's/G//')
DISK_USED_PERCENT=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')

echo "  Всего места: ${DISK_TOTAL}GB"
echo "  Доступно: ${DISK_AVAILABLE}GB"
echo "  Использовано: ${DISK_USED_PERCENT}%"

if [ "$DISK_AVAILABLE" -ge 20 ]; then
    echo -e "  ${GREEN}✅ Диск достаточно (≥20GB свободно)${NC}"
    ((PASSED++))
elif [ "$DISK_AVAILABLE" -ge 10 ]; then
    echo -e "  ${YELLOW}⚠️  Диск минимально (10-20GB), рекомендуется 20GB+${NC}"
    ((WARNINGS++))
else
    echo -e "  ${RED}❌ Диск недостаточно (<10GB), требуется минимум 20GB${NC}"
    ((FAILED++))
fi

echo ""

# ═══════════════════════════════════════════════════════
# 4. Проверка Docker
# ═══════════════════════════════════════════════════════
echo -e "${CYAN}[4/6] Проверка Docker...${NC}"

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
    echo "  Docker версия: ${DOCKER_VERSION}"
    
    # Проверить что Docker работает
    if docker ps &> /dev/null; then
        echo -e "  ${GREEN}✅ Docker установлен и работает${NC}"
        ((PASSED++))
    else
        echo -e "  ${RED}❌ Docker установлен, но не работает (нужны права?)${NC}"
        echo "     Попробуй: sudo usermod -aG docker \$USER && newgrp docker"
        ((FAILED++))
    fi
else
    echo -e "  ${RED}❌ Docker не установлен${NC}"
    echo "     Установи: curl -fsSL https://get.docker.com | sh"
    ((FAILED++))
fi

echo ""

# ═══════════════════════════════════════════════════════
# 5. Проверка Docker Compose
# ═══════════════════════════════════════════════════════
echo -e "${CYAN}[5/6] Проверка Docker Compose...${NC}"

if docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version | awk '{print $4}')
    echo "  Docker Compose версия: ${COMPOSE_VERSION}"
    echo -e "  ${GREEN}✅ Docker Compose установлен${NC}"
    ((PASSED++))
elif command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version | awk '{print $3}' | sed 's/,//')
    echo "  Docker Compose версия: ${COMPOSE_VERSION}"
    echo -e "  ${GREEN}✅ Docker Compose установлен (legacy)${NC}"
    ((PASSED++))
else
    echo -e "  ${RED}❌ Docker Compose не установлен${NC}"
    echo "     Установи: https://docs.docker.com/compose/install/"
    ((FAILED++))
fi

echo ""

# ═══════════════════════════════════════════════════════
# 6. Проверка портов
# ═══════════════════════════════════════════════════════
echo -e "${CYAN}[6/6] Проверка портов...${NC}"

PORTS=(7474 7687 6379)
PORTS_FREE=true

for PORT in "${PORTS[@]}"; do
    if command -v netstat &> /dev/null; then
        if netstat -tuln 2>/dev/null | grep -q ":${PORT} "; then
            echo -e "  ${YELLOW}⚠️  Порт ${PORT} занят${NC}"
            PORTS_FREE=false
        fi
    elif command -v ss &> /dev/null; then
        if ss -tuln 2>/dev/null | grep -q ":${PORT} "; then
            echo -e "  ${YELLOW}⚠️  Порт ${PORT} занят${NC}"
            PORTS_FREE=false
        fi
    fi
done

if [ "$PORTS_FREE" = true ]; then
    echo -e "  ${GREEN}✅ Порты 7474, 7687, 6379 свободны${NC}"
    ((PASSED++))
else
    echo -e "  ${YELLOW}⚠️  Некоторые порты заняты (это нормально, если контейнеры уже запущены)${NC}"
    ((WARNINGS++))
fi

echo ""

# ═══════════════════════════════════════════════════════
# Итоги
# ═══════════════════════════════════════════════════════
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Результаты проверки${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${GREEN}✅ Пройдено: ${PASSED}${NC}"
echo -e "  ${YELLOW}⚠️  Предупреждений: ${WARNINGS}${NC}"
echo -e "  ${RED}❌ Ошибок: ${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}🎉 Все проверки пройдены! ВМ готова к работе.${NC}"
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}⚠️  ВМ готова, но есть предупреждения. Рекомендуется обратить внимание.${NC}"
    exit 0
else
    echo -e "${RED}❌ Есть критические проблемы. Исправьте их перед продолжением.${NC}"
    exit 1
fi

