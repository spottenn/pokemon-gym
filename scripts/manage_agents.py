#!/usr/bin/env python3
"""
Simple tmux-based agent management.
"""

import json
import subprocess
import sys
import shutil
import datetime
from pathlib import Path
from typing import List, Dict

def load_prompts(prompts_file: str) -> List[Dict]:
    """Load prompts from JSON file to get agent info."""
    with open(prompts_file, 'r') as f:
        data = json.load(f)
    return data['prompts']

def get_tmux_sessions() -> List[str]:
    """Get list of active tmux sessions."""
    try:
        result = subprocess.run(['tmux', 'list-sessions', '-F', '#{session_name}'], 
                              capture_output=True, text=True, check=True)
        return [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
    except subprocess.CalledProcessError:
        return []

def get_agent_sessions(prompts: List[Dict]) -> List[Dict]:
    """Get status of all agent sessions."""
    all_sessions = get_tmux_sessions()
    agent_sessions = []
    
    # Track which agent types have running instances
    for prompt in prompts:
        agent_id = prompt['id']
        running_instances = [s for s in all_sessions if s.startswith(f"agent-{agent_id}")]
        
        if running_instances:
            # Multiple instances running
            for session in running_instances:
                instance_id = session.replace(f"agent-{agent_id}-", "") if "-" in session[len(f"agent-{agent_id}"):] else "default"
                agent_sessions.append({
                    'id': agent_id,
                    'name': prompt['name'],
                    'session_name': session,
                    'instance_id': instance_id,
                    'running': True
                })
        else:
            # No instances running
            agent_sessions.append({
                'id': agent_id,
                'name': prompt['name'],
                'session_name': f"agent-{agent_id}",
                'instance_id': None,
                'running': False
            })
    
    # Also check for custom agents
    custom_sessions = [s for s in all_sessions if s.startswith("agent-custom-")]
    for session in custom_sessions:
        instance_id = session.replace("agent-custom-", "")
        agent_sessions.append({
            'id': 'custom',
            'name': 'Custom Agent',
            'session_name': session,
            'instance_id': instance_id,
            'running': True
        })
    
    return agent_sessions

def list_agents(agent_sessions: List[Dict]):
    """List all agents and their status."""
    print(f"\n{'ID':<25} {'Name':<30} {'Instance':<15} {'Status':<10}")
    print(f"{'-'*85}")
    
    for agent in agent_sessions:
        status = "Running" if agent['running'] else "Stopped"
        instance = agent.get('instance_id', 'N/A') if agent['running'] else 'N/A'
        print(f"{agent['id']:<25} {agent['name']:<30} {instance:<15} {status:<10}")
    
    print(f"{'-'*85}")
    running_count = sum(1 for a in agent_sessions if a['running'])
    total_unique = len(set(a['id'] for a in agent_sessions))
    print(f"Total: {total_unique} agent types, {running_count} running instances")

def get_agent_instance_path(agent_id: str, project_root: Path, instance_id: str = None) -> Path:
    """Get the path to an agent's project copy."""
    parent_dir = project_root.parent
    if instance_id:
        return parent_dir / f"pokemon-gym-{agent_id}-{instance_id}"
    else:
        return parent_dir / f"pokemon-gym-{agent_id}"

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

def start_agent(agent_id: str, prompts: List[Dict], project_root: Path) -> bool:
    """Start a specific agent."""
    prompt_config = next((p for p in prompts if p['id'] == agent_id), None)
    if not prompt_config:
        print(f"❌ Agent '{agent_id}' not found in prompts")
        return False
    
    # Generate timestamp for unique instance
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    session_name = f"agent-{agent_id}-{timestamp}"
    
    # Multiple instances are now allowed
    print(f"🚀 Starting new instance of {agent_id} with timestamp {timestamp}")
    
    # Create project copy with timestamp
    try:
        copy_id = f"{agent_id}-{timestamp}"
        instance_path = create_project_copy(copy_id, project_root)
    except Exception as e:
        print(f"❌ Failed to create project copy for {agent_id}: {e}")
        return False
    
    # Launch in tmux using the project copy
    claude_cmd = [
        'tmux', 'new-session', '-d', '-s', session_name,
        'claude', '--dangerously-skip-permissions', '--add-dir', str(instance_path), prompt_config['prompt']
    ]
    
    try:
        subprocess.run(claude_cmd, check=True, cwd=str(instance_path))
        print(f"✅ Started {prompt_config['name']} (session: {session_name})")
        print(f"   Working in: {instance_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start {agent_id}: {e}")
        return False

def cleanup_agent_work(agent_id: str, project_root: Path, instance_id: str = None) -> bool:
    """Create branch with agent's work and push it."""
    instance_path = get_agent_instance_path(agent_id, project_root, instance_id)
    
    if not instance_path.exists():
        print(f"No project copy found for {agent_id}")
        return True
    
    try:
        # Check if there are any changes
        result = subprocess.run(['git', 'status', '--porcelain'], 
                               cwd=str(instance_path), capture_output=True, text=True)
        
        if not result.stdout.strip():
            print(f"No changes found for {agent_id}, skipping branch creation")
            shutil.rmtree(instance_path)
            print(f"Deleted project copy: {instance_path}")
            return True
        
        # Create branch name with instance timestamp
        branch_suffix = instance_id if instance_id else datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"agent-{agent_id}-{branch_suffix}"
        
        print(f"Creating branch '{branch_name}' with {agent_id}'s changes...")
        
        # Create and switch to new branch
        subprocess.run(['git', 'checkout', '-b', branch_name], 
                      cwd=str(instance_path), check=True)
        
        # Stage all changes
        subprocess.run(['git', 'add', '.'], cwd=str(instance_path), check=True)
        
        # Commit changes
        commit_msg = f"Work by {agent_id}\n\n🤖 Generated with Claude Code\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        subprocess.run(['git', 'commit', '-m', commit_msg], 
                      cwd=str(instance_path), check=True)
        
        # Push branch
        subprocess.run(['git', 'push', '-u', 'origin', branch_name], 
                      cwd=str(instance_path), check=True)
        
        print(f"✅ Pushed branch '{branch_name}' with {agent_id}'s work")
        
        # Delete the project copy
        shutil.rmtree(instance_path)
        print(f"🗑️  Deleted project copy: {instance_path}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to cleanup {agent_id}: {e}")
        print(f"Project copy remains at: {instance_path}")
        return False

