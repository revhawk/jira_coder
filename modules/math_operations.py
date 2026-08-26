def area(shape: str, **dimensions) -> float:
    """Calculates the area of a given shape based on its dimensions.

    Args:
        shape (str): The type of shape to calculate the area for (e.g., 'circle', 'rectangle').
        dimensions (dict): A dictionary containing the dimensions required to calculate the area of the shape.

    Returns:
        float: The calculated area of the shape.

    Raises:
        ValueError: If an unsupported shape is provided or if dimensions are negative.
        KeyError: If the required dimensions for a shape are missing.
    """
    if shape == 'circle':
        try:
            radius = dimensions['radius']
            if radius < 0:
                raise ValueError("Radius cannot be negative")
            return 3.141592653589793 * radius * radius
        except KeyError:
            raise KeyError("Missing required dimension: 'radius'")

    elif shape == 'rectangle':
        try:
            length = dimensions['length']
            width = dimensions['width']
            if length < 0 or width < 0:
                raise ValueError("Length and width cannot be negative")
            return length * width
        except KeyError as e:
            raise KeyError(f"Missing required dimension: {e.args[0]}")

    else:
        raise ValueError(f"Unsupported shape: {shape}")
