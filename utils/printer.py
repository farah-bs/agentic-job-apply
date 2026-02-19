def print_step(step: str, agent: str, message: str):
    """Print a formatted step indicator"""
    print(f"\n[{step}] {agent}")
    print(f"    {message}")


def print_result(title: str, details: str):
    """Print a formatted result"""
    print(f"{title}: {details}")