def stop_agent(agent_id: str, project_root: Path = None, cleanup: bool = True, instance_id: str = None) -> bool:
    """Stop a specific agent and optionally cleanup its work."""
    all_sessions = get_tmux_sessions()
    
    if instance_id:
        session_name = f"agent-{agent_id}-{instance_id}"
        if session_name not in all_sessions:
            print(f"⚠️  Agent '{agent_id}' instance '{instance_id}' is not running")
            return False
    else:
        # Find any running instance of this agent
        matching_sessions = [s for s in all_sessions if s.startswith(f"agent-{agent_id}")]
        if not matching_sessions:
            print(f"⚠️  No running instances of agent '{agent_id}' found")
            return False
        elif len(matching_sessions) > 1:
            print(f"⚠️  Multiple instances of '{agent_id}' running:")
            for session in matching_sessions:
                instance = session.replace(f"agent-{agent_id}-", "") if "-" in session[len(f"agent-{agent_id}"):] else "default"
                print(f"    {instance}")
            print(f"Please specify instance ID: python manage_agents.py stop {agent_id} <instance_id>")
            return False
        else:
            session_name = matching_sessions[0]
            instance_id = session_name.replace(f"agent-{agent_id}-", "") if "-" in session_name[len(f"agent-{agent_id}"):] else None
    
    try:
        subprocess.run(['tmux', 'kill-session', '-t', session_name], check=True)
        print(f"🛑 Stopped agent '{agent_id}'")
        
        # Cleanup if requested and project_root provided
        if cleanup and project_root:
            cleanup_agent_work(agent_id, project_root, instance_id)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to stop {agent_id}: {e}")
        return False

def attach_agent(agent_id: str, instance_id: str = None) -> bool:
    """Attach to a specific agent session."""
    all_sessions = get_tmux_sessions()
    
    if instance_id:
        session_name = f"agent-{agent_id}-{instance_id}"
        if session_name not in all_sessions:
            print(f"❌ Agent '{agent_id}' instance '{instance_id}' is not running")
            return False
    else:
        # Find any running instance of this agent
        matching_sessions = [s for s in all_sessions if s.startswith(f"agent-{agent_id}")]
        if not matching_sessions:
            print(f"❌ No running instances of agent '{agent_id}' found")
            return False
        elif len(matching_sessions) > 1:
            print(f"⚠️ Multiple instances of '{agent_id}' running:")
            for session in matching_sessions:
                instance = session.replace(f"agent-{agent_id}-", "") if "-" in session[len(f"agent-{agent_id}"):] else "default"
                print(f"    {instance}")
            print(f"Please specify instance ID: python manage_agents.py attach {agent_id} <instance_id>")
            return False
        else:
            session_name = matching_sessions[0]
    
    print(f"Attaching to {agent_id}... (Press Ctrl+B then D to detach)")
    try:
        subprocess.run(['tmux', 'attach', '-t', session_name])
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to attach to {agent_id}: {e}")
        return False

