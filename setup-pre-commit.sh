#!/bin/bash
# Setup script for pre-commit hooks

set -e

echo "🔧 Setting up pre-commit hooks for Kartograph..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found. Please install Python 3."
    exit 1
fi

# Check if Node.js is installed (for app/ TypeScript checks)
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not found. Please install Node.js."
    exit 1
fi

# Install pre-commit
echo "📦 Installing pre-commit..."
pip install pre-commit

# Install app dependencies (needed for TypeScript/ESLint hooks)
echo "📦 Installing app dependencies..."
cd app
npm install
cd ..

# Install pre-commit hooks
echo "🪝 Installing git hooks..."
pre-commit install

# Generate secrets baseline (to avoid false positives)
echo "🔐 Generating secrets baseline..."
if command -v detect-secrets &> /dev/null; then
    detect-secrets scan --baseline .secrets.baseline
else
    # If detect-secrets isn't installed yet, let pre-commit install it
    echo "Installing detect-secrets via pre-commit..."
    pre-commit run detect-secrets --all-files || true
fi

# Run pre-commit on all files to verify setup
echo "✅ Running pre-commit on all files..."
pre-commit run --all-files || echo "⚠️  Some checks failed. Review output above and fix issues."

echo ""
echo "✅ Pre-commit setup complete!"
echo ""
echo "ℹ️  Pre-commit will now run automatically on git commit."
echo "ℹ️  To run manually: pre-commit run --all-files"
echo "ℹ️  To skip hooks (not recommended): git commit --no-verify"
