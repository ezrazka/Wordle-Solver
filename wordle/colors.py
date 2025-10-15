color_mappings = {
    "g": "\033[42m\033[1;97m",
    "y": "\033[43m\033[1;97m",
    "x": "\033[100m\033[1;97m",
    "reset": "\033[0m"
}

def colorize(text, color):
    if color not in color_mappings:
        raise ValueError("Invalid color code.")
    
    return f"{color_mappings[color]}{text}{color_mappings['reset']}"