#!/usr/bin/env python3
"""
Test script to verify the agent management system works correctly.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

def test_prompts_loading():
    """Test that prompts can be loaded correctly."""
    print("Testing prompts loading...")
    
    scripts_dir = Path(__file__).parent
    prompts_file = scripts_dir / 'prompts.json'
    
    with open(prompts_file, 'r') as f:
        data = json.load(f)
    
    prompts = data['prompts']
    print(f"✅ Loaded {len(prompts)} prompts successfully")
    
    # Verify all required fields
    for prompt in prompts:
        required_fields = ['name', 'id', 'description', 'prompt']
        for field in required_fields:
            if field not in prompt:
                print(f"❌ Missing field '{field}' in prompt: {prompt.get('name', 'Unknown')}")
                return False
    
    print("✅ All prompts have required fields")
    return True

def test_dry_run():
    """Test dry run functionality."""
    print("\nTesting dry run functionality...")
    
    cmd = [sys.executable, 'scripts/launch_agents.py', '--dry-run']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Dry run failed: {result.stderr}")
        return False
    
    if "DRY RUN" in result.stdout:
        print("✅ Dry run executed successfully")
        return True
    else:
        print(f"❌ Unexpected dry run output: {result.stdout}")
        return False

def test_manage_help():
    """Test management script help."""
    print("\nTesting management script help...")
    
    cmd = [sys.executable, 'scripts/manage_agents.py', '--help']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Management script help failed: {result.stderr}")
        return False
    
    if "Manage Claude Code agents" in result.stdout:
        print("✅ Management script help works")
        return True
    else:
        print(f"❌ Unexpected help output: {result.stdout}")
        return False

def test_single_agent_selection():
    """Test single agent selection."""
    print("\nTesting single agent selection...")
    
    cmd = [sys.executable, 'scripts/launch_agents.py', '--agents', 'claude_code_auditor', '--dry-run']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Single agent selection failed: {result.stderr}")
        return False
    
    if "Claude Code Auditor (claude_code_auditor)" in result.stdout:
        print("✅ Single agent selection works")
        return True
    else:
        print(f"❌ Single agent not found in output: {result.stdout}")
        return False

def main():
    """Run all tests."""
    print("Running agent management system tests...")
    print("=" * 60)
    
    tests = [
        test_prompts_loading,
        test_dry_run,
        test_manage_help,
        test_single_agent_selection
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! The agent management system is ready to use.")
        print("\nNext steps:")
        print("1. Run: python scripts/launch_agents.py --agents claude_code_auditor")
        print("2. Wait for setup to complete (may take several minutes)")
        print("3. Monitor: python scripts/manage_agents.py list")
    else:
        print("❌ Some tests failed. Please check the issues above.")
        sys.exit(1)

if __name__ == '__main__':
    main()