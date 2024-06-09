#  Thanks to MADTANK:  https://github.com/madtank

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Function to draw the geometric structure with customizable file name
def draw_geometric_structure(file_name, base_circles=4, base_circle_color='blue', top_circle_color='orange', line_color='grey', line_width=2):

    # Define the directory and save path using the file_name parameter
    directory = 'diagrams'
    if not os.path.exists(directory):
        os.makedirs(directory)
    save_path = f'{directory}/{file_name}.png'
    
    fig, ax = plt.subplots()

    # Draw base circles
    for i in range(base_circles):
        circle = patches.Circle((i * 1.5, 0), 0.5, color=base_circle_color)
        ax.add_patch(circle)

    # Draw top circle
    top_circle = patches.Circle(((base_circles - 1) * 0.75, 2), 0.6, color=top_circle_color)
    ax.add_patch(top_circle)

    # Draw lines
    for i in range(base_circles):
        line = plt.Line2D([(i * 1.5), ((base_circles - 1) * 0.75)], [0, 2], color=line_color, linewidth=line_width)
        ax.add_line(line)

    # Set limits and aspect
    ax.set_xlim(-1, base_circles * 1.5)
    ax.set_ylim(-1, 3)
    ax.set_aspect('equal')

    # Remove axes
    ax.axis('off')

    # Save the plot to the specified path
    plt.savefig(save_path, bbox_inches='tight', pad_inches=0)
    plt.close()

    # Return the path for verification
    return save_path

# Example usage:
#file_name = 'custom_geometric_structure'
#image_path = draw_geometric_structure(file_name, base_circles=8, base_circle_color='blue', top_circle_color='orange', line_color='grey', line_width=2)