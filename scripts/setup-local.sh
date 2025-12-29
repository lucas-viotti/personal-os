#!/bin/bash
# =============================================================================
# Logbook Local - Setup Script for macOS
# =============================================================================
# This script sets up local scheduling using launchd (macOS's task scheduler)
# 
# Usage: ./setup-local.sh [install|uninstall|test]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$REPO_DIR/logs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

install_launchd() {
    echo_info "Installing Logbook launchd jobs..."
    
    # Create logs directory
    mkdir -p "$LOG_DIR"
    
    # Create LaunchAgents directory if needed
    mkdir -p "$LAUNCHD_DIR"
    
    # Process each plist file
    for plist_template in "$SCRIPT_DIR/launchd/"*.plist; do
        plist_name=$(basename "$plist_template")
        plist_dest="$LAUNCHD_DIR/$plist_name"
        
        echo_info "Installing $plist_name..."
        
        # Replace REPO_PATH placeholder with actual path
        sed "s|REPO_PATH|$REPO_DIR|g" "$plist_template" > "$plist_dest"
        
        # Load the job
        launchctl unload "$plist_dest" 2>/dev/null || true
        launchctl load "$plist_dest"
        
        echo_info "  ✓ Loaded $plist_name"
    done
    
    echo ""
    echo_info "✅ Installation complete!"
    echo ""
    echo "Scheduled jobs:"
    echo "  • Daily Briefing: 8:30 AM (Mon-Fri)"
    echo "  • Daily Closing:  5:50 PM (Mon-Fri)"
    echo "  • Weekly Review:  3:00 PM (Friday)"
    echo ""
    echo "Logs will be written to: $LOG_DIR"
    echo ""
    echo_warn "Don't forget to configure your .env file!"
    echo "  cp $SCRIPT_DIR/env.example $REPO_DIR/.env"
    echo "  # Then edit .env with your credentials"
}

uninstall_launchd() {
    echo_info "Uninstalling Logbook launchd jobs..."
    
    for plist_name in com.logbook.briefing.plist com.logbook.closing.plist com.logbook.weekly.plist; do
        plist_dest="$LAUNCHD_DIR/$plist_name"
        
        if [ -f "$plist_dest" ]; then
            echo_info "Unloading $plist_name..."
            launchctl unload "$plist_dest" 2>/dev/null || true
            rm "$plist_dest"
            echo_info "  ✓ Removed $plist_name"
        fi
    done
    
    echo ""
    echo_info "✅ Uninstallation complete!"
}

test_script() {
    echo_info "Testing Logbook Local script..."
    echo ""
    
    # Check Python
    if command -v python3 &> /dev/null; then
        echo_info "✓ Python3 found: $(python3 --version)"
    else
        echo_error "✗ Python3 not found!"
        exit 1
    fi
    
    # Check .env file
    if [ -f "$REPO_DIR/.env" ]; then
        echo_info "✓ .env file found"
    else
        echo_warn "✗ .env file not found - copy from scripts/env.example"
    fi
    
    # Check Tasks directory
    if [ -d "$REPO_DIR/Tasks" ]; then
        TASK_COUNT=$(ls "$REPO_DIR/Tasks/"*.md 2>/dev/null | wc -l | tr -d ' ')
        echo_info "✓ Tasks directory found ($TASK_COUNT tasks)"
    else
        echo_warn "✗ Tasks directory not found"
    fi
    
    echo ""
    echo_info "Running briefing in dry-run mode..."
    echo ""
    
    # Run the script (it will print to stdout if Slack isn't configured)
    cd "$REPO_DIR"
    python3 "$SCRIPT_DIR/logbook-local.py" briefing
}

show_status() {
    echo_info "Logbook Local Status"
    echo ""
    
    for plist_name in com.logbook.briefing com.logbook.closing com.logbook.weekly; do
        if launchctl list | grep -q "$plist_name"; then
            echo_info "✓ $plist_name is loaded"
        else
            echo_warn "✗ $plist_name is not loaded"
        fi
    done
}

# Main
case "${1:-help}" in
    install)
        install_launchd
        ;;
    uninstall)
        uninstall_launchd
        ;;
    test)
        test_script
        ;;
    status)
        show_status
        ;;
    *)
        echo "Logbook Local - Setup Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  install    Install launchd jobs for automatic scheduling"
        echo "  uninstall  Remove launchd jobs"
        echo "  test       Test the script with current configuration"
        echo "  status     Show status of launchd jobs"
        echo ""
        echo "Before installing, make sure to:"
        echo "  1. Copy env.example to ../.env"
        echo "  2. Fill in your credentials in .env"
        echo "  3. Run '$0 test' to verify everything works"
        ;;
esac

