#!/usr/bin/env python3
"""
Pokemon-Gym Streaming Dashboard
Real-time monitoring dashboard for Pokemon gameplay with AI thoughts display
"""

import os
import sys
import time
import json
import argparse
import requests
import pygame
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

class PokemonDashboard:
    """Real-time dashboard for Pokemon-Gym streaming with server API integration"""
    
    def __init__(self, server_url: str = "http://localhost:8080", thoughts_file: str = "thoughts.txt"):
        self.server_url = server_url.rstrip('/')
        self.thoughts_file = Path(thoughts_file)
        self.last_thoughts_modified = 0
        self.current_thoughts = {"step": "?", "thoughts": "Waiting for AI...", "location": "Unknown"}
        self.game_state = {}
        self.server_status = {"connected": False, "last_check": 0}
        
        # Initialize pygame
        pygame.init()
        
        # Display settings
        self.screen_width = 1200
        self.screen_height = 800
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Pokemon-Gym Streaming Dashboard")
        
        # Fonts
        self.title_font = pygame.font.Font(None, 48)
        self.header_font = pygame.font.Font(None, 32)
        self.text_font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        
        # Colors
        self.bg_color = (15, 15, 25)
        self.panel_color = (25, 25, 40)
        self.border_color = (60, 60, 80)
        self.text_color = (220, 220, 220)
        self.title_color = (100, 200, 255)
        self.location_color = (255, 200, 100)
        self.health_color = (100, 255, 100)
        self.error_color = (255, 100, 100)
        self.warning_color = (255, 200, 100)
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        print(f"Dashboard initialized - Server: {self.server_url}")
        print(f"Monitoring thoughts file: {self.thoughts_file}")
    
    def check_server_status(self) -> bool:
        """Check if the Pokemon server is responding"""
        try:
            response = requests.get(f"{self.server_url}/status", timeout=2)
            if response.status_code == 200:
                self.server_status = {"connected": True, "last_check": time.time()}
                return True
        except requests.RequestException:
            pass
        
        self.server_status = {"connected": False, "last_check": time.time()}
        return False
    
    def get_game_state(self) -> Optional[Dict[str, Any]]:
        """Fetch current game state from server"""
        if not self.server_status["connected"]:
            return None
            
        try:
            response = requests.get(f"{self.server_url}/game_state", timeout=2)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            pass
        
        return None
    
    def read_thoughts(self) -> Optional[Dict[str, str]]:
        """Read and parse the AI thoughts file"""
        if not self.thoughts_file.exists():
            return None
        
        try:
            # Check if file has been modified
            current_modified = os.path.getmtime(self.thoughts_file)
            if current_modified == self.last_thoughts_modified:
                return None  # No change
            
            self.last_thoughts_modified = current_modified
            
            with open(self.thoughts_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the content
            lines = content.split('\n')
            
            # Extract step number
            step = "?"
            if lines and "=== AI Thoughts - Step" in lines[0]:
                try:
                    step = lines[0].split("Step")[1].split("===")[0].strip()
                except:
                    pass
            
            # Extract thoughts and location
            thoughts_lines = []
            location = "Unknown"
            in_thoughts = False
            
            for line in lines:
                if "=== AI Thoughts" in line:
                    in_thoughts = True
                    continue
                elif "=== Location:" in line:
                    in_thoughts = False
                    try:
                        location = line.split(":")[1].split("===")[0].strip()
                    except:
                        pass
                elif in_thoughts and line.strip():
                    thoughts_lines.append(line)
            
            thoughts = '\n'.join(thoughts_lines).strip()
            if not thoughts:
                thoughts = "Processing..."
            
            return {
                "step": step,
                "thoughts": thoughts,
                "location": location
            }
            
        except Exception as e:
            print(f"Error reading thoughts file: {e}")
            return None
    
    def wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> list:
        """Wrap text to fit within a maximum width"""
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
                    current_line = []
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def draw_panel(self, x: int, y: int, width: int, height: int, title: str = ""):
        """Draw a panel with border and optional title"""
        # Panel background
        pygame.draw.rect(self.screen, self.panel_color, (x, y, width, height))
        pygame.draw.rect(self.screen, self.border_color, (x, y, width, height), 2)
        
        # Title if provided
        if title:
            title_surface = self.header_font.render(title, True, self.title_color)
            title_rect = title_surface.get_rect(centerx=x + width//2, y=y + 10)
            self.screen.blit(title_surface, title_rect)
            return y + 40  # Return y position after title
        
        return y + 10
    
    def draw_server_status(self, x: int, y: int, width: int, height: int):
        """Draw server connection status panel"""
        content_y = self.draw_panel(x, y, width, height, "Server Status")
        
        # Connection status
        status_text = "CONNECTED" if self.server_status["connected"] else "DISCONNECTED"
        status_color = self.health_color if self.server_status["connected"] else self.error_color
        
        status_surface = self.text_font.render(f"Status: {status_text}", True, status_color)
        self.screen.blit(status_surface, (x + 20, content_y))
        
        # Server URL
        url_surface = self.small_font.render(f"URL: {self.server_url}", True, self.text_color)
        self.screen.blit(url_surface, (x + 20, content_y + 30))
        
        # Last check time
        if self.server_status["last_check"] > 0:
            last_check = datetime.fromtimestamp(self.server_status["last_check"]).strftime("%H:%M:%S")
            check_surface = self.small_font.render(f"Last Check: {last_check}", True, self.text_color)
            self.screen.blit(check_surface, (x + 20, content_y + 50))
    
    def draw_game_state(self, x: int, y: int, width: int, height: int):
        """Draw current game state panel"""
        content_y = self.draw_panel(x, y, width, height, "Game State")
        
        if not self.game_state:
            no_data_surface = self.text_font.render("No game data available", True, self.warning_color)
            self.screen.blit(no_data_surface, (x + 20, content_y))
            return
        
        # Location
        location = self.game_state.get('location', 'Unknown')
        location_surface = self.text_font.render(f"Location: {location}", True, self.location_color)
        self.screen.blit(location_surface, (x + 20, content_y))
        
        # Coordinates
        coords = self.game_state.get('coordinates', [0, 0])
        coords_surface = self.text_font.render(f"Coordinates: [{coords[0]}, {coords[1]}]", True, self.text_color)
        self.screen.blit(coords_surface, (x + 20, content_y + 25))
        
        # Score
        score = self.game_state.get('score', 0)
        score_surface = self.text_font.render(f"Score: {score}", True, self.text_color)
        self.screen.blit(score_surface, (x + 20, content_y + 50))
        
        # Money
        money = self.game_state.get('money', 0)
        money_surface = self.text_font.render(f"Money: ${money}", True, self.text_color)
        self.screen.blit(money_surface, (x + 20, content_y + 75))
        
        # Badges
        badges = self.game_state.get('badges', [])
        badges_surface = self.text_font.render(f"Badges: {len(badges)}", True, self.text_color)
        self.screen.blit(badges_surface, (x + 20, content_y + 100))
        
        # Pokemon count
        pokemon = self.game_state.get('pokemon', [])
        pokemon_surface = self.text_font.render(f"Pokemon: {len(pokemon)}", True, self.text_color)
        self.screen.blit(pokemon_surface, (x + 20, content_y + 125))
    
    def draw_ai_thoughts(self, x: int, y: int, width: int, height: int):
        """Draw AI thoughts panel"""
        content_y = self.draw_panel(x, y, width, height, f"AI Thoughts - Step {self.current_thoughts['step']}")
        
        # Thoughts content
        max_text_width = width - 40
        thought_paragraphs = self.current_thoughts['thoughts'].split('\n')
        
        current_y = content_y
        for paragraph in thought_paragraphs:
            if paragraph.strip():
                wrapped_lines = self.wrap_text(paragraph, self.text_font, max_text_width)
                
                for line in wrapped_lines:
                    if current_y + 25 < y + height - 60:  # Leave space for location
                        text_surface = self.text_font.render(line, True, self.text_color)
                        self.screen.blit(text_surface, (x + 20, current_y))
                        current_y += 25
                
                current_y += 10  # Space between paragraphs
        
        # Location at bottom
        location_surface = self.text_font.render(f"Location: {self.current_thoughts['location']}", True, self.location_color)
        self.screen.blit(location_surface, (x + 20, y + height - 40))
    
    def draw_stats(self, x: int, y: int, width: int, height: int):
        """Draw system statistics panel"""
        content_y = self.draw_panel(x, y, width, height, "System Stats")
        
        # Thoughts file status
        thoughts_status = "ACTIVE" if self.thoughts_file.exists() else "MISSING"
        thoughts_color = self.health_color if self.thoughts_file.exists() else self.error_color
        
        thoughts_surface = self.text_font.render(f"Thoughts File: {thoughts_status}", True, thoughts_color)
        self.screen.blit(thoughts_surface, (x + 20, content_y))
        
        # Current time
        current_time = datetime.now().strftime("%H:%M:%S")
        time_surface = self.text_font.render(f"Time: {current_time}", True, self.text_color)
        self.screen.blit(time_surface, (x + 20, content_y + 25))
        
        # Frame rate
        fps = int(self.clock.get_fps())
        fps_surface = self.text_font.render(f"FPS: {fps}", True, self.text_color)
        self.screen.blit(fps_surface, (x + 20, content_y + 50))
    
    def update_data(self):
        """Update all data from sources"""
        # Check server status periodically
        current_time = time.time()
        if current_time - self.server_status.get("last_check", 0) > 5:  # Check every 5 seconds
            self.check_server_status()
        
        # Get game state if server is connected
        if self.server_status["connected"]:
            game_state = self.get_game_state()
            if game_state:
                self.game_state = game_state
        
        # Read thoughts file
        new_thoughts = self.read_thoughts()
        if new_thoughts:
            self.current_thoughts = new_thoughts
    
    def draw(self):
        """Draw the complete dashboard"""
        self.screen.fill(self.bg_color)
        
        # Main title
        title_surface = self.title_font.render("Pokemon-Gym Streaming Dashboard", True, self.title_color)
        title_rect = title_surface.get_rect(centerx=self.screen_width // 2, y=20)
        self.screen.blit(title_surface, title_rect)
        
        # Layout panels
        panel_margin = 10
        panel_y_start = 80
        
        # Top row: Server Status and Game State
        top_panel_width = (self.screen_width - 3 * panel_margin) // 2
        top_panel_height = 200
        
        self.draw_server_status(panel_margin, panel_y_start, top_panel_width, top_panel_height)
        self.draw_game_state(panel_margin + top_panel_width + panel_margin, panel_y_start, 
                           top_panel_width, top_panel_height)
        
        # Middle row: AI Thoughts (large panel)
        thoughts_y = panel_y_start + top_panel_height + panel_margin
        thoughts_height = 400
        thoughts_width = self.screen_width - 2 * panel_margin
        
        self.draw_ai_thoughts(panel_margin, thoughts_y, thoughts_width, thoughts_height)
        
        # Bottom row: System Stats
        stats_y = thoughts_y + thoughts_height + panel_margin
        stats_height = 120
        stats_width = self.screen_width - 2 * panel_margin
        
        self.draw_stats(panel_margin, stats_y, stats_width, stats_height)
        
        pygame.display.flip()
    
    def run(self):
        """Main dashboard loop"""
        print("Starting Pokemon-Gym Dashboard")
        print("Press ESC to exit, R to force refresh")
        
        while self.running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_r:
                        # Force refresh
                        self.last_thoughts_modified = 0
                        self.server_status["last_check"] = 0
            
            # Update data and draw
            self.update_data()
            self.draw()
            
            # Control frame rate
            self.clock.tick(10)  # 10 FPS for dashboard
        
        pygame.quit()
        print("Dashboard closed")


def main():
    """Main function for running the dashboard"""
    parser = argparse.ArgumentParser(description="Pokemon-Gym Streaming Dashboard")
    parser.add_argument("--server-url", type=str, default="http://localhost:8080",
                       help="Pokemon server URL (default: http://localhost:8080)")
    parser.add_argument("--thoughts-file", type=str, default="thoughts.txt",
                       help="Path to AI thoughts file (default: thoughts.txt)")
    
    args = parser.parse_args()
    
    dashboard = PokemonDashboard(
        server_url=args.server_url,
        thoughts_file=args.thoughts_file
    )
    
    try:
        dashboard.run()
    except KeyboardInterrupt:
        print("\nDashboard interrupted by user")
    except Exception as e:
        print(f"Error running dashboard: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()