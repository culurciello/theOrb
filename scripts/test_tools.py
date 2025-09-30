#!/usr/bin/env python3
"""
Test script to demonstrate the AI agent tools functionality.
"""

from ai_agents.tools import ToolManager, DateTimeTool, CalculatorTool
from ai_agents.basic_agent import BasicAgent


def test_individual_tools():
    """Test each tool individually."""
    print("🔧 Testing Individual Tools")
    print("=" * 40)

    # Test DateTime Tool
    print("\n📅 DateTimeTool Tests:")
    dt_tool = DateTimeTool()

    # Test different formats
    test_cases = [
        {"format": "human"},
        {"format": "iso"},
        {"format": "date"},
        {"format": "time"},
        {"component": "year"},
        {"component": "weekday"}
    ]

    for params in test_cases:
        result = dt_tool.execute(**params)
        print(f"  {params}: {result}")

    # Test Calculator Tool
    print("\n🧮 CalculatorTool Tests:")
    calc_tool = CalculatorTool()

    expressions = [
        "2 + 3 * 4",
        "sqrt(16)",
        "sin(pi/2)",
        "log10(100)",
        "15 * 23 + 10",
        "2**8"
    ]

    for expr in expressions:
        result = calc_tool.execute(expression=expr)
        print(f"  {expr} = {result.get('result', result)}")


def test_tool_manager():
    """Test the tool manager."""
    print("\n🛠️  Testing Tool Manager")
    print("=" * 40)

    tm = ToolManager()

    print(f"Available tools: {list(tm.get_all_tools().keys())}")
    print("\nTool descriptions:")
    print(tm.get_tools_description())

    # Test tool execution via manager
    print("\nExecuting tools via manager:")

    # DateTime test
    dt_result = tm.execute_tool('get_datetime', {'format': 'human'})
    print(f"Current time: {dt_result}")

    # Calculator test
    calc_result = tm.execute_tool('calculate', {'expression': '2**10'})
    print(f"2^10 = {calc_result}")


def test_basic_agent_integration():
    """Test the basic agent with tool integration."""
    print("\n🤖 Testing Basic Agent Integration")
    print("=" * 40)

    agent = BasicAgent()

    # Mock progress callback
    def progress_callback(status, message):
        print(f"  Progress: {status} - {message}")

    # Test tool call processing
    test_responses = [
        "The current time is: TOOL_CALL: get_datetime({\"format\": \"human\"})",
        "Let me calculate that for you: TOOL_CALL: calculate({\"expression\": \"15 + 25 * 2\"})",
        "Today's date is: TOOL_CALL: get_datetime({\"format\": \"date\"})",
        "The square root of 144 is: TOOL_CALL: calculate({\"expression\": \"sqrt(144)\"})"
    ]

    for response in test_responses:
        print(f"\nOriginal: {response}")
        processed = agent._process_tool_calls(response, progress_callback)
        print(f"Processed: {processed}")


if __name__ == "__main__":
    print("🚀 AI Agent Tools Test Suite")
    print("=" * 50)

    try:
        test_individual_tools()
        test_tool_manager()
        test_basic_agent_integration()

        print("\n✅ All tests completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()