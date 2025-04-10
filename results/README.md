# PokemonEval Results

This directory contains evaluation results comparing different LLM agents playing Pokemon Red.

## Overview

The comparison shows how various LLM models (Claude-3.5-Sonnet, Claude-3.7-Sonnet, GPT-4o, Gemini-2.5-Pro, and Llama-4) perform in playing Pokemon Red. The evaluation measures progression through the game, battle strategy, and overall effectiveness.

## Results

![](comparison_plot.png)

## Running Comparisons

To generate your own comparison plots based on scoring events:

```bash
python compare_scores.py --files score_events_claude-3-5-sonnet.json score_events_claude-3-7-sonnet.json score_events_gpt-4o.json
```

Or use a directory with multiple score event files:

```bash
python compare_scores.py --dir . --pattern "score_events_*.json" --output my_comparison.png
```

Command-line options:
- `--files`: List of score event JSON files to compare
- `--dir`: Directory containing score event files
- `--pattern`: File pattern to match (default: score_events_*.json)
- `--output`: Output file name for the plot (default: comparison_plot.png)

## Data Access

The complete trace data and gameplay logs can be downloaded from:
[https://drive.google.com/file/d/1uTaexC23GOnMLMe8txHsKlzB2SMybhF1/view?usp=drive_link](https://drive.google.com/file/d/1uTaexC23GOnMLMe8txHsKlzB2SMybhF1/view?usp=drive_link)

## Methodology

Models were evaluated based on their ability to progress through the game, make strategic decisions in battles, and complete objectives. The scoring system rewards progress milestones and effective battle tactics.

The comparison uses standardized metrics to ensure fair comparison across all models. 