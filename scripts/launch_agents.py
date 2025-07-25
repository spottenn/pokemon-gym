#!/usr/bin/env python3
"""
Simple tmux-based agent launcher with auto-generated agent selection.
"""

import json
import subprocess
import sys
import shutil
import argparse
from pathlib import Path
from typing import List, Dict, Optional

def load_prompts(prompts_file: str) -> List[Dict]:
    """Load prompts from JSON file."""
    with open(prompts_file, 'r') as f:
        data = json.load(f)
    return data['prompts']

def list_available_agents(prompts: List[Dict]):
    """Show available agents from prompts file."""
    print("\nAvailable agents:")
    for i, prompt in enumerate(prompts, 1):
        print(f"  {i}. {prompt['name']} ({prompt['id']})")
    print()

def select_agents_by_args(prompts: List[Dict], agent_args: list) -> List[Dict]:
    """Select agents by command-line arguments (IDs or 'all')."""
    if not agent_args or agent_args == ['all']:
        return prompts
    
    selected = []
    for arg in agent_args:
        # Try to find by ID
        agent = next((p for p in prompts if p['id'] == arg), None)
        if agent:
            selected.append(agent)
        else:
            print(f"⚠️  Agent '{arg}' not found. Available agents:")
            for p in prompts:
                print(f"  {p['id']}")
    
    return selected

def select_agents_interactive(prompts: List[Dict]) -> List[Dict]:
    """Interactive agent selection."""
    list_available_agents(prompts)
    
    while True:
        choice = input("Select agents (comma-separated numbers, 'all', or 'q' to quit): ").strip()
        
        if choice.lower() == 'q':
            sys.exit(0)
        elif choice.lower() == 'all':
            return prompts
        else:
            try:
                indices = [int(x.strip()) - 1 for x in choice.split(',')]
                selected = [prompts[i] for i in indices if 0 <= i < len(prompts)]
                if selected:
                    return selected
                else:
                    print("Invalid selection. Try again.")
            except (ValueError, IndexError):
                print("Invalid format. Use numbers like '1,3,5' or 'all'.")

def create_project_copy(agent_id: str, source_dir: Path) -> Path:
    """Create a project copy for the agent."""
    parent_dir = source_dir.parent
    instance_name = f"pokemon-gym-{agent_id}"
    instance_path = parent_dir / instance_name
    
    # Remove existing copy if it exists
    if instance_path.exists():
        print(f"Removing existing copy: {instance_path}")
        shutil.rmtree(instance_path)
    
    print(f"Creating project copy: {instance_path}")
    shutil.copytree(source_dir, instance_path, 
                   ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
    
    return instance_path

def launch_agent_in_tmux(agent: Dict, project_root: Path, custom_prompt: Optional[str] = None, append_text: Optional[str] = None):
    """Launch a single agent in its own tmux session with project copy."""
    session_name = f"agent-{agent['id']}"
    
    # Check if session already exists
    try:
        subprocess.run(['tmux', 'has-session', '-t', session_name], 
                      check=True, capture_output=True)
        print(f"⚠️  Session '{session_name}' already exists. Use 'tmux attach -t {session_name}' to connect.")
        return False
    except subprocess.CalledProcessError:
        pass  # Session doesn't exist, which is what we want
    
    # Create project copy for this agent
    try:
        instance_path = create_project_copy(agent['id'], project_root)
    except Exception as e:
        print(f"❌ Failed to create project copy for {agent['name']}: {e}")
        return False
    
    # Determine the final prompt to use
    if custom_prompt:
        final_prompt = custom_prompt
    else:
        final_prompt = agent['prompt']
        if append_text:
            final_prompt = f"{final_prompt}\n\n{append_text}"
    
    # Create new tmux session and run a script that executes multiple claude commands
    # Use heredoc to avoid quote escaping issues
    script_content = f"""#!/bin/bash

# First command - initial prompt (non-interactive)
claude --dangerously-skip-permissions -p << 'PROMPT1'
{final_prompt}
PROMPT1

# Second command - validation check (non-interactive)  
claude --dangerously-skip-permissions --continue -p << 'PROMPT2'
Have you thoroughly tested and validated your claims/audits, including end to end?
PROMPT2

# Third command - completion check (interactive)
claude --dangerously-skip-permissions --continue << 'PROMPT3'
Here is your original prompt:

{final_prompt}

Have you fully accomplished the goals? If not, please keep going autonomously until you have and you have tested your work end to end
PROMPT3
"""
    
    # Write the script to the instance directory
    script_path = instance_path / 'run_agent.sh'
    with open(script_path, 'w') as f:
        f.write(script_content)
    script_path.chmod(0o755)
    
    # Create tmux session that runs the script
    claude_cmd = [
        'tmux', 'new-session', '-d', '-s', session_name,
        'bash', str(script_path)
    ]
    
    try:
        subprocess.run(claude_cmd, check=True, cwd=str(instance_path))
        print(f"✅ Launched {agent['name']} in tmux session '{session_name}'")
        print(f"   Working in: {instance_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to launch {agent['name']}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Simple tmux-based agent launcher.")
    parser.add_argument('agents', nargs='*', help='Agent IDs to launch (or "all")')
    parser.add_argument('-p', '--prompt', type=str, help='Custom prompt to use instead of predefined prompt')
    parser.add_argument('-a', '--append', type=str, help='Text to append to the predefined prompt')
    
    args = parser.parse_args()
    
    # Handle help manually for backward compatibility
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        parser.print_help()
        print("\nExamples:")
        print("  python launch_agents.py                    # Interactive selection")
        print("  python launch_agents.py test_agent         # Launch specific agent")
        print("  python launch_agents.py test_agent claude_code_auditor  # Launch multiple")
        print("  python launch_agents.py all                # Launch all agents")
        print("  python launch_agents.py test_agent -p \"Custom prompt here\"  # Custom prompt")
        print("  python launch_agents.py claude_code_auditor -a \"Also audit the blink component\"  # Append text")
        print("\nAfter launching:")
        print("  - List sessions: tmux list-sessions")
        print("  - Attach to agent: tmux attach -t agent-<id>")
        print("  - Detach: Ctrl+B then D")
        print("  - Kill session: tmux kill-session -t agent-<id>")
        print("  - Manage: python manage_agents.py list")
        sys.exit(0)
    
    # Get project paths
    project_root = Path(__file__).parent.parent
    prompts_file = project_root / 'scripts' / 'prompts.json'
    
    if not prompts_file.exists():
        print(f"Error: Prompts file not found: {prompts_file}")
        sys.exit(1)
    
    # Load and select agents
    prompts = load_prompts(str(prompts_file))
    
    # Use command-line args if provided, otherwise interactive
    if args.agents:
        selected_agents = select_agents_by_args(prompts, args.agents)
    else:
        selected_agents = select_agents_interactive(prompts)
    
    if not selected_agents:
        print("No agents selected.")
        sys.exit(0)
    
    print(f"\nLaunching {len(selected_agents)} agents...")
    
    launched = 0
    for agent in selected_agents:
        if launch_agent_in_tmux(agent, project_root, args.prompt, args.append):
            launched += 1
    
    print(f"\n✅ Successfully launched {launched}/{len(selected_agents)} agents")
    print("\nUseful tmux commands:")
    print("  tmux list-sessions           # List all sessions")
    print("  tmux attach -t agent-<id>    # Attach to specific agent")
    print("  tmux kill-session -t agent-<id>  # Stop specific agent")
    print("  python manage_agents.py      # Use management script")

if __name__ == '__main__':
    main()