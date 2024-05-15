
  ## This is a sample skill. Replace with your own skill function
  ## In general, a good skill must have 3 sections:
  ## 1. Imports (import libraries needed for your skill)
  ## 2. Function definition  AND docstrings (this helps the LLM understand what the function does and how to use it)
  ## 3. Function body (the actual code that implements the function)

  import numpy as np
  import matplotlib.pyplot as plt
  from matplotlib import font_manager as fm

  def save_cat_ascii_art_to_png(filename='ascii_cat.png'):
      """
      Creates ASCII art of a cat and saves it to a PNG file.

      :param filename: str, the name of the PNG file to save the ASCII art.
      """
      # ASCII art string
      cat_art = [
          "  /_/  ",
          " ( o.o ) ",
          " > ^ <  "
      ]

      # Determine shape of output array
      height = len(cat_art)
      width = max(len(line) for line in cat_art)

      # Create a figure and axis to display ASCII art
      fig, ax = plt.subplots(figsize=(width, height))
      ax.axis('off')  # Hide axes

      # Get a monospace font
      prop = fm.FontProperties(family='monospace')

      # Display ASCII art using text
      for y, line in enumerate(cat_art):
          ax.text(0, height-y-1, line, fontproperties=prop, fontsize=12)

      # Adjust layout
      plt.tight_layout()

      # Save figure to file
      plt.savefig(filename, dpi=120, bbox_inches='tight', pad_inches=0.1)
      plt.close(fig)