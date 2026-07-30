#!/bin/bash
# ROOT KIT PRO - Local API Server
# Serves device data as JSON for the HTML frontend
set -euo pipefail

PORT=20229
APP_DIR="$HOME/.rootkit-pro"

get_device_data() {
    local brand="" model="" android="" imei="" serial="" codename="" bootloader=""
    local sdk="" cpu="" rooted="" battery="" oem="" frp="" dm_verify=""

    if adb devices 2>/dev/null | grep -q "device$"; then
        serial=$(adb devices 2>/dev/null | grep "device$" | head -1 | awk '{print $1}')
        brand=$(adb shell getprop ro.product.brand 2>/dev/null | tr -d '\r')
        model=$(adb shell getprop ro.product.model 2>/dev/null | tr -d '\r')
        android=$(adb shell getprop ro.build.version.release 2>/dev/null | tr -d '\r')
        sdk=$(adb shell getprop ro.build.version.sdk 2>/dev/null | tr -d '\r')
        codename=$(adb shell getprop ro.product.device 2>/dev/null | tr -d '\r')
        cpu=$(adb shell getprop ro.product.cpu.abi 2>/dev/null | tr -d '\r')
        imei=$(adb shell service call iphonesubinfo 1 2>/dev/null | awk -F "'" '{print $2}' | sed 's/ //g' | tr -d '\n.' | head -c 15)
        [ ${#imei} -lt 13 ] && imei=$(adb shell settings get secure android_id 2>/dev/null | tr -d '\r')
        rooted=$(adb shell "su -c id 2>/dev/null | grep -c uid=0" 2>/dev/null | tr -d '\r')
        [ "$rooted" = "1" ] && rooted="true" || rooted="false"
        bootloader=$(adb shell getprop ro.boot.flash.locked 2>/dev/null | tr -d '\r')
        [ "$bootloader" = "0" ] && bootloader="unlocked" || [ "$bootloader" = "1" ] && bootloader="locked" || bootloader="unknown"
        battery=$(adb shell dumpsys battery 2>/dev/null | grep "level:" | awk '{print $2}' | tr -d '\r')
        oem=$(adb shell settings get global oem_unlock_enabled 2>/dev/null | tr -d '\r')
        frp=$(adb shell getprop ro.frp.pst 2>/dev/null | tr -d '\r')
        dm_verify=$(adb shell getprop ro.boot.verifiedbootstate 2>/dev/null | tr -d '\r')

        cat << JSON
{"connected":true,"brand":"$brand","model":"$model","android":"$android","sdk":"$sdk","codename":"$codename","cpu":"$cpu","imei":"$imei","serial":"$serial","bootloader":"$bootloader","rooted":$rooted,"battery":"$battery","oem":"$oem","frp":"$frp","dm_verify":"$dm_verify"}
JSON
    else
        echo '{"connected":false}'
    fi
}

get_methods() {
    local brand="${1:-}"
    local brand_lower=$(echo "$brand" | tr '[:upper:]' '[:lower:]')
    case "$brand_lower" in
        xiaomi|redmi|poco)
            echo '[{"name":"Mi Unlock (official)","url":"https://en.miui.com/unlock/download_en.html","success":65,"tool":"xiaomi_mi_unlock"},{"name":"EDL Firehose","cmd":"fastboot oem unlock","success":40,"tool":"edl_firehose"},{"name":"Direct bootloader","cmd":"fastboot flashing unlock","success":55,"tool":"direct_unlock"}]'
            ;;
        motorola|moto)
            echo '[{"name":"Motorola unlock (official)","url":"https://motorola.com/unlockbootloader","success":50,"tool":"motola_official"},{"name":"Fastboot OEM","cmd":"fastboot oem unlock","success":45,"tool":"fastboot_oem"},{"name":"EDL/QFIL","cmd":"QFIL tool","success":35,"tool":"edl_qfil"}]'
            ;;
        samsung)
            echo '[{"name":"OEM Unlock","cmd":"Settings > Developer > OEM Unlock","success":70,"tool":"samsung_oem"},{"name":"Heimdall","cmd":"heimdall flash","success":55,"tool":"heimdall"},{"name":"Download Mode + Odin","cmd":"Odin3 tool","success":45,"tool":"odin_mode"}]'
            ;;
        apple|iphone)
            echo '[{"name":"checkra1n","url":"https://checkra.in","success":60,"tool":"checkrain"},{"name":"palera1n","url":"https://palera.in","success":55,"tool":"palera1n"},{"name":"Taurine / Dopamine","cmd":"Unc0ver family","success":40,"tool":"taurine"}]'
            ;;
        huawei)
            echo '[{"name":"EMUI unlock","url":"https://consumer.huawei.com/en/flash/unlock","success":35,"tool":"huawei_emui"},{"name":"Fastboot oem","cmd":"fastboot oem unlock","success":30,"tool":"fastboot_huawei"},{"name":"EDL deep flash","cmd":"Deep flash cable","success":25,"tool":"deep_flash"}]'
            ;;
        google|pixel)
            echo '[{"name":"Fastboot flashing unlock","cmd":"fastboot flashing unlock","success":80,"tool":"pixel_unlock"},{"name":"Android Flash Tool","url":"https://flash.android.com","success":75,"tool":"flash_tool"},{"name":"Factory Image","cmd":"Google factory images","success":70,"tool":"factory_image"}]'
            ;;
        oneplus)
            echo '[{"name":"Fastboot unlock","cmd":"fastboot oem unlock","success":75,"tool":"oneplus_unlock"},{"name":"MSM Download Tool","cmd":"MSM tool","success":50,"tool":"msm_tool"},{"name":"Deep testing app","cmd":"OnePlus community app","success":60,"tool":"deep_testing"}]'
            ;;
        *)
            echo '[{"name":"Fastboot OEM","cmd":"fastboot oem unlock","success":30,"tool":"fastboot_oem"},{"name":"Fastboot flashing","cmd":"fastboot flashing unlock","success":25,"tool":"fastboot_flashing"}]'
            ;;
    esac
}

