#!/usr/bin/env python3
"""ROOT KIT PRO v2.1 - Cross-Platform API Server (Multi-Device)"""
import http.server
import json
import subprocess
import os
import sys
import platform
import shutil
import socketserver, socket
import concurrent.futures

PORT = 20229
IS_WINDOWS = platform.system() == "Windows"
APP_DIR = os.path.join(os.path.expanduser("~"), ".rootkit-pro")

def find_adb():
    if IS_WINDOWS:
        paths = [
            os.path.join(os.environ.get("LOCALAPPDATA",""), "Android", "Sdk", "platform-tools", "adb.exe"),
            os.path.join(os.environ.get("PROGRAMFILES",""), "Android", "platform-tools", "adb.exe"),
            os.path.join(os.environ.get("ANDROID_HOME",""), "platform-tools", "adb.exe"),
            "C:\\platform-tools\\adb.exe",
        ]
        for p in paths:
            if os.path.isfile(p):
                return p
        found = shutil.which("adb.exe") or shutil.which("adb")
        return found or "adb"
    else:
        return shutil.which("adb") or "adb"

def find_fastboot():
    if IS_WINDOWS:
        paths = [
            os.path.join(os.environ.get("LOCALAPPDATA",""), "Android", "Sdk", "platform-tools", "fastboot.exe"),
            "C:\\platform-tools\\fastboot.exe",
        ]
        for p in paths:
            if os.path.isfile(p):
                return p
        found = shutil.which("fastboot.exe") or shutil.which("fastboot")
        return found or "fastboot"
    else:
        return shutil.which("fastboot") or "fastboot"

ADB = find_adb()
FASTBOOT = find_fastboot()

def run(cmd, timeout=8):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout,
                           creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0)
        return r.stdout.strip().replace('\r','')
    except Exception:
        return ""

def run_adb_serial(serial, cmd, timeout=8):
    return run(f'"{ADB}" -s {serial} {cmd}', timeout)

def get_device_info(serial):
    """Get full info for a single device by serial"""
    brand = run_adb_serial(serial, "shell getprop ro.product.brand")
    model = run_adb_serial(serial, "shell getprop ro.product.model")
    android = run_adb_serial(serial, "shell getprop ro.build.version.release")
    sdk = run_adb_serial(serial, "shell getprop ro.build.version.sdk")
    codename = run_adb_serial(serial, "shell getprop ro.product.device")
    cpu = run_adb_serial(serial, "shell getprop ro.product.cpu.abi")
    imei_raw = run_adb_serial(serial, "shell service call iphonesubinfo 1")
    imei_clean = ""
    for part in imei_raw.split("'"):
        part = part.strip()
        if part.isdigit() and len(part) > 3:
            imei_clean += part
    if len(imei_clean) < 13:
        imei_clean = run_adb_serial(serial, "shell settings get secure android_id")
    bl = run_adb_serial(serial, "shell getprop ro.boot.flash.locked")
    bootloader = "unlocked" if bl == "0" else "locked"
    rooted = run_adb_serial(serial, 'shell "su -c id 2>/dev/null | grep -c uid=0"') == "1"
    battery_raw = run_adb_serial(serial, "shell dumpsys battery")
    battery = ""
    for line in battery_raw.split('\n'):
        if 'level:' in line:
            battery = line.split(':')[-1].strip()
            break
    oem = run_adb_serial(serial, "shell settings get global oem_unlock_enabled")
    frp = run_adb_serial(serial, "shell getprop ro.frp.pst")
    dm = run_adb_serial(serial, "shell getprop ro.boot.verifiedbootstate")
    product = run_adb_serial(serial, "shell getprop ro.product.board")

    return {
        "connected": True, "serial": serial, "platform": platform.system(),
        "brand": brand, "model": model, "android": android, "sdk": sdk,
        "codename": codename, "cpu": cpu, "imei": imei_clean,
        "bootloader": bootloader, "rooted": rooted,
        "battery": battery, "oem_unlock": oem, "frp": frp, "dm_verify": dm,
        "product": product,
    }

def get_devices():
    """Detect ALL connected devices (ADB + Fastboot)"""
    devices_out = run(f'"{ADB}" devices')
    lines = [l for l in devices_out.split('\n') if '\tdevice' in l]

    # Also check fastboot
    fb_out = run(f'"{FASTBOOT}" devices')
    fb_lines = [l for l in fb_out.split('\n') if l.strip()]

    all_serials = []
    for l in lines:
        serial = l.split('\t')[0]
        all_serials.append({"serial": serial, "mode": "adb"})
    for l in fb_lines:
        serial = l.split()[0]
        all_serials.append({"serial": serial, "mode": "fastboot"})

    if not all_serials:
        return {"count": 0, "devices": [], "platform": platform.system()}

    # Parallel fetch for speed
    devices = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(all_serials), 8)) as ex:
        futures = {}
        for entry in all_serials:
            if entry["mode"] == "adb":
                futures[ex.submit(get_device_info, entry["serial"])] = entry
        for f in concurrent.futures.as_completed(futures):
            try:
                devices.append(f.result())
            except Exception:
                pass

    # Fastboot devices (less info)
    for entry in all_serials:
        if entry["mode"] == "fastboot":
            serial = entry["serial"]
            product = run(f'"{FASTBOOT}" -s {serial} getvar product 2>&1')
            product_name = ""
            for line in product.split('\n'):
                if 'product:' in line:
                    product_name = line.split(':')[-1].strip()
                    break
            bl_info = run(f'"{FASTBOOT}" -s {serial} oem device-info 2>&1')
            bl = "locked"
            if "unlocked" in bl_info.lower() and "true" in bl_info.lower():
                bl = "unlocked"
            devices.append({
                "connected": True, "serial": serial, "platform": platform.system(),
                "brand": product_name, "model": product_name, "android": "N/A",
                "sdk": "N/A", "codename": product_name, "cpu": "N/A", "imei": "N/A",
                "bootloader": bl, "rooted": False, "battery": "",
                "oem_unlock": "", "frp": "", "dm_verify": "", "product": product_name,
                "mode": "fastboot",
            })

    return {"count": len(devices), "devices": devices, "platform": platform.system()}

def get_device_by_serial(serial):
    """Get info for a specific device"""
    devices_data = get_devices()
    for d in devices_data["devices"]:
        if d["serial"] == serial:
            return d
    return {"connected": False, "serial": serial}

