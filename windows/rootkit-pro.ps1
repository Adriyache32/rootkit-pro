# ROOT KIT PRO v2.1 - Windows PowerShell CLI
# GitHub Dark Theme Terminal UI

$ErrorActionPreference = "SilentlyContinue"
$APP_DIR = "$env:USERPROFILE\.rootkit-pro"

# GitHub Dark Theme Colors
$BG      = "`e[48;5;235m"
$FG      = "`e[38;5;252m"
$DIM     = "`e[2m"
$BOLD    = "`e[1m"
$RESET   = "`e[0m"
$GREEN   = "`e[38;5;78m"
$BLUE    = "`e[38;5;75m"
$PURPLE  = "`e[38;5;141m"
$YELLOW  = "`e[38;5;179m"
$RED     = "`e[38;5;203m"
$BORDER  = "`e[38;5;240m"
$CYAN    = "`e[38;5;117m"
$WHITE   = "`e[38;5;255m"

function Write-Line { Write-Host "$BORDER────────────────────────────────────────────────────────────────$RESET" }
function Write-Thin { Write-Host "$BORDER┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄$RESET" }

function Show-Header {
    Clear-Host
    Write-Host ""
    Write-Host "  ${BORDER}┌──────────────────────────────────────────────────────────────┐${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${PURPLE}${BOLD}███╗   ██╗${RESET} ${GREEN}${BOLD}██╗  ██╗${RESET} ${BLUE}${BOLD}███████╗${RESET} ${YELLOW}${BOLD}████████╗${RESET} ${RED}${BOLD}██╗   ██╗${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${PURPLE}${BOLD}████╗  ██║${RESET} ${GREEN}${BOLD}██║  ██║${RESET} ${BLUE}${BOLD}██╔════╝${RESET} ${YELLOW}${BOLD}╚══██╔══╝${RESET} ${RED}${BOLD}╚██╗ ██╔╝${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${PURPLE}${BOLD}██╔██╗ ██║${RESET} ${GREEN}${BOLD}███████║${RESET} ${BLUE}${BOLD}█████╗${RESET}      ${YELLOW}${BOLD}██║${RESET}     ${RED}${BOLD} ╚████╔╝ ${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${PURPLE}${BOLD}██║╚██╗██║${RESET} ${GREEN}${BOLD}██╔══██║${RESET} ${BLUE}${BOLD}██╔══╝${RESET}      ${YELLOW}${BOLD}██║${RESET}     ${RED}${BOLD}  ╚██╔╝  ${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${PURPLE}${BOLD}██║ ╚████║${RESET} ${GREEN}${BOLD}██║  ██║${RESET} ${BLUE}${BOLD}███████╗${RESET}     ${YELLOW}${BOLD}██║${RESET}     ${RED}${BOLD}   ██║   ${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${PURPLE}${BOLD}╚═╝  ╚═══╝${RESET} ${GREEN}${BOLD}╚═╝  ╚═╝${RESET} ${BLUE}${BOLD}╚══════╝${RESET}     ${YELLOW}${BOLD}╚═╝${RESET}     ${RED}${BOLD}   ╚═╝   ${RESET}"
    Write-Host "  ${BORDER}│${RESET}                                                              ${BORDER}│${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${DIM}Universal Phone Root / Unlock Tool${RESET}  ${DIM}v2.1${RESET}   ${DIM}Windows${RESET}         ${BORDER}│${RESET}"
    Write-Host "  ${BORDER}└──────────────────────────────────────────────────────────────┘${RESET}"
    Write-Host ""
}

