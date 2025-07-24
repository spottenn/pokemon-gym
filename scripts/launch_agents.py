#!/usr/bin/env python3
"""
Launch multiple Claude Code instances with different specialized prompts.
Each instance gets its own copy of the project in the parent directory.
"""

import json
import os
import subprocess
import sys
import shutil
import argparse
from pathlib import Path
from typing import Dict, List
import time
import uuid

def load_prompts(prompts_file: str) -> List[Dict]:
    """Load prompts from JSON file."""
    with open(prompts_file, 'r') as f:
        data = json.load(f)
    return data['prompts']

def get_project_root() -> Path:
    """Get the current project root directory."""
    return Path(__file__).parent.parent

def get_parent_dir() -> Path:
    """Get the parent directory where new instances will be created."""
    return get_project_root().parent

def create_project_instance(agent_id: str, source_dir: Path, parent_dir: Path) -> Path:
    """Create a new project instance for an agent."""
    instance_name = f"pokemon-gym-{agent_id}"
    instance_path = parent_dir / instance_name
    
    # Remove existing instance if it exists
    if instance_path.exists():
        print(f"Removing existing instance: {instance_path}")
        shutil.rmtree(instance_path)
    
    print(f"Creating project instance: {instance_path}")
    
    # Copy the entire project including .git for version control
    # Only ignore runtime/build artifacts
    shutil.copytree(source_dir, instance_path, 
                   ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'node_modules', '.DS_Store'))
    
    return instance_path

def setup_instance_environment(instance_path: Path, source_dir: Path) -> bool:
    """Set up the Python environment for the instance by copying from source."""
    print(f"Setting up environment for {instance_path.name}")
    
    source_venv = source_dir / '.venv'
    target_venv = instance_path / '.venv'
    
    # Check if source has a working venv
    if not source_venv.exists():
        print(f"No source virtual environment found at {source_venv}")
        print("Please ensure the main project has a working .venv with dependencies installed")
        return False
    
    # Remove target venv if it exists (from previous copy)
    if target_venv.exists():
        shutil.rmtree(target_venv)
    
    # Copy the entire virtual environment
    print(f"Copying virtual environment from {source_venv}")
    shutil.copytree(source_venv, target_venv)
    
    return True

def launch_claude_instance(instance_path: Path, prompt: str, session_id: str) -> subprocess.Popen:
    """Launch a Claude Code instance with the given prompt."""
    print(f"Launching Claude Code for {instance_path.name}")
    
    # Claude command with options for autonomous operation
    claude_cmd = [
        'claude',
        '--dangerously-skip-permissions',  # Skip permission prompts
        '--session-id', session_id,
        '--add-dir', str(instance_path),
        prompt
    ]
    
    # Launch Claude in the instance directory
    process = subprocess.Popen(
        claude_cmd,
        cwd=str(instance_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    return process

def generate_session_id(agent_id: str) -> str:
    """Generate a session ID for the agent."""
    return str(uuid.uuid4())

def save_agent_info(agents_info: List[Dict], info_file: Path):
    """Save agent information to file."""
    with open(info_file, 'w') as f:
        json.dump(agents_info, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description='Launch Claude Code agents for Pokemon-Gym analysis')
    parser.add_argument('--agents', nargs='+', help='Specific agent IDs to launch (default: all)')
    parser.add_argument('--skip-setup', action='store_true', help='Skip environment setup (use existing instances)')
    parser.add_argument('--prompts-file', default='prompts.json', help='Path to prompts JSON file')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    
    args = parser.parse_args()
    
    # Get directories
    project_root = get_project_root()
    parent_dir = get_parent_dir()
    scripts_dir = project_root / 'scripts'
    prompts_file = scripts_dir / args.prompts_file
    
    if not prompts_file.exists():
        print(f"Error: Prompts file not found: {prompts_file}")
        sys.exit(1)
    
    # Load prompts
    prompts = load_prompts(str(prompts_file))
    
    # Filter agents if specified
    if args.agents:
        prompts = [p for p in prompts if p['id'] in args.agents]
        if not prompts:
            print(f"Error: No matching agents found for: {args.agents}")
            sys.exit(1)
    
    if args.dry_run:
        print("DRY RUN - Would launch the following agents:")
        for prompt_config in prompts:
            print(f"  - {prompt_config['name']} ({prompt_config['id']})")
        return
    
    agents_info = []
    
    for prompt_config in prompts:
        agent_id = prompt_config['id']
        agent_name = prompt_config['name']
        prompt_text = prompt_config['prompt']
        
        print(f"\n{'='*60}")
        print(f"Setting up agent: {agent_name} ({agent_id})")
        print(f"{'='*60}")
        
        # Create project instance
        if not args.skip_setup:
            instance_path = create_project_instance(agent_id, project_root, parent_dir)
            
            # Setup environment by copying from source
            if not setup_instance_environment(instance_path, project_root):
                print(f"Failed to setup environment for {agent_id}")
                continue
        else:
            instance_path = parent_dir / f"pokemon-gym-{agent_id}"
            if not instance_path.exists():
                print(f"Instance not found: {instance_path}")
                continue
        
        # Generate session ID
        session_id = generate_session_id(agent_id)
        
        # Launch Claude instance
        try:
            process = launch_claude_instance(instance_path, prompt_text, session_id)
            
            agents_info.append({
                'id': agent_id,
                'name': agent_name,
                'session_id': session_id,
                'instance_path': str(instance_path),
                'pid': process.pid,
                'started_at': time.time()
            })
            
            print(f"✅ Launched {agent_name}")
            print(f"   Session ID: {session_id}")
            print(f"   PID: {process.pid}")
            print(f"   Instance: {instance_path}")
            
            # Small delay between launches
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Failed to launch {agent_name}: {e}")
    
    # Save agent information
    info_file = parent_dir / 'claude_agents.json'
    save_agent_info(agents_info, info_file)
    
    print(f"\n{'='*60}")
    print(f"Launched {len(agents_info)} agents")
    print(f"Agent info saved to: {info_file}")
    print(f"Use manage_agents.py to monitor and control the agents")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()