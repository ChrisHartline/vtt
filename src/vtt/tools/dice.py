import random
import re

def roll_dice(expression: str) -> str:
    """
    Evaluates a dice expression like '1d20+5' or '2d6'.
    Returns a formatted string with the result.
    """
    expression = expression.lower().replace(" ", "")
    
    # Simple regex for NdM + X or NdM - X
    match = re.match(r"^(\d+)d(\d+)(?:([+\-])(\d+))?$", expression)
    if not match:
        return f"Error: Invalid dice expression '{expression}'. Use format like '1d20+5'."
        
    num_dice = int(match.group(1))
    sides = int(match.group(2))
    
    if num_dice > 100 or sides > 1000:
        return "Error: Too many dice or sides."
        
    rolls = [random.randint(1, sides) for _ in range(num_dice)]
    total = sum(rolls)
    
    modifier_str = ""
    if match.group(3) and match.group(4):
        sign = match.group(3)
        mod = int(match.group(4))
        if sign == "+":
            total += mod
        else:
            total -= mod
        modifier_str = f" {sign} {mod}"
        
    if num_dice == 1:
        return f"Rolled {expression}: {rolls[0]}{modifier_str} = {total}"
    else:
        return f"Rolled {expression}: {rolls}{modifier_str} = {total}"