def get_methods(brand):
    brand = brand.lower()
    methods_db = {
        "xiaomi": [
            {"name":"Mi Unlock (official)","tool":"xiaomi_mi_unlock","success":65,"url":"https://en.miui.com/unlock/download_en.html",
             "steps":["1. Download Mi Unlock from en.miui.com/unlock",
                      "2. Bind Xiaomi account to device (Settings > Mi Account)",
                      "3. Wait 168h (7 days) after binding",
                      "4. Boot to fastboot: hold VolDown+Power",
                      "5. Open Mi Unlock tool, log in, follow prompts",
                      "6. Unlock will wipe all data - backup first"]},
            {"name":"EDL Firehose (qualcomm)","tool":"edl_firehose","success":40,"cmd":"",
             "steps":["1. Install Qualcomm drivers (EDL mode)",
                      "2. Open phone back case, find EDL testpoint",
                      "3. Short testpoint to ground and connect USB",
                      "4. Device shows as 'Qualcomm HS-USB QDLoader 9008'",
                      "5. Use QFIL/QPST to flash firehose programmer",
                      "6. Flash unlock bootloader via firehose loader"]},
            {"name":"Direct bootloader","tool":"direct_unlock","success":55,"cmd":"fastboot flashing unlock",
             "steps":["1. Enable Developer Options",
                      "2. Enable OEM Unlock + USB Debugging",
                      "3. Reboot to fastboot: adb reboot bootloader",
                      "4. Run: fastboot flashing unlock",
                      "5. Confirm on phone screen with volume keys",
                      "6. Run: fastboot reboot"]},
        ],
        "redmi": [
            {"name":"Mi Unlock (official)","tool":"xiaomi_mi_unlock","success":65,"url":"https://en.miui.com/unlock/download_en.html",
             "steps":["1. Download Mi Unlock from en.miui.com/unlock",
                      "2. Bind Xiaomi account (Settings > Mi Account)",
                      "3. Wait 168h after binding",
                      "4. Boot to fastboot (VolDown+Power)",
                      "5. Open Mi Unlock tool, log in, follow prompts",
                      "6. Backup data first - unlock wipes everything"]},
            {"name":"EDL Firehose (qualcomm)","tool":"edl_firehose","success":40,
             "steps":["1. Install Qualcomm drivers",
                      "2. Short EDL testpoint on motherboard",
                      "3. Connect USB - device shows as 9008",
                      "4. Use QFIL/QPST with firehose programmer",
                      "5. Flash unlock bootloader partition"]},
            {"name":"Direct bootloader","tool":"direct_unlock","success":55,"cmd":"fastboot flashing unlock",
             "steps":["1. Enable OEM Unlock in Developer Options",
                      "2. Reboot to fastboot: adb reboot bootloader",
                      "3. Run: fastboot flashing unlock",
                      "4. Confirm on phone with volume keys",
                      "5. Run: fastboot reboot",
                      "6. After reboot, run: fastboot flashing get_unlock_ability"]},
        ],
        "motorola": [
            {"name":"Motorola unlock (official)","tool":"motola_official","success":50,"url":"https://motorola.com/unlockbootloader",
             "steps":["1. Go to motorola.com/unlockbootloader",
                      "2. Create account and request unlock code",
                      "3. Wait for email with unlock code (24-48h)",
                      "4. Boot to fastboot: adb reboot bootloader",
                      "5. Run: fastboot oem get_unlock_data",
                      "6. Copy the unlock data to website, get code",
                      "7. Run: fastboot oem unlock UNLOCK_CODE"]},
            {"name":"Fastboot OEM","tool":"fastboot_oem","success":45,"cmd":"fastboot oem unlock",
             "steps":["1. Enable OEM Unlock in Developer Options",
                      "2. Check if 'oem unlock' is available",
                      "3. Reboot to fastboot: adb reboot bootloader",
                      "4. Run: fastboot oem unlock",
                      "5. Confirm on phone screen",
                      "6. Run: fastboot reboot"]},
            {"name":"EDL/QFIL","tool":"edl_qfil","success":35,
             "steps":["1. Install Qualcomm USB drivers",
                      "2. Open phone and find EDL testpoint",
                      "3. Short the contact and connect USB",
                      "4. Device shows as QDLoader 9008 in Device Manager",
                      "5. Use QFIL to flash blank-flash or firehose",
                      "6. Flash signed bootloader unlock image"]},
        ],
        "samsung": [
            {"name":"OEM Unlock (settings)","tool":"samsung_oem","success":70,"cmd":"",
             "steps":["1. Go to Settings > About Phone > Software Info",
                      "2. Tap Build Number 7 times (Developer Mode)",
                      "3. Go to Developer Options > OEM Unlock > Enable",
                      "4. Power off, connect USB cable to PC",
                      "5. Hold VolUp+VolDown and connect cable (Download Mode)",
                      "6. Press VolUp to confirm unlock",
                      "7. Device will wipe and reboot - unlock confirmed"]},
            {"name":"Heimdall (ODIN alternative)","tool":"heimdall","success":55,"cmd":"heimdall flash",
             "steps":["1. Install heimdall: sudo apt install heimdall-flasher",
                      "2. Boot to Download Mode (VolUp+VolDown+USB)",
                      "3. Run: heimdall print-pit (lists partitions)",
                      "4. Download stock firmware for your model",
                      "5. Run: heimdall flash --AP firmware.tar --no-reboot",
                      "6. Flash custom recovery: heimdall flash --RECOVERY twrp.img"]},
            {"name":"Download Mode + Odin","tool":"odin_mode","success":45,
             "steps":["1. Download Odin3 tool on Windows PC",
                      "2. Download TWRP .tar for your Samsung model",
                      "3. Boot to Download Mode (VolUp+VolDown+USB)",
                      "4. Open Odin, click AP and select TWRP .tar",
                      "5. Make sure 'Auto Reboot' is UNCHECKED",
                      "6. Click Start, wait for PASS!",
                      "7. Force reboot to recovery: VolUp+Power+Home"]},
        ],
        "google": [
            {"name":"Fastboot flashing unlock","tool":"pixel_unlock","success":80,"cmd":"fastboot flashing unlock",
             "steps":["1. Enable Developer Options + OEM Unlock",
                      "2. Reboot to bootloader: adb reboot bootloader",
                      "3. Run: fastboot flashing unlock",
                      "4. Use volume keys to confirm, press power",
                      "5. Run: fastboot reboot",
                      "6. Done - bootloader is unlocked"]},
            {"name":"Android Flash Tool","tool":"flash_tool","success":75,"url":"https://flash.android.com",
             "steps":["1. Enable USB Debugging",
                      "2. Open flash.android.com in Chrome/Edge",
                      "3. Connect device, click 'Add new device'",
                      "4. Select your device model from list",
                      "5. Select 'Force flash' + 'Unlock bootloader'",
                      "6. Click Install and wait for completion"]},
        ],
        "oneplus": [
            {"name":"Fastboot unlock","tool":"oneplus_unlock","success":75,"cmd":"fastboot oem unlock",
             "steps":["1. Enable Developer Options > OEM Unlock",
                      "2. Go to Settings > About > Build Number (tap 7x)",
                      "3. Reboot to fastboot: adb reboot bootloader",
                      "4. Run: fastboot oem unlock",
                      "5. Confirm with volume keys on screen",
                      "6. Run: fastboot reboot"]},
            {"name":"MSM Download Tool","tool":"msm_tool","success":50,
             "steps":["1. Download MSM Download Tool for your OnePlus model",
                      "2. Install Qualcomm USB drivers",
                      "3. Boot to EDL mode: hold VolUp+VolDown, connect USB",
                      "4. Open MSM Tool, select correct firmware",
                      "5. Click Start and wait for process to complete",
                      "6. Device will reboot - bootloader may stay locked"]},
        ],
        "huawei": [
            {"name":"EMUI unlock (official)","tool":"huawei_emui","success":35,"url":"https://consumer.huawei.com/en/flash/unlock",
             "steps":["1. Request unlock code from EMUI website",
                      "2. Wait for email with 16-digit unlock code",
                      "3. Insert non-verizon SIM card",
                      "4. Boot to fastboot: adb reboot bootloader",
                      "5. Run: fastboot oem unlock UNLOCK_CODE",
                      "6. Device will wipe data and reboot"]},
            {"name":"Fastboot oem","tool":"fastboot_huawei","success":30,"cmd":"fastboot oem unlock",
             "steps":["1. Enable Developer > OEM Unlock",
                      "2. Reboot to fastboot: adb reboot bootloader",
                      "3. Try: fastboot oem unlock",
                      "4. If fails, get unlock code from Huawei",
                      "5. Run: fastboot oem unlock CODE_HERE",
                      "6. Device reboots - bootloader unlocked"]},
        ],
        "apple": [
            {"name":"checkra1n","tool":"checkrain","success":60,"url":"https://checkra.in",
             "steps":["1. Download checkra1n from checkra.in",
                      "2. Connect iPhone/iPad to Mac/Linux",
                      "3. Open checkra1n and click 'Start'",
                      "4. Put device in DFU mode (follow on-screen)",
                      "5. Wait for jailbreak to complete",
                      "6. Install Cydia/Sileo from checkra1n"]},
            {"name":"palera1n","tool":"palera1n","success":55,"url":"https://palera.in",
             "steps":["1. Download palera1n from palera.in",
                      "2. Connect device and put in DFU mode",
                      "3. Run palera1n on Mac/Linux",
                      "4. Select 'Create FakeFS' option",
                      "5. Wait for jailbreak process (~5 min)",
                      "6. Sileo will be installed on springboard"]},
        ],
    }
    for k in methods_db:
        if k in brand:
            return methods_db[k]
    return [{"name":"Fastboot OEM","tool":"fastboot_oem","success":30,"cmd":"fastboot oem unlock",
             "steps":["1. Enter fastboot mode on device",
                      "2. Run: fastboot oem unlock",
                      "3. Confirm on device screen",
                      "4. Run: fastboot reboot"]}]