function Show-DeviceCard($brand,$model,$android,$codename,$cpu,$imei,$serial,$bootloader,$rooted) {
    $blColor = if ($bootloader -eq "unlocked") { $GREEN } else { $YELLOW }
    $blText  = if ($bootloader -eq "unlocked") { "Unlocked" } else { "Locked" }
    $rtColor = if ($rooted) { $GREEN } else { $RED }
    $rtText  = if ($rooted) { "YES" } else { "NO" }

    Write-Host "  ${BORDER}┌──────────────────────────────────────────────────────────────┐${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${BLUE}${BOLD}Device${RESET}                                                   ${BORDER}│${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${BORDER}────────────────────────────────────────────────────────────${RESET}  ${BORDER}│${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${DIM}Brand:${RESET}      ${FG}$brand${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${DIM}Model:${RESET}      ${FG}$model${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${DIM}Codename:${RESET}   ${CYAN}$codename${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${DIM}Android:${RESET}    ${GREEN}$android${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${DIM}CPU:${RESET}        ${FG}$cpu${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${DIM}IMEI:${RESET}       ${FG}$imei${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${DIM}Serial:${RESET}     ${FG}$serial${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${DIM}Bootloader:${RESET} ${blColor}${blText}${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${DIM}Root:${RESET}       ${rtColor}${rtText}${RESET}"
    Write-Host "  ${BORDER}└──────────────────────────────────────────────────────────────┘${RESET}"
}

function Get-DeviceInfo {
    $devices = & adb devices 2>$null
    $connected = $devices | Select-String "`tdevice$" 
    if (-not $connected) { return $null }

    $serial = ($devices | Where-Object { $_ -match "`tdevice$" } | Select-Object -First 1) -split "`t" | Select-Object -First 1
    $brand = (& adb shell getprop ro.product.brand 2>$null).Trim()
    $model = (& adb shell getprop ro.product.model 2>$null).Trim()
    $android = (& adb shell getprop ro.build.version.release 2>$null).Trim()
    $codename = (& adb shell getprop ro.product.device 2>$null).Trim()
    $cpu = (& adb shell getprop ro.product.cpu.abi 2>$null).Trim()
    $imei = (& adb shell "service call iphonesubinfo 1" 2>$null | ForEach-Object { if ($_ -match "'([^']+)'") { $matches[1].Replace(' ','') } } | Join-String).Substring(0,15)
    $bl = (& adb shell getprop ro.boot.flash.locked 2>$null).Trim()
    $bootloader = if ($bl -eq "0") { "unlocked" } else { "locked" }
    $rooted = (& adb shell "su -c id 2>/dev/null | grep -c uid=0" 2>$null).Trim() -eq "1"
    $battery = (& adb shell "dumpsys battery | grep level:" 2>$null) -replace '.*level:\s*','' | ForEach-Object { $_.Trim() } | Select-Object -First 1

    return @{
        Connected=$true; Brand=$brand; Model=$model; Android=$android
        Codename=$codename; CPU=$cpu; IMEI=$imei; Serial=$serial
        Bootloader=$bootloader; Rooted=$rooted; Battery=$battery
    }
}

function Show-Methods($brand) {
    $methods = @()
    switch -Wildcard ($brand.ToLower()) {
        "xiaomi*" { $methods = @(
            @{Name="Mi Unlock (official)"; Success=65; Status="Verify"},
            @{Name="EDL Firehose"; Success=40; Status="Available"},
            @{Name="Direct bootloader"; Success=55; Status="Available"}
        )}
        "motorola*" { $methods = @(
            @{Name="Motorola unlock (official)"; Success=50; Status="Verify"},
            @{Name="Fastboot OEM"; Success=45; Status="Available"},
            @{Name="EDL/QFIL"; Success=35; Status="Available"}
        )}
        "samsung*" { $methods = @(
            @{Name="OEM Unlock"; Success=70; Status="Available"},
            @{Name="Heimdall"; Success=55; Status="Available"},
            @{Name="Download Mode + Odin"; Success=45; Status="Available"}
        )}
        "google*" { $methods = @(
            @{Name="Fastboot flashing unlock"; Success=80; Status="Available"},
            @{Name="Android Flash Tool"; Success=75; Status="Verify"}
        )}
        "oneplus*" { $methods = @(
            @{Name="Fastboot unlock"; Success=75; Status="Available"},
            @{Name="MSM Download Tool"; Success=50; Status="Verify"}
        )}
        default { $methods = @(
            @{Name="Fastboot OEM"; Success=30; Status="Available"}
        )}
    }

    Show-Header
    Write-Host "  ${PURPLE}${BOLD}UNLOCK METHODS${RESET}  ${DIM}$brand${RESET}"
    Write-Line
    Write-Host ""
    Write-Host "  ${BORDER}│${RESET}  ${DIM}#   Method                          Success   Status${RESET}"
    Write-Host "  ${BORDER}│${RESET}  ${BORDER}────────────────────────────────────────────────────────────${RESET}"

    $i = 1
    foreach ($m in $methods) {
        $color = if ($m.Success -ge 60) { $GREEN } elseif ($m.Success -ge 35) { $YELLOW } else { $RED }
        $badge = if ($m.Status -eq "Verify") { "${YELLOW}Verify${RESET}" } else { "${GREEN}Available${RESET}" }
        $bar = "$color" + ("█" * [math]::Floor($m.Success/5)) + "${RESET}" + "$DIM" + ("░" * (12 - [math]::Floor($m.Success/5))) + "${RESET}"
        Write-Host "  ${BORDER}│${RESET}  ${DIM}$i${RESET}   ${FG}$($m.Name.PadRight(32))${RESET} ${bar} ${color}$($m.Success.ToString().PadLeft(3))%${RESET}   $badge"
        $i++
    }

    Write-Host "  ${BORDER}│${RESET}  ${BORDER}────────────────────────────────────────────────────────────${RESET}"
    Write-Host "  ${BORDER}└──────────────────────────────────────────────────────────────┘${RESET}"
}

