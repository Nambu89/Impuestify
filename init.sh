#!/bin/bash
# =============================================================================
# init.sh - TaxIA/Impuestify Environment Initialization
# =============================================================================
# Este script inicializa el entorno de desarrollo para que Claude Code
# pueda verificar el estado del proyecto al inicio de cada sesión.
#
# Uso: ./init.sh o bash init.sh
# =============================================================================

set -e  # Exit on error

echo "🚀 Inicializando entorno TaxIA/Impuestify..."
echo "============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# 1. Verificar estructura del proyecto
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}📁 Verificando estructura del proyecto...${NC}"

if [ -d "backend" ] && [ -d "frontend" ]; then
    echo -e "${GREEN}✅ Estructura backend/frontend OK${NC}"
else
    echo -e "${RED}❌ Error: No se encuentra backend/ o frontend/${NC}"
    exit 1
fi

# -----------------------------------------------------------------------------
# 2. Backend: Activar venv y verificar dependencias
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}🐍 Verificando backend Python...${NC}"

cd backend

# Activar virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
    echo -e "${GREEN}✅ Virtual environment activado${NC}"
else
    echo -e "${YELLOW}⚠️ No hay venv, creando...${NC}"
    python -m venv venv
    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
    pip install -r requirements.txt
fi

# Verificar que FastAPI importa correctamente
python -c "from app.main import app; print('✅ FastAPI app importa correctamente')" 2>/dev/null || {
    echo -e "${RED}❌ Error importando FastAPI app${NC}"
}

cd ..

# -----------------------------------------------------------------------------
# 3. Frontend: Verificar node_modules
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}⚛️ Verificando frontend React...${NC}"

cd frontend

if [ -d "node_modules" ]; then
    echo -e "${GREEN}✅ node_modules existe${NC}"
else
    echo -e "${YELLOW}⚠️ Instalando dependencias npm...${NC}"
    npm install
fi

# Verificar que compila
echo "Verificando compilación TypeScript..."
npm run build --silent 2>/dev/null && echo -e "${GREEN}✅ Frontend compila correctamente${NC}" || {
    echo -e "${YELLOW}⚠️ Hay errores de compilación, revisar${NC}"
}

cd ..

# -----------------------------------------------------------------------------
# 4. Mostrar estado de Git
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}📊 Estado de Git...${NC}"
echo "Rama actual: $(git branch --show-current)"
echo "Últimos 5 commits:"
git log --oneline -5

# -----------------------------------------------------------------------------
# 5. Mostrar resumen de claude-progress.txt
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}📋 Resumen de progreso anterior...${NC}"
if [ -f "claude-progress.txt" ]; then
    head -30 claude-progress.txt
else
    echo "No hay archivo de progreso previo"
fi

# -----------------------------------------------------------------------------
# 6. Resumen final
# -----------------------------------------------------------------------------
echo -e "\n${GREEN}=============================================${NC}"
echo -e "${GREEN}✅ Entorno inicializado correctamente${NC}"
echo -e "${GREEN}=============================================${NC}"
echo ""
echo "Próximos pasos sugeridos:"
echo "  1. Leer CLAUDE.md para contexto del proyecto"
echo "  2. Revisar claude-progress.txt para estado actual"
echo "  3. Ejecutar tests: cd backend && pytest tests/ -v"
echo "  4. Iniciar backend: cd backend && uvicorn app.main:app --reload"
echo "  5. Iniciar frontend: cd frontend && npm run dev"