def get_risk(device):
    score = 0
    risks = []
    bat = device.get("battery","")
    if bat and bat.isdigit():
        b = int(bat)
        if b < 30:
            risks.append({"level":"critical","msg":f"Battery LOW ({b}%) - Minimum 30%"})
            score += 30
        elif b < 50:
            risks.append({"level":"warning","msg":f"Battery MEDIUM ({b}%) - Recommended 50%+"})
            score += 10
    if device.get("oem_unlock") == "0":
        risks.append({"level":"critical","msg":"OEM Unlock DISABLED"})
        score += 25
    elif device.get("oem_unlock") in ("null",""):
        risks.append({"level":"warning","msg":"OEM Unlock - verify in Developer Options"})
        score += 5
    if device.get("frp"):
        risks.append({"level":"warning","msg":"FRP active - Factory reset required"})
        score += 15
    if device.get("bootloader") == "locked":
        risks.append({"level":"warning","msg":"Bootloader LOCKED - Requires unlock tool"})
        score += 15
    if device.get("dm_verify") == "verified":
        risks.append({"level":"info","msg":"DM-Verity active"})
        score += 10
    level = "low" if score < 25 else "medium" if score < 50 else "high"
    return {"score": score, "risks": risks, "level": level}

def get_apps(serial=None):
    if serial:
        output = run_adb_serial(serial, "shell pm list packages -3")
    else:
        output = run(f'"{ADB}" shell pm list packages -3')
    return [l.replace("package:","") for l in output.split('\n') if l.strip()]

def do_backup(serial=None):
    import datetime
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if IS_WINDOWS:
        backup_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "ROOTKIT-Backups", ts)
    else:
        backup_dir = os.path.join(os.path.expanduser("~"), "HDD-Backups", "rootkit-backups", ts)
    for d in ["apps","contacts","photos","files","sms","settings","system"]:
        os.makedirs(os.path.join(backup_dir, d), exist_ok=True)
    adb_cmd = f'"{ADB}" -s {serial}' if serial else f'"{ADB}"'
    run(f'{adb_cmd} shell pm list packages -3 > "{os.path.join(backup_dir,"apps","packages.txt")}"')
    run(f'{adb_cmd} shell settings list system > "{os.path.join(backup_dir,"settings","system.txt")}"')
    run(f'{adb_cmd} shell settings list secure > "{os.path.join(backup_dir,"settings","secure.txt")}"')
    run(f'{adb_cmd} shell settings list global > "{os.path.join(backup_dir,"settings","global.txt")}"')
    run(f'{adb_cmd} shell getprop > "{os.path.join(backup_dir,"system","properties.txt")}"')
    run(f'{adb_cmd} shell content query --uri content://sms/ > "{os.path.join(backup_dir,"sms","sms.txt")}"')
    run(f'{adb_cmd} pull /sdcard/DCIM/ "{os.path.join(backup_dir,"photos")}"')
    run(f'{adb_cmd} pull /sdcard/Download/ "{os.path.join(backup_dir,"files")}"')
    return {"status":"ok","path":backup_dir}

def do_panic(serial=None):
    if serial:
        run(f'"{ADB}" -s {serial} kill-server')
    else:
        run(f'"{ADB}" kill-server')
    run(f'"{FASTBOOT}" reboot')
    return {"status":"ok"}

def do_execute(tool_name, serial=None):
    """Execute an unlock method automatically"""
    adb_cmd = f'"{ADB}" -s {serial}' if serial else f'"{ADB}"'
    adb_shell = f'{adb_cmd} shell'

    exec_map = {
        "xiaomi_mi_unlock": {"status":"manual","msg":"Mi Unlock requires GUI tool. Download from en.miui.com/unlock"},
        "direct_unlock": {"status":"running","cmd":"fastboot flashing unlock"},
        "fastboot_oem": {"status":"running","cmd":"fastboot oem unlock"},
        "pixel_unlock": {"status":"running","cmd":"fastboot flashing unlock"},
        "oneplus_unlock": {"status":"running","cmd":"fastboot oem unlock"},
        "motola_official": {"status":"manual","msg":"Motorola needs unlock code from motorola.com/unlockbootloader"},
        "fastboot_huawei": {"status":"running","cmd":"fastboot oem unlock"},
        "samsung_oem": {"status":"manual","msg":"Enable OEM Unlock manually in Settings > Developer Options"},
        "heimdall": {"status":"manual","msg":"Use Heimdall CLI: heimdall print-pit / heimdall flash"},
        "odin_mode": {"status":"manual","msg":"Use Odin3 on Windows - requires GUI tool"},
        "checkrain": {"status":"manual","msg":"Use checkra1n GUI from checkra.in"},
        "palera1n": {"status":"manual","msg":"Use palera1n CLI/ GUI from palera.in"},
        "edl_firehose": {"status":"manual","msg":"EDL requires QFIL/QPST GUI tool and hardware testpoint"},
        "edl_qfil": {"status":"manual","msg":"EDL requires QFIL/QPST GUI tool and hardware testpoint"},
        "msm_tool": {"status":"manual","msg":"MSM Download Tool requires Windows GUI"},
        "flash_tool": {"status":"manual","msg":"Use Android Flash Tool at flash.android.com in browser"},
        "huawei_emui": {"status":"manual","msg":"Get unlock code from Huawei first, then run fastboot oem unlock CODE"},
    }

    if tool_name in exec_map:
        info = exec_map[tool_name]
        if info["status"] == "running":
            cmd = info["cmd"]
            result = run(f'{cmd} 2>&1')
            return {"status":"done","tool":tool_name,"command":cmd,"output":result}
        else:
            return info
    return {"status":"error","msg":f"Unknown tool: {tool_name}"}

def get_system_info():
    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "adb": ADB,
        "fastboot": FASTBOOT,
    }
def get_usb_devices():
    """Detect ALL USB devices (not just ADB) - audio, storage, HID, etc"""
    devices = []
    
    # Try lsusb (Linux)
    lsusb_out = run("lsusb 2>/dev/null")
    if lsusb_out:
        for line in lsusb_out.split('\n'):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 6:
                bus = parts[1] if len(parts) > 1 else ""
                dev = parts[3].rstrip(':') if len(parts) > 3 else ""
                vid_pid = parts[5] if len(parts) > 5 else ""
                vendor_product = ' '.join(parts[6:]) if len(parts) > 6 else ""
                vid, pid = "", ""
                if ':' in vid_pid:
                    vid, pid = vid_pid.split(':')
                devices.append({
                    "bus": bus, "device": dev, "vid": vid, "pid": pid,
                    "description": vendor_product, "type": classify_usb(vendor_product, vid, pid),
                })

    # Try lsusb -t for speed/type info
    lsusb_t = run("lsusb -t 2>/dev/null")
    if lsusb_t:
        for line in lsusb_t.split('\n'):
            if 'Full speed' in line or 'High speed' in line or 'Super speed' in line:
                pass

    # Fallback: parse /sys/bus/usb/devices
    if not devices:
        sys_usb = run("ls /sys/bus/usb/devices/ 2>/dev/null | head -30")
        if sys_usb:
            for d in sys_usb.split('\n'):
                if not d.strip():
                    continue
                product = run(f"cat /sys/bus/usb/devices/{d}/product 2>/dev/null")
                manufacturer = run(f"cat /sys/bus/usb/devices/{d}/manufacturer 2>/dev/null")
                speed = run(f"cat /sys/bus/usb/devices/{d}/speed 2>/dev/null")
                desc = f"{manufacturer} {product}".strip()
                devices.append({
                    "sys_name": d, "description": desc or "Unknown",
                    "speed": speed, "type": classify_usb(desc, "", ""),
                })
    
    return devices

