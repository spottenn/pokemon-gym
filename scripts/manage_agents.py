#!/usr/bin/env python3
"""
Manage running Claude Code agents - monitor status, view logs, and control instances.
"""

import json
import os
import subprocess
import sys
import signal
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import time
import psutil

def load_agents_info(info_file: Path) -> List[Dict]:
    """Load agent information from file."""
    if not info_file.exists():
        return []
    
    with open(info_file, 'r') as f:
        return json.load(f)

def save_agents_info(agents_info: List[Dict], info_file: Path):
    """Save agent information to file."""
    with open(info_file, 'w') as f:
        json.dump(agents_info, f, indent=2)

def check_process_status(pid: int) -> bool:
    """Check if a process is still running."""
    try:
        process = psutil.Process(pid)
        return process.is_running()
    except psutil.NoSuchProcess:
        return False

def get_process_info(pid: int) -> Optional[Dict]:
    """Get information about a running process."""
    try:
        process = psutil.Process(pid)
        return {
            'cpu_percent': process.cpu_percent(),
            'memory_mb': process.memory_info().rss / 1024 / 1024,
            'status': process.status(),
            'create_time': process.create_time()
        }
    except psutil.NoSuchProcess:
        return None

def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

def list_agents(agents_info: List[Dict]):
    """List all agents and their status."""
    print(f"\n{'='*80}")
    print(f"{'ID':<20} {'Name':<25} {'PID':<8} {'Status':<10} {'Runtime':<15}")
    print(f"{'-'*80}")
    
    for agent in agents_info:
        pid = agent['pid']
        is_running = check_process_status(pid)
        status = "Running" if is_running else "Stopped"
        
        runtime = ""
        if is_running and 'started_at' in agent:
            duration = time.time() - agent['started_at']
            runtime = format_duration(duration)
        
        print(f"{agent['id']:<20} {agent['name']:<25} {pid:<8} {status:<10} {runtime:<15}")
    
    print(f"{'='*80}")

def show_agent_details(agent: Dict):
    """Show detailed information about an agent."""
    print(f"\n{'='*60}")
    print(f"Agent: {agent['name']} ({agent['id']})")
    print(f"{'='*60}")
    print(f"Session ID: {agent['session_id']}")
    print(f"Instance Path: {agent['instance_path']}")
    print(f"PID: {agent['pid']}")
    
    if 'started_at' in agent:
        start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(agent['started_at']))
        print(f"Started At: {start_time}")
        duration = time.time() - agent['started_at']
        print(f"Runtime: {format_duration(duration)}")
    
    # Process info
    proc_info = get_process_info(agent['pid'])
    if proc_info:
        print(f"\nProcess Status:")
        print(f"  Status: {proc_info['status']}")
        print(f"  CPU: {proc_info['cpu_percent']:.1f}%")
        print(f"  Memory: {proc_info['memory_mb']:.1f} MB")
    else:
        print(f"\nProcess Status: Not Running")

def tail_agent_output(agent: Dict, lines: int = 50):
    """Tail the output of an agent."""
    instance_path = Path(agent['instance_path'])
    
    # Look for common log files
    possible_logs = [
        'PENDING_AUDIT_PROGRESS_REPORT.md',
        'AUDIT_REPORT.md',
        'agent_log.jsonl',
        'output.log'
    ]
    
    print(f"\n{'='*60}")
    print(f"Recent output from {agent['name']} ({agent['id']})")
    print(f"{'='*60}")
    
    found_logs = False
    for log_file in possible_logs:
        log_path = instance_path / log_file
        if log_path.exists():
            found_logs = True
            print(f"\n--- {log_file} ---")
            
            # Read last N lines
            with open(log_path, 'r') as f:
                content = f.readlines()
                recent_lines = content[-lines:] if len(content) > lines else content
                for line in recent_lines:
                    print(line.rstrip())
    
    if not found_logs:
        print("No log files found in instance directory")

def stop_agent(agent: Dict) -> bool:
    """Stop a running agent."""
    pid = agent['pid']
    
    if not check_process_status(pid):
        print(f"Agent {agent['id']} is not running")
        return False
    
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM to agent {agent['id']} (PID: {pid})")
        
        # Wait for graceful shutdown
        for _ in range(10):
            if not check_process_status(pid):
                print(f"Agent {agent['id']} stopped successfully")
                return True
            time.sleep(0.5)
        
        # Force kill if still running
        os.kill(pid, signal.SIGKILL)
        print(f"Force killed agent {agent['id']}")
        return True
        
    except ProcessLookupError:
        print(f"Process {pid} not found")
        return False
    except Exception as e:
        print(f"Error stopping agent: {e}")
        return False

