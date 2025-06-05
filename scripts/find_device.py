#!/usr/bin/env python3
"""
Device Finder Script
Find devices on network by MAC address with multiple scanning methods.
"""

import subprocess
import sys
import time
import argparse
import ipaddress
import concurrent.futures
import re
from typing import List, Dict, Optional


def run_command(command: List[str], timeout: int = 10) -> tuple:
    """Run a command and return success, stdout, stderr."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def get_network_interfaces() -> List[str]:
    """Get list of active network interfaces."""
    success, output, _ = run_command(['ip', 'route', 'show'])
    if not success:
        return []
    
    networks = []
    for line in output.split('\n'):
        if 'dev' in line and '/' in line:
            # Extract network from routes like "192.168.1.0/24 dev wlan0"
            parts = line.split()
            for part in parts:
                if '/' in part and not part.startswith('169.254'):
                    try:
                        network = ipaddress.IPv4Network(part, strict=False)
                        networks.append(str(network))
                    except:
                        pass
    
    return list(set(networks))


def ping_host(ip: str) -> bool:
    """Ping a single host."""
    success, _, _ = run_command(['ping', '-c', '1', '-W', '1', ip])
    return success


def scan_network_ping(network: str) -> None:
    """Scan network using ping method."""
    print(f"🔍 Scanning {network} with ping...")
    
    try:
        net = ipaddress.IPv4Network(network)
        hosts = list(net.hosts())
        
        # Use ThreadPoolExecutor for concurrent pinging
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = {executor.submit(ping_host, str(ip)): ip for ip in hosts}
            
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                completed += 1
                if completed % 50 == 0:
                    print(f"   Scanned {completed}/{len(hosts)} hosts...")
                    
    except Exception as e:
        print(f"❌ Error scanning {network}: {e}")


def scan_with_nmap(network: str) -> Optional[str]:
    """Scan network using nmap if available."""
    # Check if nmap is installed
    success, _, _ = run_command(['which', 'nmap'])
    if not success:
        return None
    
    print(f"🔍 Scanning {network} with nmap...")
    success, output, error = run_command([
        'nmap', '-sn', network
    ], timeout=60)
    
    if success:
        return output
    else:
        print(f"❌ nmap scan failed: {error}")
        return None


def get_arp_table() -> Dict[str, str]:
    """Get current ARP table as IP -> MAC mapping."""
    arp_table = {}
    
    # Try different ARP commands
    for cmd in [['arp', '-a'], ['ip', 'neigh', 'show']]:
        success, output, _ = run_command(cmd)
        if success:
            for line in output.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                # Parse different ARP output formats
                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                mac_match = re.search(r'([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}', line)
                
                if ip_match and mac_match:
                    ip = ip_match.group(1)
                    mac = mac_match.group(0).lower().replace('-', ':')
                    arp_table[ip] = mac
            
            if arp_table:
                break
    
    return arp_table


def find_mac_in_arp(target_mac: str) -> List[str]:
    """Find IP addresses associated with target MAC address."""
    target_mac = target_mac.lower().replace('-', ':')
    arp_table = get_arp_table()
    
    found_ips = []
    for ip, mac in arp_table.items():
        if mac == target_mac:
            found_ips.append(ip)
    
    return found_ips


def scan_specific_network(network: str, target_mac: str) -> List[str]:
    """Scan a specific network for target MAC."""
    print(f"\n🎯 Scanning network: {network}")
    
    # First try nmap scan
    nmap_output = scan_with_nmap(network)
    
    # Then do ping scan
    scan_network_ping(network)
    
    # Wait a bit for ARP table to populate
    time.sleep(2)
    
    # Check ARP table
    found_ips = find_mac_in_arp(target_mac)
    
    return found_ips


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Find device by MAC address on network")
    parser.add_argument('mac', help='MAC address to find (e.g., 2c:cf:67:87:6a:d5)')
    parser.add_argument('-n', '--network', help='Specific network to scan (e.g., 192.168.1.0/24)')
    parser.add_argument('--all-networks', action='store_true', help='Scan all detected networks')
    
    args = parser.parse_args()
    
    target_mac = args.mac.lower().replace('-', ':')
    
    print("🔍 MAC Address Device Finder")
    print("=" * 40)
    print(f"🎯 Looking for MAC: {target_mac}")
    
    # Check current ARP table first
    print("\n📋 Checking current ARP table...")
    found_ips = find_mac_in_arp(target_mac)
    
    if found_ips:
        print(f"✅ Found device in ARP table!")
        for ip in found_ips:
            print(f"   📍 IP: {ip}")
        return 0
    
    print("❌ Device not found in current ARP table")
    
    # Determine networks to scan
    if args.network:
        networks = [args.network]
    elif args.all_networks:
        networks = get_network_interfaces()
        if not networks:
            print("❌ No networks detected")
            return 1
        print(f"🌐 Detected networks: {', '.join(networks)}")
    else:
        # Default common networks
        networks = [
            '192.168.1.0/24',
            '192.168.0.0/24', 
            '192.168.41.0/24',
            '10.0.0.0/24',
            '172.16.0.0/24'
        ]
        print(f"🌐 Scanning common networks: {', '.join(networks)}")
    
    # Scan networks
    all_found_ips = []
    for network in networks:
        found_ips = scan_specific_network(network, target_mac)
        all_found_ips.extend(found_ips)
    
    # Final results
    print("\n" + "=" * 40)
    if all_found_ips:
        print(f"✅ Device found!")
        for ip in set(all_found_ips):
            print(f"   📍 IP Address: {ip}")
            
            # Try to get more info about the device
            success, output, _ = run_command(['ping', '-c', '1', ip])
            if success:
                print(f"   ✅ Device responds to ping")
            
            # Try to get hostname
            success, output, _ = run_command(['nslookup', ip])
            if success and 'name =' in output:
                hostname = output.split('name =')[1].strip().split()[0]
                print(f"   🏷️  Hostname: {hostname}")
    else:
        print("❌ Device not found on any scanned networks")
        print("\n💡 Troubleshooting tips:")
        print("   - Make sure the device is powered on and connected")
        print("   - Check if the MAC address is correct")
        print("   - Try scanning with --all-networks")
        print("   - The device might be on a different network")
        print("   - Some devices don't respond to ping")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 