def classify_usb(desc, vid, pid):
    """Classify USB device type by description or VID/PID"""
    d = desc.lower()
    if "charg" in d or "power" in d or "battery" in d:
        return "charger"
    if "audio" in d or "headphone" in d or "headset" in d or "speaker" in d or "microphon" in d or "sound" in d:
        return "audio"
    if "hub" in d or "root_hub" in d:
        return "hub"
    if "keyboard" in d or "keypad" in d:
        return "keyboard"
    if "mouse" in d or "pointer" in d:
        return "mouse"
    if "storage" in d or "flash" in d or "disk" in d or "drive" in d or "mass" in d or "sd" in d:
        return "storage"
    if "camera" in d or "webcam" in d or "video" in d:
        return "camera"
    if "bluetooth" in d or "bt" in d:
        return "bluetooth"
    if "wifi" in d or "wireless" in d or "network" in d or "ether" in d:
        return "network"
    if "printer" in d or "scanner" in d:
        return "printer"
    if "phone" in d or "android" in d or "adb" in d or "fastboot" in d or "qualcomm" in d or "mtp" in d:
        return "phone"
    if "game" in d or "control" in d or "joystick" in d or "xbox" in d or "playstation" in d:
        return "controller"
    if "card" in d or "reader" in d:
        return "card_reader"
    if "composite" in d:
        return "composite"
    if "nvidia" in d.lower() or "display" in d.lower() or "monitor" in d.lower():
        return "display"
    # Check vid/pid
    known_chips = {
        "8087": "intel_bluetooth", "0bda": "realtek_card_reader",
        "058f": "alcor_card_reader", "05e3": "genesys_hub",
    }
    for k, v in known_chips.items():
        if vid.lower() == k:
            return v
    return "other"

# ===== DEVICE DETAILS (RAM, Storage, Cooldown) =====
def get_device_details(serial=None):
    """Get detailed device info: RAM, storage, battery health, unlock cooldown"""
    adb_cmd = f'"{ADB}" -s {serial}' if serial else f'"{ADB}"'
    adb_shell = f'{adb_cmd} shell'
    details = {"serial": serial or "unknown"}

    # RAM
    meminfo = run(f'{adb_shell} cat /proc/meminfo 2>/dev/null')
    for line in meminfo.split('\n'):
        if 'MemTotal' in line:
            kb = line.split(':')[1].strip().replace(' kB','')
            details["ram_total_kb"] = kb
            details["ram_total_gb"] = round(int(kb) / 1048576, 2)
        if 'MemAvailable' in line:
            kb = line.split(':')[1].strip().replace(' kB','')
            details["ram_avail_kb"] = kb
            details["ram_avail_gb"] = round(int(kb) / 1048576, 2)

    # Storage
    df_out = run(f'{adb_shell} df /sdcard 2>/dev/null')
    for line in df_out.split('\n'):
        if '/sdcard' in line or '/data' in line:
            parts = line.split()
            if len(parts) >= 4:
                try:
                    details["storage_total"] = parts[1] if len(parts) > 1 else ""
                    details["storage_used"] = parts[2] if len(parts) > 2 else ""
                    details["storage_avail"] = parts[3] if len(parts) > 3 else ""
                    # Also in GB
                    details["storage_avail_gb"] = round(int(parts[3]) / 1048576, 2) if parts[3].isdigit() else 0
                except: pass

    # Battery health / temp
    bat_out = run(f'{adb_shell} dumpsys battery 2>/dev/null')
    for line in bat_out.split('\n'):
        if 'temperature' in line:
            try: details["battery_temp"] = int(line.split(':')[1].strip()) / 10
            except: pass
        if 'voltage' in line:
            try: details["battery_voltage"] = int(line.split(':')[1].strip()) / 1000
            except: pass
        if 'technology' in line:
            details["battery_type"] = line.split(':')[1].strip()

    # Unlock cooldown for Xiaomi/Redmi
    brand = run(f'{adb_shell} getprop ro.product.brand 2>/dev/null').lower()
    if 'xiaomi' in brand or 'redmi' in brand or 'poco' in brand:
        # Check various methods for remaining time
        mi_account = run(f'{adb_shell} getprop ro.miui.ui.version.code 2>/dev/null')
        # Try to get unlock status from Xiaomi specific props
        unlock_status = run(f'{adb_shell} getprop persist.sys.allow_unlock 2>/dev/null')
        bind_time = run(f'{adb_shell} settings get global mi_unlock_bind_time 2>/dev/null')

        import time
        now = int(time.time())
        cooldown_hours = 168  # Default 7 days

        if bind_time and bind_time.isdigit():
            bt = int(bind_time)
            elapsed = now - bt
            remaining = max(0, cooldown_hours * 3600 - elapsed)
            remaining_hours = remaining / 3600
            remaining_days = remaining_hours / 24

            details["unlock"] = {
                "status": "unlockable" if remaining <= 0 else "cooldown",
                "bound_timestamp": bt,
                "bound_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(bt)) if bt > 0 else "N/A",
                "cooldown_hours": cooldown_hours,
                "remaining_seconds": remaining,
                "remaining_hours": round(remaining_hours, 1),
                "remaining_days": round(remaining_days, 1),
                "remaining_text": "Ready to unlock!" if remaining <= 0 else f"{int(remaining_hours)}h {int((remaining_hours%1)*60)}m remaining ({round(remaining_days,1)} days)",
                "progress_pct": round((1 - remaining / (cooldown_hours*3600)) * 100, 1) if remaining > 0 else 100,
            }
        elif unlock_status:
            details["unlock"] = {"status": "checking", "bind_time": "unknown", "remaining_text": "Check Mi Account binding status"}
        else:
            details["unlock"] = {"status": "unknown", "remaining_text": "Bind Xiaomi account first (Settings > Mi Account)"}

    # CPU info
    cpuinfo = run(f'{adb_shell} cat /proc/cpuinfo 2>/dev/null')
    cores = 0
    for line in cpuinfo.split('\n'):
        if 'processor' in line:
            cores += 1
    if cores:
        details["cpu_cores"] = cores

    # Screen
    screen = run(f'{adb_shell} wm size 2>/dev/null')
    if 'Physical size' in screen or 'Override size' in screen:
        details["screen"] = screen.split(':')[-1].strip()
    density = run(f'{adb_shell} wm density 2>/dev/null')
    if 'Physical density' in density or 'Override density' in density:
        details["screen_density"] = density.split(':')[-1].strip()

    # Android security patch
    sec_patch = run(f'{adb_shell} getprop ro.build.version.security_patch 2>/dev/null')
    if sec_patch:
        details["security_patch"] = sec_patch

    # Build fingerprint
    fp = run(f'{adb_shell} getprop ro.build.fingerprint 2>/dev/null')
    if fp:
        details["fingerprint"] = fp[:80]

    return details

