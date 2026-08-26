def decimal_to_hexadecimal(decimal_number: int) -> str:
    """Converts a decimal number to its hexadecimal representation.

    Args:
        decimal_number (int): The decimal number to be converted to hexadecimal.

    Returns:
        str: The hexadecimal representation of the input decimal number.

    Raises:
        TypeError: If the input is not an integer.
    """
    if not isinstance(decimal_number, int):
        raise TypeError("Input must be an integer")

    if decimal_number == 0:
        return '0'

    # Determine if the number is negative
    is_negative = decimal_number < 0
    if is_negative:
        decimal_number = -decimal_number

    # Convert to hexadecimal
    hexadecimal_string = hex(decimal_number)[2:]

    # Add negative sign if the original number was negative
    if is_negative:
        hexadecimal_string = '-' + hexadecimal_string

    return hexadecimal_string
