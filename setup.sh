#!/bin/bash

# RTK-VL Robot Setup Script
# Creates venv, installs requirements, and sets up autocommit service

set -e  # Exit on any error

echo "🤖 RTK-VL Robot Project Setup"
echo "=============================="

# Get project directory
PROJECT_DIR=$(pwd)
DEVICE_NAME=$(hostname)
BRANCH_NAME="robot-${DEVICE_NAME}"

echo "📍 Project Directory: $PROJECT_DIR"
echo "🖥️  Device Name: $DEVICE_NAME"
echo "🌿 Branch Name: $BRANCH_NAME"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check required tools
echo "🔍 Checking required tools..."

if ! command_exists python3; then
    echo "⚠️  Python3 not found. Installing Python3..."
    
    # Detect package manager and install Python
    if command_exists apt; then
        echo "📦 Using apt package manager..."
        sudo apt update
        sudo apt install -y python3 python3-pip python3-venv python3-dev
        echo "✅ Python3 installed successfully"
    elif command_exists yum; then
        echo "📦 Using yum package manager..."
        sudo yum install -y python3 python3-pip python3-venv python3-devel
        echo "✅ Python3 installed successfully"
    elif command_exists dnf; then
        echo "📦 Using dnf package manager..."
        sudo dnf install -y python3 python3-pip python3-venv python3-devel
        echo "✅ Python3 installed successfully"
    elif command_exists pacman; then
        echo "📦 Using pacman package manager..."
        sudo pacman -S --noconfirm python python-pip python-virtualenv
        echo "✅ Python3 installed successfully"
    else
        echo "❌ Unable to detect package manager. Please install Python3 manually:"
        echo "   - Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
        echo "   - CentOS/RHEL: sudo yum install python3 python3-pip python3-venv"
        echo "   - Fedora: sudo dnf install python3 python3-pip python3-venv"
        echo "   - Arch: sudo pacman -S python python-pip python-virtualenv"
        exit 1
    fi
    
    # Verify installation
    if ! command_exists python3; then
        echo "❌ Python3 installation failed. Please install manually."
        exit 1
    fi
else
    echo "✅ Python3 found"
fi

if ! command_exists git; then
    echo "⚠️  Git not found. Installing Git..."
    
    # Detect package manager and install Git
    if command_exists apt; then
        sudo apt install -y git
    elif command_exists yum; then
        sudo yum install -y git
    elif command_exists dnf; then
        sudo dnf install -y git
    elif command_exists pacman; then
        sudo pacman -S --noconfirm git
    else
        echo "❌ Unable to detect package manager. Please install Git manually."
        exit 1
    fi
    
    # Verify installation
    if ! command_exists git; then
        echo "❌ Git installation failed. Please install manually."
        exit 1
    else
        echo "✅ Git installed successfully"
    fi
else
    echo "✅ Git found"
fi

echo "✅ All required tools found"
echo ""

# Initialize git repository if not already initialized
if [ ! -d ".git" ]; then
    echo "📦 Initializing Git repository..."
    git init
    git add .
    git commit -m "Initial commit: RTK-VL Robot project setup"
    echo "✅ Git repository initialized"
else
    echo "✅ Git repository already exists"
fi

# Create device-specific branch
echo "🌿 Setting up device branch: $BRANCH_NAME"
if git show-ref --verify --quiet refs/heads/$BRANCH_NAME; then
    echo "✅ Branch $BRANCH_NAME already exists"
    git checkout $BRANCH_NAME
else
    git checkout -b $BRANCH_NAME
    echo "✅ Created and switched to branch $BRANCH_NAME"
fi
echo ""

# Create Python virtual environment
echo "🐍 Setting up Python virtual environment..."
if [ -d "venv" ]; then
    echo "✅ Virtual environment already exists"
else
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📦 Installing requirements..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Requirements installed successfully"
else
    echo "⚠️  requirements.txt not found, skipping package installation"
fi
echo ""

# Create autocommit service script
echo "⚙️  Creating autocommit service script..."
cat > scripts/autocommit_service.py << 'EOF'
#!/usr/bin/env python3
"""
Autocommit Service Script
Runs every 10 minutes to commit changes to device-specific branch
"""

