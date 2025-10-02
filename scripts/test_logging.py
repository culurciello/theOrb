#!/usr/bin/env python3
"""Test script to verify logging is working"""
import logging

# Configure logging the same way as app.py
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger('orb')

# Test various log messages
logger.info("📨 USER MESSAGE | User: testuser | Collection: None | Agent: auto | Message: What is the weather?...")
logger.info("🤖 AGENT DETECTED | Agent: basic")
logger.info("⚙️ AGENT PROCESSING | Agent: basic | Collection: None")
logger.info("🔧 TOOL CALL | Tool: get_datetime | Parameters: {'format': 'human'}")
logger.info("✅ TOOL SUCCESS | Tool: get_datetime | Result: {'success': True, 'datetime': '2025-10-02 12:00:00'}...")
logger.info("🤖 LLM REQUEST | Agent: Basic Agent | Model: GPT-4 (gpt-4) | Message: What is the weather?...")
logger.info("💬 LLM RESPONSE | Agent: Basic Agent | Model: GPT-4 (gpt-4) | Length: 150 chars")
logger.info("✅ AGENT RESPONSE | Agent: basic | Length: 150 chars | Verified: None")

print("\n✅ Logging test complete! Check logs/app.log")
