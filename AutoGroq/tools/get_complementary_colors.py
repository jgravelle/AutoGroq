# Tool filename: complementary_colors.py
# Import necessary module(s)
import colorsys

def get_complementary_colors(color):
    # docstrings
    """
    Returns a list of complementary colors for the given color.

    Parameters:
    color (str): The color in hexadecimal format (e.g., '#FF0000' for red).

    Returns:
    list: A list of complementary colors in hexadecimal format.
    """

    # Body of tool
    # Convert the color from hexadecimal to RGB
    r, g, b = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    # Convert RGB to HSV
    h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    # Calculate the complementary hue
    h_compl = (h + 0.5) % 1
    # Convert the complementary hue back to RGB
    r_compl, g_compl, b_compl = colorsys.hsv_to_rgb(h_compl, 1, 1)
    # Convert RGB to hexadecimal
    color_compl = '#{:02x}{:02x}{:02x}'.format(int(r_compl*255), int(g_compl*255), int(b_compl*255))
    # Return the complementary color
    return [color_compl]

    # Example usage:
    # color = '#FF0000'
    # print(get_complementary_colors(color))