# ===== ACTIONS (Fastboot, Recovery, Shizuku, Dhizuku) =====
def do_action(action, serial=None):
    """Execute device actions: fastboot, recovery, shizuku, dhizuku"""
    adb_cmd = f'"{ADB}" -s {serial}' if serial else f'"{ADB}"'
    adb_shell = f'{adb_cmd} shell'

    if action == "fastboot":
        run(f'{adb_cmd} reboot bootloader')
        return {"status":"ok","action":"fastboot","msg":"Rebooting to fastboot..."}
    elif action == "recovery":
        run(f'{adb_cmd} reboot recovery')
        return {"status":"ok","action":"recovery","msg":"Rebooting to recovery..."}
    elif action == "shizuku":
        # Start Shizuku via ADB
        r = run(f'{adb_shell} sh /data/data/moe.shizuku.privileged.api/files/start.sh 2>/dev/null')
        if not r:
            r = run(f'{adb_shell} pm grant moe.shizuku.privileged.api android.permission.INTERACT_ACROSS_USERS_FULL 2>/dev/null')
            r2 = run(f'{adb_shell} sh /data/data/moe.shizuku.privileged.api/files/start.sh 2>/dev/null')
            if not r2:
                return {"status":"manual","action":"shizuku","msg":"Shizuku not installed. Install from Play Store, then use 'adb shell sh /data/data/moe.shizuku.privileged.api/files/start.sh'"}
        return {"status":"ok","action":"shizuku","msg":"Shizuku started via ADB!","output":r}
    elif action == "dhizuku":
        r = run(f'{adb_shell} am start -n com.rosan.dhizuku/.server.DhizukuDaemon 2>/dev/null')
        if not r:
            r = run(f'{adb_shell} pm grant com.rosan.dhizuku android.permission.INTERACT_ACROSS_USERS_FULL 2>/dev/null')
            r2 = run(f'{adb_shell} am start -n com.rosan.dhizuku/.server.DhizukuDaemon 2>/dev/null')
            if not r2:
                return {"status":"manual","action":"dhizuku","msg":"Dhizuku not installed. Install from GitHub, then use 'adb shell am start -n com.rosan.dhizuku/.server.DhizukuDaemon'"}
        return {"status":"ok","action":"dhizuku","msg":"Dhizuku started!","output":r}
    elif action == "sideload":
        return {"status":"manual","action":"sideload","msg":"Use: adb sideload <file.zip> from recovery mode"}
    elif action == "edl":
        run(f'{adb_cmd} reboot edl 2>/dev/null')
        return {"status":"ok","action":"edl","msg":"Rebooting to EDL mode..."}
    elif action == "soft-reboot":
        run(f'{adb_shell} pkill system_server 2>/dev/null')
        return {"status":"ok","action":"soft-reboot","msg":"Soft rebooting (system_server killed)..."}
    elif action == "screenshot":
        ts = run("date +%Y%m%d_%H%M%S")
        path = f"/sdcard/screenshot_{ts}.png"
        run(f'{adb_shell} screencap -p {path} 2>/dev/null')
        return {"status":"ok","action":"screenshot","msg":f"Screenshot saved to {path}"}
    elif action == "screenrecord":
        return {"status":"manual","action":"screenrecord","msg":"Use: adb shell screenrecord /sdcard/record.mp4"}
    return {"status":"error","msg":f"Unknown action: {action}"}

# ===== DEVICE OPTIMIZATION =====
def get_optimization(serial=None):
    """Analyze device and return optimization suggestions"""
    adb_cmd = f'"{ADB}" -s {serial}' if serial else f'"{ADB}"'
    adb_shell = f'{adb_cmd} shell'
    tips = []
    score = 100

    # 1. Cache size
    cache = run(f'{adb_shell} du -sh /data/dalvik-cache 2>/dev/null | cut -f1')
    if cache:
        tips.append({"icon":"🗑️","type":"cache","msg":f"Dalvik cache: {cache}", "action": "wipe_cache", "cmd": "adb shell rm -rf /data/dalvik-cache/*"})
        tips.append({"icon":"🗑️","type":"cache","msg":f"Cache partition: {run(f'{adb_shell} du -sh /cache 2>/dev/null | cut -f1') or '?'}", "action": "wipe_cache"})

    # 2. Unused apps (user installed, check last used time)
    pkgs = run(f'{adb_shell} pm list packages -3 2>/dev/null')
    if pkgs:
        user_apps = [p.replace('package:','').strip() for p in pkgs.split('\n') if p.strip()]
        unused = []
        for pkg in user_apps[:20]:  # Check first 20
            last = run(f'{adb_shell} dumpsys package {pkg} 2>/dev/null | grep "lastUsageTime" | head -1')
            if last and '0' not in last.split('=')[-1].strip():
                unused.append(pkg)
        if len(unused) > 5:
            tips.append({"icon":"📱","type":"apps","msg":f"{len(unused)} apps possibly unused. Check and uninstall.", "action": "list_unused"})
            score -= 10

    # 3. System app updates available
    sys_pkgs = run(f'{adb_shell} pm list packages -s 2>/dev/null')
    if sys_pkgs:
        sys_apps = [p.replace('package:','').strip() for p in sys_pkgs.split('\n') if p.strip()]
        updates_avail = 0
        for pkg in sys_apps[:30]:
            ver = run(f'{adb_shell} dumpsys package {pkg} 2>/dev/null | grep "versionName" | head -1')
            upd = run(f'{adb_shell} dumpsys package {pkg} 2>/dev/null | grep "updateAvailable" | head -1')
            if upd and 'true' in upd.lower():
                updates_avail += 1
        if updates_avail > 0:
            tips.append({"icon":"📦","type":"updates","msg":f"{updates_avail} system apps have updates available", "action": "update_apps"})
            score -= 5

    # 4. Battery optimization check
    bat_opt = run(f'{adb_shell} dumpsys deviceidle 2>/dev/null | grep "mState=" | head -1')
    if bat_opt:
        state = bat_opt.split('=')[-1].strip()
        if state != 'ACTIVE':
            tips.append({"icon":"🔋","type":"battery","msg":f"Battery optimization mode: {state}", "action": "battery_opt"})

    # 5. Old APK files
    apks = run(f'{adb_shell} find /sdcard -name "*.apk" -type f 2>/dev/null | wc -l')
    if apks and int(apks) > 0:
        tips.append({"icon":"📦","type":"apk","msg":f"{apks.strip()} APK files found on storage", "action": "list_apks"})

    # 6. Screen timeout
    timeout = run(f'{adb_shell} settings get system screen_off_timeout 2>/dev/null')
    if timeout and timeout.isdigit():
        mins = int(timeout) / 60000
        if mins > 5:
            tips.append({"icon":"🖥️","type":"screen","msg":f"Screen timeout: {int(mins)}min (consider reducing to save battery)"})

    # 7. Animations enabled
    anim_scale = run(f'{adb_shell} settings get global window_animation_scale 2>/dev/null')
    if anim_scale and float(anim_scale) > 0:
        tips.append({"icon":"🎬","type":"animations","msg":f"Animations scale: {anim_scale}x", "action": "disable_anim"})

    # 8. Bluetooth on
    bt = run(f'{adb_shell} settings get global bluetooth_on 2>/dev/null')
    if bt and bt.strip() == '1':
        tips.append({"icon":"🔵","type":"bluetooth","msg":"Bluetooth is ON (turn off when not in use to save battery)"})

    # 9. App optimization suggestions
    tips.append({"icon":"⚡","type":"performance","msg":"Enable developer options > Force GPU rendering for smoother UI"})
    tips.append({"icon":"💾","type":"storage","msg":"Move photos/videos to PC or cloud periodically"})

    level = "good" if score >= 85 else ("fair" if score >= 60 else "poor")
    return {"score": score, "level": level, "tips": tips}