def stop_all_agents(agent_sessions: List[Dict], project_root: Path, cleanup: bool = True):
    """Stop all running agents."""
    running_agents = [a for a in agent_sessions if a['running']]
    if not running_agents:
        print("No agents are currently running")
        return
    
    print(f"Stopping {len(running_agents)} running agent instances...")
    for agent in running_agents:
        stop_agent(agent['id'], project_root, cleanup, agent.get('instance_id'))

def main():
    if len(sys.argv) < 2:
        print("Usage: python manage_agents.py <command> [agent_id] [options]")
        print("\nCommands:")
        print("  list                    # List all agents and their status")
        print("  start <agent_id>        # Start specific agent")
        print("  stop <agent_id>         # Stop specific agent (with cleanup)")
        print("  stop <agent_id> <instance_id>  # Stop specific instance")
        print("  stop <agent_id> --no-cleanup  # Stop without creating branch")
        print("  attach <agent_id>       # Attach to agent session")
        print("  attach <agent_id> <instance_id>  # Attach to specific instance")
        print("  cleanup <agent_id>      # Cleanup agent work (create branch & delete)")
        print("  stop-all                # Stop all running agents (with cleanup)")
        print("  stop-all --no-cleanup   # Stop all without creating branches")
        print("\nExample:")
        print("  python manage_agents.py list")
        print("  python manage_agents.py start claude_code_auditor")
        print("  python manage_agents.py attach claude_code_auditor")
        print("  python manage_agents.py stop claude_code_auditor")
        print("  python manage_agents.py cleanup claude_code_auditor")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    # Check for --no-cleanup flag
    no_cleanup = '--no-cleanup' in sys.argv
    cleanup = not no_cleanup
    
    # Get project paths
    project_root = Path(__file__).parent.parent
    prompts_file = project_root / 'scripts' / 'prompts.json'
    
    if not prompts_file.exists():
        print(f"Error: Prompts file not found: {prompts_file}")
        sys.exit(1)
    
    # Load prompts and get session status
    prompts = load_prompts(str(prompts_file))
    agent_sessions = get_agent_sessions(prompts)
    
    if command == 'list':
        list_agents(agent_sessions)
    
    elif command == 'start':
        if len(sys.argv) < 3:
            print("Error: Please specify agent ID")
            print("Available agents:")
            for p in prompts:
                print(f"  {p['id']}")
            sys.exit(1)
        
        agent_id = sys.argv[2]
        start_agent(agent_id, prompts, project_root)
    
    elif command == 'stop':
        if len(sys.argv) < 3:
            print("Error: Please specify agent ID")
            running = [a for a in agent_sessions if a['running']]
            if running:
                print("Running agents:")
                for a in running:
                    instance = a.get('instance_id', 'N/A') if a['running'] else 'N/A'
                    print(f"  {a['id']} ({instance})")
            sys.exit(1)
        
        agent_id = sys.argv[2]
        instance_id = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else None
        stop_agent(agent_id, project_root, cleanup, instance_id)
    
    elif command == 'attach':
        if len(sys.argv) < 3:
            print("Error: Please specify agent ID")
            running = [a for a in agent_sessions if a['running']]
            if running:
                print("Running agents:")
                for a in running:
                    instance = a.get('instance_id', 'N/A') if a['running'] else 'N/A'
                    print(f"  {a['id']} ({instance})")
            sys.exit(1)
        
        agent_id = sys.argv[2]
        instance_id = sys.argv[3] if len(sys.argv) > 3 else None
        attach_agent(agent_id, instance_id)
    
    elif command == 'cleanup':
        if len(sys.argv) < 3:
            print("Error: Please specify agent ID")
            print("Available agents with project copies:")
            for p in prompts:
                instance_path = get_agent_instance_path(p['id'], project_root)
                if instance_path.exists():
                    print(f"  {p['id']}")
            sys.exit(1)
        
        agent_id = sys.argv[2]
        cleanup_agent_work(agent_id, project_root)
    
    elif command == 'stop-all':
        stop_all_agents(agent_sessions, project_root, cleanup)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == '__main__':
    main()