def restart_agent(agent: Dict, scripts_dir: Path) -> Optional[Dict]:
    """Restart an agent."""
    # Stop if running
    if check_process_status(agent['pid']):
        stop_agent(agent)
        time.sleep(1)
    
    # Launch again
    instance_path = Path(agent['instance_path'])
    
    # Load prompt
    prompts_file = scripts_dir / 'prompts.json'
    with open(prompts_file, 'r') as f:
        prompts_data = json.load(f)
    
    prompt_config = next((p for p in prompts_data['prompts'] if p['id'] == agent['id']), None)
    if not prompt_config:
        print(f"Prompt not found for agent {agent['id']}")
        return None
    
    # Launch Claude instance
    claude_cmd = [
        'claude',
        '--dangerously-skip-permissions',
        '--session-id', agent['session_id'],
        '--add-dir', str(instance_path),
        prompt_config['prompt']
    ]
    
    process = subprocess.Popen(
        claude_cmd,
        cwd=str(instance_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Update agent info
    agent['pid'] = process.pid
    agent['started_at'] = time.time()
    
    print(f"Restarted agent {agent['id']} with PID {process.pid}")
    return agent

def main():
    parser = argparse.ArgumentParser(description='Manage Claude Code agents')
    parser.add_argument('command', choices=['list', 'status', 'stop', 'restart', 'logs'],
                       help='Command to execute')
    parser.add_argument('--agent', help='Agent ID for specific commands')
    parser.add_argument('--all', action='store_true', help='Apply command to all agents')
    parser.add_argument('--lines', type=int, default=50, help='Number of lines to show for logs')
    
    args = parser.parse_args()
    
    # Get paths
    parent_dir = Path(__file__).parent.parent.parent
    scripts_dir = Path(__file__).parent
    info_file = parent_dir / 'claude_agents.json'
    
    # Load agents info
    agents_info = load_agents_info(info_file)
    
    if not agents_info:
        print("No agents found. Run launch_agents.py first.")
        sys.exit(1)
    
    if args.command == 'list':
        list_agents(agents_info)
    
    elif args.command == 'status':
        if args.agent:
            agent = next((a for a in agents_info if a['id'] == args.agent), None)
            if agent:
                show_agent_details(agent)
            else:
                print(f"Agent '{args.agent}' not found")
        else:
            for agent in agents_info:
                show_agent_details(agent)
    
    elif args.command == 'logs':
        if args.agent:
            agent = next((a for a in agents_info if a['id'] == args.agent), None)
            if agent:
                tail_agent_output(agent, args.lines)
            else:
                print(f"Agent '{args.agent}' not found")
        else:
            for agent in agents_info:
                tail_agent_output(agent, args.lines)
    
    elif args.command == 'stop':
        agents_to_stop = []
        if args.all:
            agents_to_stop = agents_info
        elif args.agent:
            agent = next((a for a in agents_info if a['id'] == args.agent), None)
            if agent:
                agents_to_stop = [agent]
            else:
                print(f"Agent '{args.agent}' not found")
                sys.exit(1)
        else:
            print("Specify --agent ID or --all")
            sys.exit(1)
        
        for agent in agents_to_stop:
            stop_agent(agent)
    
    elif args.command == 'restart':
        agents_to_restart = []
        if args.all:
            agents_to_restart = agents_info
        elif args.agent:
            agent = next((a for a in agents_info if a['id'] == args.agent), None)
            if agent:
                agents_to_restart = [agent]
            else:
                print(f"Agent '{args.agent}' not found")
                sys.exit(1)
        else:
            print("Specify --agent ID or --all")
            sys.exit(1)
        
        updated_agents = []
        for i, agent in enumerate(agents_info):
            if agent in agents_to_restart:
                updated = restart_agent(agent, scripts_dir)
                if updated:
                    updated_agents.append(updated)
                else:
                    updated_agents.append(agent)
            else:
                updated_agents.append(agent)
        
        # Save updated info
        save_agents_info(updated_agents, info_file)

if __name__ == '__main__':
    main()