# ===== RECOVERY INFO =====
def get_recovery_info(serial=None):
    """Check recovery status and TWRP installation"""
    adb_cmd = f'"{ADB}" -s {serial}' if serial else f'"{ADB}"'
    adb_shell = f'{adb_cmd} shell'

    # Check if device is in fastboot
    is_fastboot = serial and 'fastboot' in serial.lower()

    result = {
        "mode": "unknown",
        "recovery": "stock",
        "twrp_version": None,
        "has_recovery": False,
        "features": []
    }

    if is_fastboot:
        result["mode"] = "fastboot"
        # Check fastboot vars
        vars_out = run(f'"{ADB}" getvar all 2>/dev/null | grep -i "recovery\\|twrp\\|product\\|version"')
        if 'twrp' in vars_out.lower():
            result["recovery"] = "twrp"
            result["has_recovery"] = True
        result["features"] = ["flash_recovery", "flash_boot", "erase_data"]
        return result

    # Check running mode
    mode = run(f'{adb_shell} getprop ro.bootmode 2>/dev/null').strip()
    result["mode"] = mode or "android"

    # Check if TWRP is installed
    # Method 1: Check recovery block
    recovery_dev = run(f'{adb_shell} ls -la /dev/block/by-name/recovery 2>/dev/null')
    if recovery_dev:
        result["has_recovery"] = True
        result["features"].append("custom_recovery")

    # Method 2: Check for TWRP files
    twrp_files = run(f'{adb_shell} ls /data/media/0/TWRP 2>/dev/null')
    if twrp_files:
        result["recovery"] = "twrp"
        # Get TWRP version
        twrp_ver = run(f'{adb_shell} cat /data/media/0/TWRP/.twrps 2>/dev/null | grep version')
        if twrp_ver:
            result["twrp_version"] = twrp_ver.strip()
        result["features"].extend(["twrp_backup", "twrp_restore", "twrp_install_zip"])
    else:
        # Check for OrangeFox
        ofox = run(f'{adb_shell} ls /data/media/0/Fox 2>/dev/null')
        if ofox:
            result["recovery"] = "orangefox"
            result["features"].extend(["ofox_backup", "ofox_restore"])
        else:
            # Check for PBRP
            pbrp = run(f'{adb_shell} ls /data/media/0/PBRP 2>/dev/null')
            if pbrp:
                result["recovery"] = "pbrp"

    # Check bootloader status
    bl = run(f'{adb_shell} getprop ro.boot.flash.locked 2>/dev/null').strip()
    if bl == '0':
        result["features"].append("bootloader_unlocked")
    elif bl == '1':
        result["features"].append("bootloader_locked")

    # Available actions
    result["features"].extend(["reboot_recovery", "reboot_bootloader", "sideload"])

    return result

# ===== PREMIUM SYSTEM =====
PREMIUM_KEYS = {
    "ROOTKIT-PREMIUM-2026-MONTHLY": {"tier":"monthly","expires": 365*24*3600, "price":3},
    "ROOTKIT-PREMIUM-2026-YEARLY": {"tier":"yearly","expires": 365*24*3600*12, "price":30},
    "ROOTKIT-PREMIUM-2026-LIFETIME": {"tier":"lifetime","expires": -1, "price":60},
}

# Secret premium keys for users
def generate_premium_key(tier="monthly"):
    """Generate a premium key for a user"""
    import hashlib, base64, time
    raw = f"ROOTKIT-PRO-{tier}-{int(time.time())}-{os.urandom(4).hex()}"
    key = base64.b64encode(hashlib.sha256(raw.encode()).digest()[:12]).decode()[:16]
    return key

def validate_premium_key(key):
    """Validate a premium key"""
    import time
    for valid_key, info in PREMIUM_KEYS.items():
        if key == valid_key:
            return {"valid": True, "tier": info["tier"], "price": info["price"],
                    "features": ["device_details","actions_all","usb_analyzer","premium_badge"],
                    "expires": "lifetime" if info["expires"] == -1 else f"{info['expires']//86400} days"}
    for user, info in KNOWN_KEYS.items():
        if info["key"] == key:
            return {"valid": True, "tier": info["tier"],
                    "features": ["device_details","actions_all","usb_analyzer","premium_badge",
                                 "fastboot_recovery","shizuku_dhizuku","optimize","recovery",
                                 "buildprop","cpu_tweaks","test_toolbox","logcat","ota_block","adb_terminal",
                                 "battery_health","hardware_test","wireless_adb","screen_mirror"],
                    "expires": info["expires"]}
    return {"valid": False}

# Known premium keys (one per user)
KNOWN_KEYS = {
    "adriyache": {"key":"RKT-PRO-ADRY2026","tier":"lifetime","expires":"never"},
    "demo": {"key":"RKT-PRO-DEMO-001","tier":"monthly","expires":"2026-09-01"},
}

def get_premium_status(key=None):
    if key and key in [v["key"] for v in KNOWN_KEYS.values()]:
        for user, info in KNOWN_KEYS.items():
            if info["key"] == key:
                return {"active":True,"user":user,"tier":info["tier"],"expires":info["expires"],
                        "features":["premium_badge","device_details","actions_all","usb_analyzer","priority_support",
                                    "fastboot_recovery","shizuku_dhizuku","screenshot","screenrecord","edl_mode"]}
    # Hardcoded master key
    if key == "RKT-MASTER-2026-FREE":
        return {"active":True,"user":"master","tier":"lifetime","expires":"never",
                "features":["premium_badge","device_details","actions_all","usb_analyzer","priority_support",
                            "fastboot_recovery","shizuku_dhizuku","screenshot","screenrecord","edl_mode"]}
    return {"active":False}

# ===== PREMIUM KEY REQUEST (24h wait) =====
PENDING_KEYS_FILE = os.path.join(APP_DIR, 'pending_keys.json')

def load_pending_keys():
    if os.path.exists(PENDING_KEYS_FILE):
        try: return json.load(open(PENDING_KEYS_FILE))
        except: return {}
    return {}

def save_pending_keys(keys):
    with open(PENDING_KEYS_FILE, 'w') as f: json.dump(keys, f)

def request_premium_key(device_id=None):
    """Request a premium key with 24h wait"""
    import hashlib, time, uuid
    pending = load_pending_keys()
    device_id = device_id or uuid.uuid4().hex[:8]
    now = int(time.time())
    cooldown = 24 * 3600  # 24 hours
    
    # Check if device already requested
    if device_id in pending:
        req_time = pending[device_id]["requested_at"]
        elapsed = now - req_time
        remaining = max(0, cooldown - elapsed)
        if remaining > 0:
            return {"status":"waiting","device_id":device_id,
                    "requested_at":req_time,
                    "remaining_seconds":remaining,
                    "remaining_hours":round(remaining/3600,1),
                    "ready_in":f"{int(remaining/3600)}h {int((remaining%3600)/60)}m"}
        else:
            # Time passed, generate key
            raw = f"RKT-FREE-{device_id}-{req_time}"
            key = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
            pending[device_id]["key"] = key
            pending[device_id]["activated"] = now
            save_pending_keys(pending)
            return {"status":"ready","device_id":device_id,"key":key,
                    "tier":"monthly","expires":"30 days"}
    
    # New request
    pending[device_id] = {
        "requested_at": now,
        "device_id": device_id,
        "status": "pending"
    }
    save_pending_keys(pending)
    return {"status":"requested","device_id":device_id,
            "wait_hours":24,"ready_at":now+cooldown,
            "msg":"Premium key requested! Check back in 24 hours."}