get_risk() {
    local brand="${1:-}" model="${2:-}"
    local battery=$(adb shell dumpsys battery 2>/dev/null | grep "level:" | awk '{print $2}' | tr -d '\r')
    local oem=$(adb shell settings get global oem_unlock_enabled 2>/dev/null | tr -d '\r')
    local frp=$(adb shell getprop ro.frp.pst 2>/dev/null | tr -d '\r')
    local bl=$(adb shell getprop ro.boot.flash.locked 2>/dev/null | tr -d '\r')
    local dm=$(adb shell getprop ro.boot.verifiedbootstate 2>/dev/null | tr -d '\r')
    local score=0
    local risks="[]"

    [ -n "$battery" ] && [ "$battery" -lt 30 ] && score=$((score+30))
    [ -n "$battery" ] && [ "$battery" -ge 30 ] && [ "$battery" -lt 50 ] && score=$((score+10))
    [ "$oem" = "0" ] && score=$((score+25))
    [ -n "$frp" ] && score=$((score+15))
    [ "$bl" = "1" ] && score=$((score+15))
    [ "$dm" = "verified" ] && score=$((score+10))

    cat << JSON
{"battery":"$battery","oem":"$oem","frp":"$frp","bootloader":"$bl","dm_verify":"$dm","score":$score}
JSON
}

get_backup_apps() {
    adb shell pm list packages -3 2>/dev/null | sed 's/package://' | jq -R . | jq -s .
}

do_backup() {
    local backup_dir="$HOME/HDD-Backups/rootkit-backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"/{apps,contacts,photos,files,sms,settings,system}
    adb shell pm list packages -3 2>/dev/null | sed 's/package://' > "$backup_dir/apps/packages.txt"
    adb shell settings list system > "$backup_dir/settings/system.txt" 2>/dev/null
    adb shell settings list secure > "$backup_dir/settings/secure.txt" 2>/dev/null
    adb shell settings list global > "$backup_dir/settings/global.txt" 2>/dev/null
    adb shell getprop > "$backup_dir/system/properties.txt" 2>/dev/null
    adb shell content query --uri content://sms/ 2>/dev/null > "$backup_dir/sms/sms.txt"
    adb pull /sdcard/DCIM/ "$backup_dir/photos/" 2>/dev/null
    adb pull /sdcard/Download/ "$backup_dir/files/" 2>/dev/null
    echo "{\"status\":\"ok\",\"path\":\"$backup_dir\"}"
}

do_panic() {
    adb kill-server 2>/dev/null
    fastboot reboot 2>/dev/null
    echo '{"status":"ok"}'
}

# HTTP Server
echo -e "\033[38;5;141m  ROOT KIT PRO API Server starting on port $PORT...\033[0m"

while true; do
    request=$(nc -l -p "$PORT" -q 1 2>/dev/null || true)
    method=$(echo "$request" | head -1 | awk '{print $2}')

    case "$method" in
        /api/device)
            data=$(get_device_data)
            ;;
        /api/methods*)
            brand=$(echo "$request" | grep -oP 'brand=\K[^& ]+' || echo "")
            data=$(get_methods "$brand")
            ;;
        /api/risk*)
            brand=$(echo "$request" | grep -oP 'brand=\K[^& ]+' || echo "")
            model=$(echo "$request" | grep -oP 'model=\K[^& ]+' || echo "")
            data=$(get_risk "$brand" "$model")
            ;;
        /api/apps)
            data=$(get_backup_apps)
            ;;
        /api/backup)
            data=$(do_backup)
            ;;
        /api/panic)
            data=$(do_panic)
            ;;
        *)
            data='{"error":"not found"}'
            ;;
    esac

    printf "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\n\r\n%s" "$data" | nc -l -p "$PORT" -q 0 2>/dev/null || true
done