function Show-Risk($brand) {
    $battery = (& adb shell "dumpsys battery | grep level:" 2>$null) -replace '.*level:\s*','' | ForEach-Object { $_.Trim() } | Select-Object -First 1
    $bl = (& adb shell getprop ro.boot.flash.locked 2>$null).Trim()
    $oem = (& adb shell settings get global oem_unlock_enabled 2>$null).Trim()
    $frp = (& adb shell getprop ro.frp.pst 2>$null).Trim()
    $score = 0
    $risks = @()

    if ($battery -and [int]$battery -lt 30) { $risks += "${RED}BATTERY LOW${RESET} ($battery%)"; $score += 30 }
    elseif ($battery -and [int]$battery -lt 50) { $risks += "${YELLOW}BATTERY MEDIUM${RESET} ($battery%)"; $score += 10 }
    if ($oem -eq "0") { $risks += "${RED}OEM Unlock DISABLED${RESET}"; $score += 25 }
    elseif ($oem -eq "null" -or -not $oem) { $risks += "${YELLOW}OEM Unlock: verify in Dev Options${RESET}"; $score += 5 }
    if ($frp) { $risks += "${YELLOW}FRP active${RESET}"; $score += 15 }
    if ($bl -eq "1") { $risks += "${YELLOW}Bootloader LOCKED${RESET}"; $score += 15 }

    $color = if ($score -lt 25) { $GREEN } elseif ($score -lt 50) { $YELLOW } else { $RED }
    $level = if ($score -lt 25) { "LOW RISK" } elseif ($score -lt 50) { "MEDIUM RISK" } else { "HIGH RISK" }

    Show-Header
    Write-Host "  ${YELLOW}${BOLD}RISK ANALYSIS${RESET}  ${DIM}$brand${RESET}"
    Write-Line
    Write-Host ""
    if ($risks.Count -eq 0) { Write-Host "  ${GREEN}No risks detected${RESET}" }
    else { $risks | ForEach-Object { Write-Host "  $_" } }
    Write-Host ""
    Write-Line
    Write-Host "  ${DIM}Risk Score:${RESET} ${FG}$score/100${RESET}"
    Write-Host "  ${color}${BOLD}$level${RESET}"
    Write-Line
}

# === MAIN ===
Show-Header
Write-Host "  ${DIM}Scanning USB devices...${RESET}"
$device = Get-DeviceInfo

if (-not $device) {
    Write-Host "  ${RED}No device detected${RESET}"
    Write-Host "  ${DIM}Connect via USB and enable USB Debugging${RESET}"
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit
}

Write-Host "  ${GREEN}Device detected!${RESET}"
Show-DeviceCard $device.Brand $device.Model $device.Android $device.Codename $device.CPU $device.IMEI $device.Serial $device.Bootloader $device.Rooted
Write-Host ""
Show-Methods $device.Brand
Write-Host ""
Read-Host "Press Enter for Risk Analysis"
Show-Risk $device.Brand
Write-Host ""
Read-Host "Press Enter to exit"