def get_premium_status(key=None):
    # Check known keys (instant)
    if key and key in [v["key"] for v in KNOWN_KEYS.values()]:
        for user, info in KNOWN_KEYS.items():
            if info["key"] == key:
                return {"active":True,"user":user,"tier":info["tier"],"expires":info["expires"],
                        "features":["premium_badge","device_details","actions_all","optimize","recovery","usb_analyzer","priority_support",
                                    "fastboot_recovery","shizuku_dhizuku","screenshot","screenrecord","edl_mode",
                                    "buildprop","cpu_tweaks","test_toolbox","logcat","ota_block","adb_terminal",
                                    "battery_health","hardware_test","wireless_adb","screen_mirror"]}
    # Master key
    if key == "RKT-MASTER-2026-FREE":
        return {"active":True,"user":"master","tier":"lifetime","expires":"never",
                "features":["premium_badge","device_details","actions_all","optimize","recovery","usb_analyzer","priority_support",
                            "fastboot_recovery","shizuku_dhizuku","screenshot","screenrecord","edl_mode",
                            "buildprop","cpu_tweaks","test_toolbox","logcat","ota_block","adb_terminal",
                            "battery_health","hardware_test","wireless_adb","screen_mirror"]}
    # Check pending keys
    if key:
        for did, info in load_pending_keys().items():
            if info.get("key") == key:
                return {"active":True,"user":did,"tier":"free-monthly","expires":"30 days",
                        "features":["premium_badge","device_details","actions_all","usb_analyzer",
                                    "fastboot_recovery","shizuku_dhizuku","screenshot","screenrecord","edl_mode",
                                    "buildprop","cpu_tweaks","test_toolbox","logcat","ota_block","adb_terminal",
                                    "battery_health","hardware_test","wireless_adb","screen_mirror"]}
    return {"active":False}

# ===== BUILD.PROP EDITOR =====
def get_buildprop(serial=None, prop=None, value=None):
    adb_shell = f'"{ADB}" -s {serial} shell' if serial else f'"{ADB}" shell'
    if prop and value is not None:
        run(f'{adb_shell} su -c "setprop {prop} {value}" 2>/dev/null')
        run(f'{adb_shell} setprop {prop} {value} 2>/dev/null')
        return {"status":"ok","prop":prop,"value":value}
    props_out = run(f'{adb_shell} getprop')
    lines = props_out.split('\n')
    result = {}
    for line in lines:
        if ']: [' in line:
            key = line.split(']: [')[0].strip('[')
            val = line.split(']: [')[1].strip(']')
            result[key] = val
    return {"props": result, "count": len(result)}

# ===== CPU/GAMING TWEAKS =====
def get_cpu_tweaks(serial=None, profile=None):
    adb_shell = f'"{ADB}" -s {serial} shell' if serial else f'"{ADB}" shell'
    if profile:
        if profile == "performance":
            run(f'{adb_shell} echo performance > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null')
        elif profile == "powersave":
            run(f'{adb_shell} echo powersave > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null')
        else:
            run(f'{adb_shell} echo schedutil > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null')
        return {"status":"ok","profile":profile,"msg":f"CPU profile set to {profile}! May revert on reboot."}
    governors = run(f'{adb_shell} cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null')
    available = run(f'{adb_shell} cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors 2>/dev/null')
    cores_online = run(f'{adb_shell} cat /sys/devices/system/cpu/online 2>/dev/null')
    freq = run(f'{adb_shell} cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null')
    return {
        "governor": governors or "N/A",
        "available_governors": available.split() if available else [],
        "cores_online": cores_online or "N/A",
        "current_freq_mhz": round(int(freq)/1000, 1) if freq and freq.isdigit() else "N/A",
    }

# ===== TEST TOOLBOX =====
def run_test(serial=None, test=None):
    adb_shell = f'"{ADB}" -s {serial} shell' if serial else f'"{ADB}" shell'
    if test == "sensors":
        out = run(f'{adb_shell} dumpsys sensorservice 2>/dev/null | head -60')
        return {"test":"sensors","output":out}
    elif test == "screen":
        out = run(f'{adb_shell} dumpsys display 2>/dev/null | head -50')
        return {"test":"screen","output":out}
    elif test == "touch":
        out = run(f'{adb_shell} dumpsys input 2>/dev/null | head -50')
        return {"test":"touch","output":out}
    elif test == "sound":
        out = run(f'{adb_shell} dumpsys media.audio_flinger 2>/dev/null | head -40')
        return {"test":"sound","output":out}
    return {"test":"unknown","output":"Invalid test"}

# ===== LOGCAT VIEWER =====
def get_logcat(serial=None, lines=20, filter_text=None):
    adb_shell = f'"{ADB}" -s {serial} shell' if serial else f'"{ADB}" shell'
    try: lines = int(lines)
    except: lines = 20
    cmd = f'logcat -d -t {lines}'
    if filter_text:
        cmd += f' | grep -i "{filter_text}"'
    out = run(f'{adb_shell} {cmd} 2>/dev/null')
    logs = [l for l in out.split('\n') if l.strip()] if out else []
    return {"lines": logs, "count": len(logs)}

# ===== OTA BLOCKER =====
def ota_block(serial=None, action="status"):
    adb_shell = f'"{ADB}" -s {serial} shell' if serial else f'"{ADB}" shell'
    if action == "block":
        run(f'{adb_shell} pm disable com.google.android.gms/.update.SystemUpdateActivity 2>/dev/null')
        run(f'{adb_shell} pm disable com.android.systemui/.SystemUpdate 2>/dev/null')
        run(f'{adb_shell} pm disable com.android.updater 2>/dev/null')
        run(f'{adb_shell} pm disable com.google.android.gms/.update.SystemUpdateService 2>/dev/null')
        return {"status":"ok","action":"blocked","msg":"OTA updates blocked! Re-enable with unblock."}
    elif action == "unblock":
        run(f'{adb_shell} pm enable com.google.android.gms/.update.SystemUpdateActivity 2>/dev/null')
        run(f'{adb_shell} pm enable com.android.systemui/.SystemUpdate 2>/dev/null')
        run(f'{adb_shell} pm enable com.android.updater 2>/dev/null')
        run(f'{adb_shell} pm enable com.google.android.gms/.update.SystemUpdateService 2>/dev/null')
        return {"status":"ok","action":"unblocked","msg":"OTA updates re-enabled!"}
    else:
        blocked = run(f'{adb_shell} pm list packages -d 2>/dev/null | grep -i "update"')
        return {"status":"checking","blocked": bool(blocked.strip())}

# ===== ADB SHELL TERMINAL =====
def adb_shell_cmd(serial=None, cmd=""):
    if not cmd:
        return {"status":"error","msg":"No command provided"}
    adb_cmd = f'"{ADB}" -s {serial}' if serial else f'"{ADB}"'
    out = run(f'{adb_cmd} shell {cmd}', timeout=15)
    return {"cmd": cmd, "output": out}

# ===== BATTERY HEALTH =====
def get_battery_health(serial=None):
    adb_shell = f'"{ADB}" -s {serial} shell' if serial else f'"{ADB}" shell'
    result = {}
    for f in ['capacity','cycle_count','charge_full','charge_full_design','charge_counter','current_now','status','health','technology']:
        val = run(f'{adb_shell} cat /sys/class/power_supply/battery/{f} 2>/dev/null')
        if val:
            result[f] = val
    if not result:
        # Fallback to dumpsys
        ds = run(f'{adb_shell} dumpsys battery 2>/dev/null')
        for line in ds.split('\n'):
            if ':' in line:
                k,v = line.split(':',1)
                result[k.strip().lower().replace(' ','_')] = v.strip()
    if result.get('charge_full') and result.get('charge_full_design'):
        try:
            result['health_pct'] = round(int(result['charge_full']) / int(result['charge_full_design']) * 100, 1)
        except: pass
    return result

