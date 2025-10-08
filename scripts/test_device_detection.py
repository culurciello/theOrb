#!/usr/bin/env python3
"""
Quick test to verify device detection and CUDA availability.
"""
import os
import torch

print("=== Device Detection Test ===")

# Test 1: Normal CUDA detection
print(f"🔍 CUDA available: {torch.cuda.is_available()}")
print(f"🔍 CUDA device count: {torch.cuda.device_count()}")
if torch.cuda.is_available():
    print(f"🔍 Current CUDA device: {torch.cuda.current_device()}")
    print(f"🔍 Device name: {torch.cuda.get_device_name()}")

print("\n✅ Test complete! To run in CPU-only mode:")
print("   CUDA_VISIBLE_DEVICES='' python app.py")
print("   or")
print("   python test_cpu_only.py")