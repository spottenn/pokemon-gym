#!/usr/bin/env python3
"""
Alternative OBS Testing Setup - Real-time Thoughts Viewer
Simulates what OBS would do by reading the thoughts file and displaying it
"""

import os
import sys
import time
import argparse
import pygame
from pathlib import Path

class ThoughtsViewer:
    """Simple viewer that monitors and displays the thoughts file in real-time"""
    
    def __init__(self, thoughts_file: str = "thoughts.txt", refresh_rate: float = 0.5):
        self.thoughts_file = Path(thoughts_file)
        self.refresh_rate = refresh_rate
        self.last_content = ""
        self.last_modified = 0
        
        # Pygame setup
        pygame.init()
        self.screen_width = 800
        self.screen_height = 600
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption(f"AI Thoughts Viewer - {thoughts_file}")
        
        # Fonts
        self.title_font = pygame.font.Font(None, 36)
        self.text_font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        
        # Colors
        self.bg_color = (20, 20, 30)
        self.text_color = (220, 220, 220)
        self.title_color = (100, 200, 255)
        self.location_color = (255, 200, 100)
        self.border_color = (60, 60, 80)
        
        self.running = True
        self.clock = pygame.time.Clock()
    
    def read_thoughts(self) -> dict:
        """Read and parse the thoughts file"""
        if not self.thoughts_file.exists():
            return {
                "step": "?",
                "thoughts": "Waiting for AI thoughts...",
                "location": "Unknown"
            }
        
        try:
            # Check if file has been modified
            current_modified = os.path.getmtime(self.thoughts_file)
            if current_modified == self.last_modified:
                return None  # No change
            
            self.last_modified = current_modified
            
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
            
            # Extract thoughts (everything between step header and location)
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
            return {
                "step": "?",
                "thoughts": f"Error: {str(e)}",
                "location": "Unknown"
            }
    
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
                    # Word is too long, split it
                    lines.append(word)
                    current_line = []
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def draw(self, data: dict):
        """Draw the thoughts display"""
        self.screen.fill(self.bg_color)
        
        # Draw border
        pygame.draw.rect(self.screen, self.border_color, 
                        (10, 10, self.screen_width - 20, self.screen_height - 20), 3)
        
        # Draw title
        title_text = f"AI Thoughts - Step {data['step']}"
        title_surface = self.title_font.render(title_text, True, self.title_color)
        title_rect = title_surface.get_rect(centerx=self.screen_width // 2, y=30)
        self.screen.blit(title_surface, title_rect)
        
        # Draw thoughts
        y_offset = 100
        max_text_width = self.screen_width - 80
        
        # Split thoughts by newlines first
        thought_paragraphs = data['thoughts'].split('\n')
        
        for paragraph in thought_paragraphs:
            if paragraph.strip():
                # Wrap each paragraph
                wrapped_lines = self.wrap_text(paragraph, self.text_font, max_text_width)
                
                for line in wrapped_lines:
                    text_surface = self.text_font.render(line, True, self.text_color)
                    self.screen.blit(text_surface, (40, y_offset))
                    y_offset += 30
                
                # Add space between paragraphs
                y_offset += 10
        
        # Draw location at bottom
        location_text = f"Location: {data['location']}"
        location_surface = self.text_font.render(location_text, True, self.location_color)
        location_rect = location_surface.get_rect(centerx=self.screen_width // 2, 
                                                 y=self.screen_height - 60)
        self.screen.blit(location_surface, location_rect)
        
        # Draw status
        status_text = f"Monitoring: {self.thoughts_file} | Refresh: {self.refresh_rate}s"
        status_surface = self.small_font.render(status_text, True, (100, 100, 120))
        self.screen.blit(status_surface, (20, self.screen_height - 30))
        
        pygame.display.flip()
    
    def run(self):
        """Main viewer loop"""
        print(f"Starting thoughts viewer for: {self.thoughts_file}")
        print("This simulates what OBS would capture from the thoughts file")
        print("Press ESC or close window to exit")
        
        # Initial draw
        current_data = self.read_thoughts()
        if current_data:
            self.draw(current_data)
        
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
                        self.last_modified = 0
            
            # Read and update display
            new_data = self.read_thoughts()
            if new_data:
                current_data = new_data
                self.draw(current_data)
            
            # Control frame rate
            self.clock.tick(int(1 / self.refresh_rate))
        
        pygame.quit()
        print("Viewer closed")


def main():
    """Main function for running the thoughts viewer"""
    parser = argparse.ArgumentParser(description="AI Thoughts Viewer - OBS Alternative")
    parser.add_argument("--thoughts-file", type=str, default="thoughts.txt",
                       help="Path to the thoughts file to monitor")
    parser.add_argument("--refresh-rate", type=float, default=0.5,
                       help="Refresh rate in seconds (default: 0.5)")
    
    args = parser.parse_args()
    
    viewer = ThoughtsViewer(
        thoughts_file=args.thoughts_file,
        refresh_rate=args.refresh_rate
    )
    
    try:
        viewer.run()
    except KeyboardInterrupt:
        print("\nViewer interrupted by user")
    except Exception as e:
        print(f"Error running viewer: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()