import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return success status."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    # Get project directory from environment or use current directory
    project_dir = os.environ.get('RTK_PROJECT_DIR', os.getcwd())
    device_name = os.environ.get('RTK_DEVICE_NAME', 'unknown')
    branch_name = f"robot-{device_name}"
    
    print(f"🤖 RTK-VL Robot Autocommit Service")
    print(f"📁 Project: {project_dir}")
    print(f"🌿 Branch: {branch_name}")
    
    os.chdir(project_dir)
    
    # Check if there are changes
    success, output, _ = run_command(['git', 'status', '--porcelain'])
    if not success:
        print("❌ Failed to check git status")
        return 1
    
    if not output.strip():
        print("✅ No changes to commit")
        return 0
    
    print("📝 Changes detected, committing...")
    
    # Ensure we're on the correct branch
    run_command(['git', 'checkout', branch_name])
    
    # Add all changes
    success, _, error = run_command(['git', 'add', '.'])
    if not success:
        print(f"❌ Failed to add files: {error}")
        return 1
    
    # Create commit message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"Auto-commit from {device_name}: {timestamp}"
    
    # Commit changes
    success, _, error = run_command(['git', 'commit', '-m', commit_msg])
    if not success:
        print(f"❌ Failed to commit: {error}")
        return 1
    
    print(f"✅ Changes committed: {commit_msg}")
    
    # Try to push (don't fail if remote doesn't exist)
    success, output, error = run_command(['git', 'push', 'origin', branch_name])
    if success:
        print("✅ Changes pushed to remote")
    else:
        print(f"⚠️  Push failed (remote might not be configured): {error}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
EOF

chmod +x scripts/autocommit_service.py
echo "✅ Autocommit service script created"
echo ""

# Create systemd service file
echo "⚙️  Creating systemd service..."
SERVICE_NAME="rtk-robot-autocommit"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=RTK-VL Robot Autocommit Service
After=network.target

[Service]
Type=oneshot
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=RTK_PROJECT_DIR=$PROJECT_DIR
Environment=RTK_DEVICE_NAME=$DEVICE_NAME
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/scripts/autocommit_service.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Systemd service file created: $SERVICE_FILE"

# Create systemd timer file
TIMER_FILE="/etc/systemd/system/${SERVICE_NAME}.timer"

sudo tee $TIMER_FILE > /dev/null << EOF
[Unit]
Description=RTK-VL Robot Autocommit Timer
Requires=${SERVICE_NAME}.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=10min
Persistent=true

[Install]
WantedBy=timers.target
EOF

echo "✅ Systemd timer file created: $TIMER_FILE"
echo ""

# Enable and start the service
echo "🚀 Enabling and starting autocommit service..."
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}.timer
sudo systemctl start ${SERVICE_NAME}.timer

echo "✅ Autocommit service enabled and started"
echo ""

# Create desktop shortcut for easy access
echo "🖥️  Creating desktop shortcuts..."
mkdir -p ~/.local/share/applications

cat > ~/.local/share/applications/rtk-robot.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=RTK-VL Robot
Comment=Open RTK-VL Robot project in terminal
Exec=gnome-terminal --working-directory=$PROJECT_DIR
Icon=applications-system
Terminal=false
Categories=Development;
EOF

echo "✅ Desktop shortcut created"
echo ""

# Create useful aliases
echo "⚙️  Creating useful aliases..."
cat >> ~/.bashrc << EOF

# RTK-VL Robot aliases
alias rtk-cd='cd $PROJECT_DIR'
alias rtk-activate='source $PROJECT_DIR/venv/bin/activate'
alias rtk-status='sudo systemctl status $SERVICE_NAME.timer'
alias rtk-logs='sudo journalctl -u $SERVICE_NAME.service -f'
alias rtk-restart='sudo systemctl restart $SERVICE_NAME.timer'
alias rtk-commit='cd $PROJECT_DIR && python scripts/autocommit.py'
EOF

echo "✅ Aliases added to ~/.bashrc"
echo ""

# Final status check
echo "📊 Setup Summary:"
echo "=================="
echo "✅ Project Directory: $PROJECT_DIR"
echo "✅ Device Name: $DEVICE_NAME"
echo "✅ Git Branch: $BRANCH_NAME"
echo "✅ Virtual Environment: $PROJECT_DIR/venv"
echo "✅ Autocommit Service: $SERVICE_NAME"
echo "✅ Commit Interval: Every 10 minutes"
echo ""

echo "🎉 Setup Complete!"
echo ""

echo "💡 Useful Commands:"
echo "==================="
echo "rtk-cd          - Navigate to project directory"
echo "rtk-activate    - Activate Python virtual environment"
echo "rtk-status      - Check autocommit service status"
echo "rtk-logs        - View autocommit service logs"
echo "rtk-restart     - Restart autocommit service"
echo "rtk-commit      - Manual commit"
echo ""

echo "🔍 Service Status:"
sudo systemctl status ${SERVICE_NAME}.timer --no-pager

echo ""
echo "📝 Next Steps:"
echo "1. Configure your robot hardware in config/robot_config.yaml"
echo "2. Test the system with: python src/main.py"
echo "3. Check autocommit logs with: rtk-logs"
echo "4. The system will auto-commit every 10 minutes to branch: $BRANCH_NAME"
echo ""

# Reload bashrc for current session
echo "💫 Reloading bash configuration..."
source ~/.bashrc 2>/dev/null || echo "Please run 'source ~/.bashrc' or restart terminal for aliases"

echo "🚀 RTK-VL Robot is ready to go!" 