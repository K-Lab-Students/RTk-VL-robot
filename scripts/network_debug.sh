#!/bin/bash

# Network Debug Script
# Help troubleshoot network scanning issues

echo "🔍 Network Debug & Troubleshooting"
echo "=================================="

TARGET_MAC="2c:cf:67:87:6a:d5"

echo "🎯 Target MAC: $TARGET_MAC"
echo ""

# 1. Check current network configuration
echo "📡 Current Network Configuration:"
echo "--------------------------------"
ip addr show | grep -E "inet|ether" | head -10
echo ""

# 2. Show current routing table
echo "🛣️  Current Routes:"
echo "-------------------"
ip route show
echo ""

# 3. Check current ARP table
echo "📋 Current ARP Table:"
echo "--------------------"
arp -a 2>/dev/null | head -10 || ip neigh show | head -10
echo ""

# 4. Check if target MAC is already in ARP table
echo "🎯 Checking for target MAC in ARP table:"
echo "----------------------------------------"
if arp -a 2>/dev/null | grep -i "$TARGET_MAC"; then
    echo "✅ Found target MAC in ARP table!"
else if ip neigh show | grep -i "$TARGET_MAC"; then
    echo "✅ Found target MAC in neighbor table!"
else
    echo "❌ Target MAC not found in ARP/neighbor table"
fi
fi
echo ""

# 5. Detect active network interfaces
echo "🌐 Active Network Interfaces:"
echo "-----------------------------"
for iface in $(ip link show | grep "state UP" | cut -d: -f2 | tr -d ' '); do
    echo "Interface: $iface"
    ip addr show $iface | grep "inet "
done
echo ""

# 6. Suggest networks to scan
echo "💡 Suggested Networks to Scan:"
echo "------------------------------"
ip route show | grep -E "192\.168\.|10\.|172\." | awk '{print $1}' | grep "/" | sort -u
echo ""

# 7. Test your original command step by step
echo "🧪 Testing Your Original Command:"
echo "---------------------------------"

echo "Step 1: Flushing neighbor table..."
if sudo ip neigh flush all; then
    echo "✅ Neighbor table flushed"
else
    echo "❌ Failed to flush neighbor table"
fi
echo ""

echo "Step 2: Testing ping on 192.168.41.x network..."
echo "Pinging a few hosts to test..."
for i in {1..5}; do
    if ping -c1 -W1 192.168.41.$i >/dev/null 2>&1; then
        echo "✅ 192.168.41.$i responds"
    else
        echo "❌ 192.168.41.$i no response"
    fi
done
echo ""

echo "Step 3: Checking ARP table after ping..."
arp -n | grep "192.168.41" | head -5
echo ""

# 8. Alternative scanning methods
echo "🔧 Alternative Methods:"
echo "----------------------"

# Check if nmap is available
if command -v nmap >/dev/null 2>&1; then
    echo "✅ nmap is available - you can use: nmap -sn 192.168.41.0/24"
else
    echo "❌ nmap not installed - install with: sudo apt install nmap"
fi

# Check if arp-scan is available
if command -v arp-scan >/dev/null 2>&1; then
    echo "✅ arp-scan is available - you can use: sudo arp-scan -l"
else
    echo "❌ arp-scan not installed - install with: sudo apt install arp-scan"
fi

echo ""
echo "💡 Recommendations:"
echo "-------------------"
echo "1. Use the Python script: python scripts/find_device.py $TARGET_MAC"
echo "2. Try different network ranges (your device might not be on 192.168.41.x)"
echo "3. Check if the device responds to ping at all"
echo "4. Make sure the MAC address is correct"
echo "5. Some devices don't respond to ICMP ping - try ARP scan instead" 