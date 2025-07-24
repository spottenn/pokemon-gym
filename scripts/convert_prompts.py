#!/usr/bin/env python3
"""
Convert prompts from CLAUDE_CODE_PROMPTS.md to JSON format.
"""

import json
import re
from pathlib import Path

def parse_markdown_prompts(md_content: str) -> list:
    """Parse prompts from markdown content."""
    prompts = []
    
    # Split by --- sections
    sections = re.split(r'^---\s*$', md_content, flags=re.MULTILINE)
    
    for section in sections:
        # Look for ## headings
        heading_match = re.search(r'^## (.+?)$', section, re.MULTILINE)
        if not heading_match:
            continue
        
        title = heading_match.group(1).strip()
        
        # Skip usage notes and other non-prompt sections
        if title.lower() in ['usage notes']:
            continue
        
        # Extract the prompt text (everything after the heading)
        prompt_start = heading_match.end()
        prompt_text = section[prompt_start:].strip()
        
        # Clean up the prompt text
        prompt_text = re.sub(r'\n\s*\n', '\n\n', prompt_text)  # Normalize whitespace
        prompt_text = prompt_text.strip()
        
        if not prompt_text:
            continue
        
        # Generate ID from title
        agent_id = title.lower().replace(' ', '_').replace('-', '_')
        agent_id = re.sub(r'[^a-z0-9_]', '', agent_id)
        
        prompts.append({
            'name': title,
            'id': agent_id,
            'description': prompt_text.split('.')[0] + '.' if '.' in prompt_text else title,
            'prompt': prompt_text
        })
    
    return prompts

def main():
    # Get file paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    md_file = project_root / 'CLAUDE_CODE_PROMPTS.md'
    json_file = script_dir / 'prompts.json'
    
    # Read markdown file
    with open(md_file, 'r') as f:
        md_content = f.read()
    
    # Parse prompts
    prompts = parse_markdown_prompts(md_content)
    
    # Create JSON structure
    json_data = {
        'prompts': prompts
    }
    
    # Write JSON file
    with open(json_file, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Converted {len(prompts)} prompts to {json_file}")
    for prompt in prompts:
        print(f"  - {prompt['name']} ({prompt['id']})")

if __name__ == '__main__':
    main()