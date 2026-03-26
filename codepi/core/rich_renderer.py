# Rich Renderer

This module contains comprehensive rich-based terminal UI components for improved user experience in interactive mode.

## Components

### 1. RichText
- **Description:** A class to render rich text with colors, styles, and more.
- **Usage:** 
  ```python
  from rich import print
  
  class RichText:
      def __init__(self, message: str, style: str = "bold green"):
          self.message = message
          self.style = style
      
      def render(self):
          print(f"[{self.style}]{self.message}[/{self.style}]")
