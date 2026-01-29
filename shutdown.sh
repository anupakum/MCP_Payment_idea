#!/bin/bash
# Dispute Resolution System - Shutdown Script
# This script stops all PM2 services

echo "========================================"
echo "Stopping Dispute Resolution System"
echo "========================================"
echo ""

# Check if PM2 is installed
if ! command -v pm2 &> /dev/null; then
    echo "ERROR: PM2 is not installed"
    echo "Services cannot be stopped without PM2"
    exit 1
fi

# Show current status
echo "Current PM2 status:"
pm2 status

echo ""
echo "Stopping all PM2 services..."

# Stop all services
pm2 stop all

echo ""
echo "Deleting all PM2 services..."

# Delete all services
pm2 delete all

echo ""
echo "Saving PM2 process list..."
pm2 save --force

echo ""
echo "========================================"
echo "All services stopped and removed"
echo "========================================"
echo ""
echo "To restart services, run: ./startup.sh"
echo ""
