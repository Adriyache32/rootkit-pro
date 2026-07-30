#!/bin/bash
#============================================================
# REDMI NOTE 9 PRO - Bootloader Unlock Workflow
# Ready to run after Aug 2, 2026 (168h cooldown)
#============================================================
set -euo pipefail

R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' C='\033[0;36m' NC='\033[0m'
BLD='\033[1m'

HDD="/media/adriyache32/HDD/ROOTKIT-PRO"
LOG="/home/adriyache32/.rootkit-pro/unlock.log"
MIUNLOCK="/tmp/MiUnlockTool"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"; }

echo -e "${BLD}${C}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLD}${C}║  REDMI NOTE 9 PRO - Desbloqueo Bootloader       ║${NC}"
echo -e "${BLD}${C}║  Paso 1: Mi Unlock Tool                          ║${NC}"
echo -e "${BLD}${C}╚══════════════════════════════════════════════════╝${NC}"

# Check cooldown
echo -e "\n${Y}Verificando cooldown de 168h...${NC}"
BOUND_DATE="2026-07-26 20:00"
UNLOCK_DATE=$(date -d "$BOUND_DATE + 168 hours" '+%Y-%m-%d %H:%M')
NOW=$(date '+%Y-%m-%d %H:%M')
echo -e "Cuenta vinculada: ${BOUND_DATE}"
echo -e "Desbloqueo disponible: ${UNLOCK_DATE}"
echo -e "Ahora: ${NOW}"

if [[ "$NOW" < "$UNLOCK_DATE" ]]; then
    echo -e "${R}ERROR: Aún en cooldown. Vuelve después de $UNLOCK_DATE${NC}"
    exit 1
fi
echo -e "${G}Cooldown completado OK${NC}"

# Step 1: Unlock bootloader
echo -e "\n${BLD}PASO 1: Desbloquear Bootloader${NC}"
echo -e "${Y}1. Apaga el teléfono completamente${NC}"
echo -e "${Y}2. Mantén Volume- + Power para entrar Fastboot${NC}"
echo -e "${Y}3. Conecta el USB al Lenovo${NC}"
read -p "Presiona Enter cuando el teléfono esté en Fastboot..."

# Verify fastboot connection
if ! fastboot devices | grep -q "b104bc5f"; then
    echo -e "${R}ERROR: No se detecta el Redmi en fastboot${NC}"
    echo "Devices: $(fastboot devices)"
    exit 1
fi
echo -e "${G}Redmi detectado en fastboot${NC}"

# Run MiUnlockTool
log "Starting miunlock"
cd "$MIUNLOCK" && python3 run_miunlock3.py 2>&1 | tee -a "$LOG"

# Step 2: Install TWRP (after reboot)
echo -e "\n${BLD}PASO 2: Instalar TWRP${NC}"
echo -e "${Y}El teléfono se reiniciará. Espera a que arranque completamente.${NC}"
echo -e "${Y}Luego apaga y vuelve a entrar en Fastboot.${NC}"
read -p "Presiona Enter cuando estés listo para flashear TWRP..."

echo -e "${C}Importante: Necesitas descargar twrp-joyeuse.img manualmente${NC}"
echo -e "${C} desde https://dl.twrp.me/joyeuse/ o https://twrp.me/xiaomi/${NC}"
read -p "Ruta al TWRP .img: " TWRP_IMG
if [ -f "$TWRP_IMG" ]; then
    fastboot flash recovery "$TWRP_IMG"
    log "TWRP flashed from $TWRP_IMG"
    echo -e "${G}TWRP instalado${NC}"
else
    echo -e "${R}Archivo no encontrado: $TWRP_IMG${NC}"
    exit 1
fi

# Step 3: Boot to TWRP and install Magisk
echo -e "\n${BLD}PASO 3: Instalar Magisk (Root)${NC}"
echo -e "${Y}Mantén Volume+ al reiniciar para entrar en TWRP${NC}"
read -p "Presiona Enter cuando estés en TWRP..."

MAGISK_APK="$HDD/magisk/Magisk-v30.7.apk"
if [ -f "$MAGISK_APK" ]; then
    adb push "$MAGISK_APK" /sdcard/
    echo -e "${G}Magisk APK copiado al teléfono${NC}"
    echo -e "${C}En TWRP: Install -> Install ZIP -> selecciona Magisk-v30.7.apk${NC}"
else
    echo -e "${R}Magisk no encontrado en $MAGISK_APK${NC}"
fi

# Step 4: Full backup
echo -e "\n${BLD}PASO 4: Backup completo${NC}"
read -p "¿Hacer backup de datos en TWRP? (s/n): " DO_BACKUP
if [ "$DO_BACKUP" = "s" ]; then
    BACKUP_DEST="$HDD/backups/redmi-note9pro/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DEST"
    echo -e "${C}En TWRP: Backup -> selecciona Data, EFS, Boot, System -> Swipe${NC}"
    echo -e "${C}Backup se guardará en TWRP local. Después puedes copiarlo con adb pull.${NC}"
fi

echo -e "\n${G}${BLD}¡DES BLOQUEO COMPLETADO!${NC}"
echo -e "Siguientes pasos:"
echo -e "  1. Reinstalar 48 apps del Vivo"
echo -e "  2. Configurar Geode + Geometry Dash"
echo -e "  3. Restaurar datos de la nube Xiaomi"
log "Unlock workflow completed"
