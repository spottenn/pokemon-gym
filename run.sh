#!/bin/bash
INTELLIGENCE_URL=${INTELLIGENCE_URL:-${AGENT_URL:-"http://localhost:8000"}}
MAX_DURATION=${MAX_DURATION:-1}

python evaluate.py --intelligence_url $INTELLIGENCE_URL --rom_path Pokemon_Red.gb --max_duration $MAX_DURATION