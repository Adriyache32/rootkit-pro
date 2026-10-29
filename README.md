# rootkit-pro v2.1 🛡️

> **Universal Phone Root / Unlock Tool** para **Linux** y **Windows**. ADB/Fastboot, análisis de riesgo, backup, botón de pánico. UI GitHub Dark.

## ⚠️ ADVERTENCIA DE SEGURIDAD

**Solo para dispositivos propios.** El desbloqueo del bootloader:
- Borra **todos los datos** del dispositivo
- Anula la **garantía** del fabricante
- Puede dejar el dispositivo inutilizable (brick)
- **Úsalo bajo tu propia responsabilidad**

## ✨ Funciones

| Función | Marcas soportadas |
|---------|-------------------|
| Detección ADB/Fastboot | Todas |
| Unlock bootloader | Xiaomi, Google Pixel, OnePlus, Motorola, Nothing |
| EDL Mode (Emergency Download) | Xiaomi, Motorola |
| Samsung FRP bypass | Samsung (Exynos/Snapdragon) |
| Backup completo | Apps, fotos, SMS, contactos, ajustes |
| Análisis de riesgo | Puntuación 0-100 antes de cada operación |
| Botón de pánico | Detiene todo y restaura backup automático |
| UI Web (GitHub Dark) | Puerto 20229, responsive, móvil |

## 🚀 Inicio rápido

```bash
# Linux
git clone https://github.com/Adriyache32/rootkit-pro.git
cd rootkit-pro
chmod +x launcher.sh
./launcher.sh

# Windows
# Ejecuta backend/rootkit-pro.exe o usa portable/rootkit-pro.bat

# Docker
docker run -d -p 20229:20229 --privileged -v /dev/bus/usb:/dev/bus/usb adriyache32/rootkit-pro
```

## 📸 Demo

![rootkit-pro Demo](assets/demo.gif)

## 🔧 Configuración

```yaml
# config.yaml
adb_path: "adb"
fastboot_path: "fastboot"
api_port: 20229
backup_dir: "./backups"
risk_threshold: 70  # Auto-cancelar si riesgo > 70
auto_backup: true
panic_enabled: true
```

## 🏗️ Arquitectura

```
rootkit-pro/
├── launcher.sh              # Entry point Linux
├── backend/
│   ├── main.py             # FastAPI + WebSocket
│   ├── adb.py              # Wrapper ADB async
│   ├── fastboot.py         # Wrapper Fastboot
│   ├── unlock/             # Métodos por marca
│   │   ├── xiaomi.py
│   │   ├── pixel.py
│   │   ├── oneplus.py
│   │   └── ...
│   ├── risk.py             # Análisis de riesgo
│   ├── backup.py           # Backup/restauración
│   └── panic.py            # Botón de pánico
├── html/                   # UI Web (GitHub Dark)
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── packaging/
    ├── Dockerfile
    ├── rootkit-pro.spec    # PyInstaller
    └── InnoSetup.iss       # Windows installer
```

## 🤝 Contribuir

Ver [CONTRIBUTING.md](CONTRIBUTING.md) — **Lee SECURITY.md primero**

## 📄 Licencia

MIT — ver [LICENSE](LICENSE)

---

**Responsabilidad:** El autor no se hace responsable por daños a dispositivos.
