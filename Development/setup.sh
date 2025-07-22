#!/bin/bash

echo ""
echo "========================================"
echo "  🎬 Render Farm Professional Setup"
echo "========================================"
echo ""

echo "Choose installation method:"
echo ""
echo "[1] Quick Install (Development)"
echo "[2] Build Professional Installer"
echo "[3] Exit"
echo ""

read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "🚀 Starting Quick Installation..."
        echo ""
        python3 setup_installer.py
        ;;
    2)
        echo ""
        echo "🏗️ Building Professional Installer..."
        echo ""
        python3 build_installer.py
        ;;
    3)
        echo ""
        echo "👋 Goodbye!"
        exit 0
        ;;
    *)
        echo ""
        echo "❌ Invalid choice. Please enter 1, 2, or 3."
        exit 1
        ;;
esac

echo ""
echo "✅ Setup complete!"