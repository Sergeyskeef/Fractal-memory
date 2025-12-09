#!/bin/bash
# ═══════════════════════════════════════════════════════
# FRACTAL MEMORY SYSTEM - Infrastructure Check
# ═══════════════════════════════════════════════════════
# Проверяет что Docker контейнеры работают корректно
#
# Использование:
#   bash scripts/check_infrastructure.sh

set -e

# Цвета
CYAN='\033[36m'
GREEN='\033[32m'
RED='\033[31m'
YELLOW='\033[33m'
RESET='\033[0m'

echo -e "${CYAN}═══════════════════════════════════════════════════════${RESET}"
echo -e "${CYAN}  FRACTAL MEMORY - Infrastructure Check${RESET}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${RESET}"
echo ""

# Счетчик ошибок
ERRORS=0

# ═══════════════════════════════════════════════════════
# Проверка Docker
# ═══════════════════════════════════════════════════════
echo -e "${CYAN}Checking Docker...${RESET}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not installed${RESET}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓ Docker installed${RESET}"
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose not installed${RESET}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓ Docker Compose installed${RESET}"
fi

echo ""

# ═══════════════════════════════════════════════════════
# Проверка контейнеров
# ═══════════════════════════════════════════════════════
echo -e "${CYAN}Checking containers...${RESET}"

# Neo4j
if docker ps | grep -q "fractal-memory-neo4j"; then
    echo -e "${GREEN}✓ Neo4j container running${RESET}"

    # Проверка health
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' fractal-memory-neo4j 2>/dev/null || echo "unknown")
    if [ "$HEALTH" = "healthy" ]; then
        echo -e "${GREEN}  └─ Health: healthy${RESET}"
    else
        echo -e "${YELLOW}  └─ Health: $HEALTH${RESET}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${RED}✗ Neo4j container not running${RESET}"
    ERRORS=$((ERRORS + 1))
fi

# Redis
if docker ps | grep -q "fractal-memory-redis"; then
    echo -e "${GREEN}✓ Redis container running${RESET}"

    # Проверка health
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' fractal-memory-redis 2>/dev/null || echo "unknown")
    if [ "$HEALTH" = "healthy" ]; then
        echo -e "${GREEN}  └─ Health: healthy${RESET}"
    else
        echo -e "${YELLOW}  └─ Health: $HEALTH${RESET}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${RED}✗ Redis container not running${RESET}"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# ═══════════════════════════════════════════════════════
# Проверка портов
# ═══════════════════════════════════════════════════════
echo -e "${CYAN}Checking ports...${RESET}"

# Neo4j ports
if netstat -an 2>/dev/null | grep -q ":7474" || ss -tuln 2>/dev/null | grep -q ":7474"; then
    echo -e "${GREEN}✓ Neo4j HTTP port (7474) open${RESET}"
else
    echo -e "${RED}✗ Neo4j HTTP port (7474) not accessible${RESET}"
    ERRORS=$((ERRORS + 1))
fi

if netstat -an 2>/dev/null | grep -q ":7687" || ss -tuln 2>/dev/null | grep -q ":7687"; then
    echo -e "${GREEN}✓ Neo4j Bolt port (7687) open${RESET}"
else
    echo -e "${RED}✗ Neo4j Bolt port (7687) not accessible${RESET}"
    ERRORS=$((ERRORS + 1))
fi

# Redis port
if netstat -an 2>/dev/null | grep -q ":6379" || ss -tuln 2>/dev/null | grep -q ":6379"; then
    echo -e "${GREEN}✓ Redis port (6379) open${RESET}"
else
    echo -e "${RED}✗ Redis port (6379) not accessible${RESET}"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# ═══════════════════════════════════════════════════════
# Проверка .env
# ═══════════════════════════════════════════════════════
echo -e "${CYAN}Checking configuration...${RESET}"

if [ -f ".env" ]; then
    echo -e "${GREEN}✓ .env file exists${RESET}"

    # Проверка обязательных переменных
    if grep -q "NEO4J_PASSWORD=" .env; then
        echo -e "${GREEN}  └─ NEO4J_PASSWORD set${RESET}"
    else
        echo -e "${RED}  └─ NEO4J_PASSWORD missing${RESET}"
        ERRORS=$((ERRORS + 1))
    fi

    if grep -q "OPENAI_API_KEY=" .env; then
        echo -e "${GREEN}  └─ OPENAI_API_KEY set${RESET}"
    else
        echo -e "${YELLOW}  └─ OPENAI_API_KEY missing (optional for infra)${RESET}"
    fi
else
    echo -e "${RED}✗ .env file not found${RESET}"
    echo -e "${YELLOW}  └─ Copy .env.example to .env and configure${RESET}"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# ═══════════════════════════════════════════════════════
# Итоги
# ═══════════════════════════════════════════════════════
echo -e "${CYAN}═══════════════════════════════════════════════════════${RESET}"

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${RESET}"
    echo -e "${YELLOW}Run 'make migrate' to set up database schema${RESET}"
    echo -e "${YELLOW}Run 'make smoke' to verify full setup${RESET}"
    exit 0
else
    echo -e "${RED}✗ $ERRORS check(s) failed${RESET}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${RESET}"
    echo -e "  1. Start containers: ${CYAN}make docker-up${RESET}"
    echo -e "  2. Check logs:       ${CYAN}make docker-logs${RESET}"
    echo -e "  3. Create .env:      ${CYAN}cp .env.example .env${RESET}"
    exit 1
fi
