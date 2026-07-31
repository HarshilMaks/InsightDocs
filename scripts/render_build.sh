#!/usr/bin/env bash
# Render Build Script for Native Python Deployments
set -o errexit

echo "=== Building backend dependencies ==="
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "=== Build Complete ==="
