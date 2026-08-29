from vtt.tools.dice import roll_dice

def test_roll_dice_no_modifier():
    result = roll_dice("1d20")
    assert "Rolled 1d20:" in result
    assert "Error:" not in result

def test_roll_dice_modifier():
    result = roll_dice("2d6+3")
    assert "Rolled 2d6+3:" in result
    assert "+" in result
    assert "Error:" not in result

def test_roll_dice_negative_modifier():
    result = roll_dice("1d8-1")
    assert "Rolled 1d8-1:" in result
    assert "-" in result
    assert "Error:" not in result

def test_invalid_dice():
    result = roll_dice("invalid")
    assert "Error:" in result
