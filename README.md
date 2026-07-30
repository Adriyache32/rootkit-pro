# ROOT KIT PRO v2.1

Universal Phone Root / Unlock Tool — Works on **Linux** and **Windows**.

## Features

- Phone detection (ADB/Fastboot)
- Brand-specific unlock methods (Xiaomi, Samsung, Google, Motorola, OnePlus, Huawei, Apple)
- Risk analysis with scoring
- Full backup (apps, photos, SMS, settings)
- Emergency panic button
- HTML interface (GitHub Dark theme)
- Python API server (port 20229)

## Linux

```bash
# Quick start
rootkit-pro

# Or via API
python3 ~/.rootkit-pro/backend/api.py
# Open http://localhost:20229
```

## Windows

### Option 1: Installer
```cmd
cd windows
install.bat
```

### Option 2: Portable
```cmd
# Run the batch launcher
windows\ROOTKIT-PRO.bat

# Or PowerShell CLI
powershell -ExecutionPolicy Bypass -File windows\rootkit-pro.ps1
```

### Option 3: API Server
```cmd
python %USERPROFILE%\.rootkit-pro\backend\api.py
# Open http://localhost:20229 in browser
```

## Requirements

### Both platforms
- Python 3.8+
- ADB Platform Tools
- USB drivers for your phone
- USB Debugging enabled

### Windows
- USB drivers (OEM specific)
- Added `platform-tools` to PATH

### Linux
- `pacman -S android-tools` or download platform-tools

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/device` | Connected device info |
| `/api/methods?brand=Xiaomi` | Unlock methods |
| `/api/risk` | Risk analysis |
| `/api/apps` | List installed apps |
| `/api/backup` | Full device backup |
| `/api/panic` | Emergency disconnect |
| `/api/system` | Host system info |

## File Structure

```
~/.rootkit-pro/
├── html/index.html          # Web interface
├── backend/api.py           # API server (cross-platform)
├── windows/
│   ├── ROOTKIT-PRO.bat      # Windows launcher
│   ├── rootkit-pro.ps1      # PowerShell CLI
│   └── install.bat          # Windows installer
├── portable/
│   └── rootkit-pro-portable # Portable bash CLI
└── logs/
```

## License

MIT