# ===== HARDWARE TESTER =====
def run_hardware_test(serial=None, test=None):
    adb_shell = f'"{ADB}" -s {serial} shell' if serial else f'"{ADB}" shell'
    if test == "camera":
        cams = run(f'{adb_shell} dumpsys media.camera 2>/dev/null | grep -i "camera\|module\|device" | head -20')
        return {"test":"camera","output":cams or "No camera info"}
    elif test == "wifi":
        wifi = run(f'{adb_shell} dumpsys wifi 2>/dev/null | grep -i "Wi-Fi is\|state\|enabled\|connected\|ssid" | head -10')
        return {"test":"wifi","output":wifi or "No WiFi info"}
    elif test == "gps":
        gps = run(f'{adb_shell} dumpsys location 2>/dev/null | grep -i "gps\|provider\|location" | head -10')
        return {"test":"gps","output":gps or "No GPS info"}
    elif test == "nfc":
        nfc = run(f'{adb_shell} dumpsys nfc 2>/dev/null | grep -i "NFC\|nfc" | head -10')
        return {"test":"nfc","output":nfc or "No NFC"}
    elif test == "bluetooth":
        bt = run(f'{adb_shell} dumpsys bluetooth_manager 2>/dev/null | grep -i "state\|adapter\|enabled" | head -10')
        return {"test":"bluetooth","output":bt or "No BT info"}
    return {"test":"unknown","output":"Invalid test"}

# ===== WIRELESS ADB =====
def wireless_adb(serial=None, action="status", port=5555):
    adb_cmd = f'"{ADB}" -s {serial}' if serial else f'"{ADB}"'
    adb_shell = f'{adb_cmd} shell'
    if action == "enable":
        ip = run(f'{adb_shell} ip addr show wlan0 2>/dev/null | grep "inet " | head -1')
        if not ip:
            ip = run(f'{adb_shell} getprop dhcp.wlan0.ipaddress 2>/dev/null')
        ip_addr = ""
        if ip:
            parts = ip.split()
            for p in parts:
                if '.' in p and '/' in p:
                    ip_addr = p.split('/')[0]
                    break
                elif '.' in p:
                    ip_addr = p
        if not ip_addr:
            ip_addr = run(f'{adb_shell} ifconfig wlan0 2>/dev/null | grep "inet addr" | head -1')
            if ':' in ip_addr:
                ip_addr = ip_addr.split(':')[1].split()[0]
        run(f'{adb_cmd} tcpip {port} 2>/dev/null')
        return {"status":"ok","action":"enabled","port":port,"ip":ip_addr or "unknown","msg":f"Wireless ADB on {ip_addr}:{port}"}
    elif action == "disable":
        run(f'{adb_cmd} usb 2>/dev/null')
        return {"status":"ok","action":"disabled","msg":"Wireless ADB disabled, back to USB"}
    else:
        mode = run(f'{adb_cmd} shell getprop service.adb.tcp.port 2>/dev/null')
        ip = run(f'{adb_shell} ip addr show wlan0 2>/dev/null | grep "inet " | head -1')
        return {"status":"checking","tcp_mode": bool(mode.strip()),"ip":"..."}

# ===== SCREEN MIRROR =====
def screen_mirror(serial=None):
    import base64, time
    adb_shell = f'"{ADB}" -s {serial} shell' if serial else f'"{ADB}" shell'
    ts = str(int(time.time()*1000))
    path = f"/sdcard/.rkt_mirror_{ts}.png"
    run(f'{adb_shell} screencap -p {path} 2>/dev/null')
    adb_cmd = f'"{ADB}" -s {serial}' if serial else f'"{ADB}"'
    raw = run(f'{adb_cmd} exec-out cat {path} 2>/dev/null')
    run(f'{adb_shell} rm {path} 2>/dev/null')
    if raw:
        b64 = base64.b64encode(raw.encode('latin-1')).decode() if raw else ""
        return {"image": b64, "ts": ts}
    return {"error": "No screenshot"}

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Methods','GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = self.path.split('?')[0]
        params = {}
        if '?' in self.path:
            for p in self.path.split('?')[1].split('&'):
                if '=' in p:
                    k,v = p.split('=',1)
                    params[k] = v

        data = None
        if path == '/api/devices':
            data = get_devices()
        elif path == '/api/device':
            serial = params.get('serial','')
            if serial:
                data = get_device_by_serial(serial)
            else:
                data = get_devices()
        elif path == '/api/methods':
            data = get_methods(params.get('brand',''))
        elif path == '/api/risk':
            serial = params.get('serial','')
            device = get_device_by_serial(serial) if serial else get_devices()
            if isinstance(device, dict) and "devices" in device:
                data = {"risks":[], "score":0, "level":"none"}
            else:
                data = get_risk(device)
        elif path == '/api/apps':
            data = get_apps(params.get('serial',''))
        elif path == '/api/backup':
            data = do_backup(params.get('serial',''))
        elif path == '/api/panic':
            data = do_panic(params.get('serial',''))
        elif path == '/api/execute':
            data = do_execute(params.get('tool',''), params.get('serial',''))
        elif path == '/api/usb-devices':
            data = get_usb_devices()
        elif path == '/api/action':
            data = do_action(params.get('action',''), params.get('serial',''))
        elif path == '/api/device-details':
            data = get_device_details(params.get('serial',''))
        elif path == '/api/premium/status':
            data = get_premium_status(params.get('key',''))
        elif path == '/api/premium/validate':
            data = validate_premium_key(params.get('key',''))
        elif path == '/api/premium/request':
            data = request_premium_key(params.get('device_id',''))
        elif path == '/api/premium/generate':
            data = {"key": generate_premium_key(params.get('tier','monthly')), "tier": params.get('tier','monthly'), "note": "Contact @Adriyache32 to activate"}
        elif path == '/api/optimize':
            data = get_optimization(params.get('serial',''))
        elif path == '/api/recovery':
            data = get_recovery_info(params.get('serial',''))
        elif path == '/api/buildprop':
            data = get_buildprop(params.get('serial',''), params.get('prop'), params.get('value'))
        elif path == '/api/cpu-tweaks':
            data = get_cpu_tweaks(params.get('serial',''), params.get('profile'))
        elif path == '/api/test-toolbox':
            data = run_test(params.get('serial',''), params.get('test'))
        elif path == '/api/logcat':
            data = get_logcat(params.get('serial',''), params.get('lines',20), params.get('filter'))
        elif path == '/api/ota-block':
            data = ota_block(params.get('serial',''), params.get('action','status'))
        elif path == '/api/adb-shell':
            data = adb_shell_cmd(params.get('serial',''), params.get('cmd',''))
        elif path == '/api/battery-health':
            data = get_battery_health(params.get('serial',''))
        elif path == '/api/hardware-test':
            data = run_hardware_test(params.get('serial',''), params.get('test'))
        elif path == '/api/wireless-adb':
            data = wireless_adb(params.get('serial',''), params.get('action','status'), params.get('port',5555))
        elif path == '/api/screen-mirror':
            data = screen_mirror(params.get('serial',''))
        elif path == '/api/system':
            data = get_system_info()
        elif path == '/':
            html_path = os.path.join(APP_DIR, 'html', 'index.html')
            if os.path.isfile(html_path):
                self.send_response(200)
                self.send_header('Content-Type','text/html')
                self.end_headers()
                with open(html_path, 'rb') as f:
                    self.wfile.write(f.read())
                return
            data = {"error":"index.html not found"}
        else:
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

if __name__ == '__main__':
    color_purple = '\033[38;5;141m' if not IS_WINDOWS else ''
    color_reset = '\033[0m' if not IS_WINDOWS else ''
    print(f"{color_purple}  ROOT KIT PRO API v2.1 ({platform.system()}){color_reset}")
    print(f"{color_purple}  http://localhost:{PORT}{color_reset}")
    print(f"{color_purple}  ADB: {ADB} | Multi-device: ON{color_reset}")
    class ReuseServer(socketserver.TCPServer):
        allow_reuse_address = True
        def server_bind(self):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try: self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except: pass
            self.socket.bind(self.server_address)
    with ReuseServer(("127.0.0.1", PORT), Handler) as server:
        server.serve_forever()
