#!/bin/bash
# Deploy ROOT KIT PRO to USB drive
USB="${1:-/media/$USER/ROOTKIT-USB}"
if [ ! -d "$USB" ]; then
    echo "USB not found at $USB"
    echo "Usage: $0 /media/$USER/USB_LABEL"
    exit 1
fi
mkdir -p "$USB/ROOTKIT-PRO"
cp /usr/local/bin/rootkit-pro "$USB/ROOTKIT-PRO/"
cp "$HOME/.rootkit-pro/portable/rootkit-pro-portable" "$USB/ROOTKIT-PRO/"
chmod +x "$USB/ROOTKIT-PRO/"*
# Create launcher
cat > "$USB/ROOTKIT-PRO/start.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
bash rootkit-pro-portable portable
EOF
chmod +x "$USB/ROOTKIT-PRO/start.sh"
echo "ROOT KIT PRO deployed to $USB/ROOTKIT-PRO/"
echo "Run: bash $USB/ROOTKIT-PRO/start.sh"
