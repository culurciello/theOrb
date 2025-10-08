#!/usr/bin/env python3
"""
Test script to run the application in CPU-only mode for testing uploads.
"""
import os
import sys

# Force CPU-only mode by hiding CUDA devices
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'

# Import and run the main app
from app import create_app

if __name__ == '__main__':
    print("🔧 Starting application in CPU-only mode for testing...")
    print("🚫 CUDA disabled via CUDA_VISIBLE_DEVICES=''")

    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)