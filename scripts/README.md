# Claude Code Agent Management Scripts

This directory contains scripts to launch and manage multiple Claude Code instances with specialized prompts for Pokemon-Gym project analysis.

## Files

- **`prompts.json`**: JSON file containing all agent prompts and configurations
- **`launch_agents.py`**: Script to launch multiple Claude Code instances with different specialized prompts
- **`manage_agents.py`**: Script to monitor, control, and view logs from running agents
- **`convert_prompts.py`**: Utility script to convert markdown prompts to JSON format

## Quick Start

### 1. Launch All Agents
```bash
# Activate virtual environment first
source .venv/bin/activate

# Launch all agents (creates instances in parent directory)
python scripts/launch_agents.py

# Or launch specific agents
python scripts/launch_agents.py --agents claude_code_auditor security_auditor
```

### 2. Monitor Agents
```bash
# List all running agents
python scripts/manage_agents.py list

# View detailed status of specific agent
python scripts/manage_agents.py status --agent claude_code_auditor

# View logs from all agents
python scripts/manage_agents.py logs

# View logs from specific agent
python scripts/manage_agents.py logs --agent claude_code_auditor --lines 100
```

### 3. Control Agents
```bash
# Stop specific agent
python scripts/manage_agents.py stop --agent claude_code_auditor

# Stop all agents
python scripts/manage_agents.py stop --all

# Restart specific agent
python scripts/manage_agents.py restart --agent claude_code_auditor

# Restart all agents
python scripts/manage_agents.py restart --all
```

## Available Agents

The following specialized agents are available:

1. **claude_code_auditor** - Verify that everything Claude Code claimed to implement actually works
2. **change_analysis_engine** - Compare current state against commit dacb5f7 and identify problematic changes
3. **code_quality_inspector** - Examine codebase for technical debt and quality issues
4. **integration_validator** - Verify all components work together as a complete system
5. **regression_hunter** - Find functionality that used to work but is now broken
6. **security_auditor** - Examine codebase for security vulnerabilities
7. **performance_analyst** - Identify bottlenecks and performance issues
8. **architecture_reviewer** - Evaluate system design and scalability concerns
9. **documentation_synchronizer** - Bring all project documentation into alignment with current reality
10. **project_completion_strategist** - Create comprehensive plan for finishing Pokemon-Gym streaming system

## How It Works

### Project Instance Creation
Each agent gets its own complete copy of the project in the parent directory:
- Creates `../pokemon-gym-{agent_id}/` directories
- Copies all project files (excluding .git, .venv, node_modules)
- Copies .env and Pokemon_Red.gb files if they exist
- Sets up separate Python virtual environment for each instance
- Installs all dependencies from requirements.txt

### Agent Management
- Each Claude Code instance runs with `--dangerously-skip-permissions` for autonomous operation
- Unique session IDs are generated for each agent
- Process information is tracked in `../claude_agents.json`
- Agents have access to their dedicated project directory via `--add-dir`

### File Structure After Launch
```
parent-directory/
├── pokemon-gym/                    # Original project
├── pokemon-gym-claude_code_auditor/  # Agent instance
├── pokemon-gym-security_auditor/     # Agent instance
├── ...
└── claude_agents.json              # Agent tracking file
```

## Command Line Options

### launch_agents.py
- `--agents AGENT_ID [AGENT_ID ...]`: Launch specific agents by ID
- `--skip-setup`: Skip environment setup (use existing instances)
- `--prompts-file FILE`: Use custom prompts file (default: prompts.json)
- `--dry-run`: Show what would be launched without executing

### manage_agents.py
- `--agent AGENT_ID`: Target specific agent
- `--all`: Apply command to all agents
- `--lines N`: Number of log lines to show (default: 50)

## Adding New Agents

1. Add new prompt configuration to `prompts.json`:
```json
{
  "name": "New Agent Name",
  "id": "new_agent_id",
  "description": "Brief description",
  "prompt": "Detailed prompt text..."
}
```

2. Launch the new agent:
```bash
python scripts/launch_agents.py --agents new_agent_id
```

## Requirements

- Python 3.11+
- Virtual environment with project dependencies
- `psutil` package for process management
- Claude Code CLI installed and configured

## Notes

- Agents run autonomously with permissions bypassed
- Each instance is independent with its own virtual environment
- Log files are created in each agent's instance directory
- Session IDs allow for conversation continuity
- Environment setup can take several minutes per agent due to dependency installation