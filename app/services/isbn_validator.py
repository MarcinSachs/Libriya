"""
ISBN validation utilities.
"""

import re


class ISBNValidator:
    """Validator for ISBN-10 and ISBN-13 formats."""

    @staticmethod
    def normalize(isbn: str) -> str:
        """
        Normalize ISBN by removing hyphens, spaces, and converting to uppercase.

        Args:
            isbn: ISBN string with or without formatting

        Returns:
            Normalized ISBN string
        """
        if not isbn:
            return ""
        return isbn.strip().replace("-", "").replace(" ", "").upper()

    @staticmethod
    def validate_isbn_10(isbn: str) -> bool:
        """
        Validate ISBN-10 using checksum algorithm.

        Args:
            isbn: 10-digit ISBN string

        Returns:
            True if valid ISBN-10, False otherwise
        """
        if not isbn or len(isbn) != 10:
            return False

        if not isbn[:9].isdigit() or not (isbn[9].isdigit() or isbn[9] == 'X'):
            return False

        total = sum((10 - i) * int(digit) for i, digit in enumerate(isbn[:9]))
        check_digit = (11 - (total % 11)) % 11

        expected_check = 'X' if check_digit == 10 else str(check_digit)
        return isbn[9] == expected_check

    @staticmethod
    def validate_isbn_13(isbn: str) -> bool:
        """
        Validate ISBN-13 using checksum algorithm.

        Args:
            isbn: 13-digit ISBN string

        Returns:
            True if valid ISBN-13, False otherwise
        """
        if not isbn or len(isbn) != 13 or not isbn.isdigit():
            return False

        total = sum(int(digit) * (1 if i % 2 == 0 else 3)
                    for i, digit in enumerate(isbn[:12]))
        check_digit = (10 - (total % 10)) % 10

        return int(isbn[12]) == check_digit

    @staticmethod
    def is_valid(isbn: str) -> bool:
        """
        Check if ISBN is valid (either ISBN-10 or ISBN-13).

        Args:
            isbn: ISBN string (with or without formatting)

        Returns:
            True if valid, False otherwise
        """
        normalized = ISBNValidator.normalize(isbn)

        # Remove any remaining non-digit/non-X characters
        cleaned = re.sub(r'[^\dX]', '', normalized)

        if len(cleaned) == 10:
            return ISBNValidator.validate_isbn_10(cleaned)
        elif len(cleaned) == 13:
            return ISBNValidator.validate_isbn_13(cleaned)

        return False

    @staticmethod
    def format_isbn_13(isbn: str) -> str:
        """
        Format ISBN to standard ISBN-13 format with hyphens.
        Example: 978-0-545-00395-7

        Args:
            isbn: ISBN string

        Returns:
            Formatted ISBN-13 string
        """
        normalized = ISBNValidator.normalize(isbn)
        cleaned = re.sub(r'[^\d]', '', normalized)

        if len(cleaned) == 13:
            return f"{cleaned[0:3]}-{cleaned[3]}-{cleaned[4:7]}-{cleaned[7:12]}-{cleaned[12]}"
        elif len(cleaned) == 10:
            # Convert ISBN-10 to ISBN-13
            isbn_13 = "978" + cleaned[:-1]
            total = sum(int(digit) * (1 if i % 2 == 0 else 3)
                        for i, digit in enumerate(isbn_13))
            check_digit = (10 - (total % 10)) % 10
            isbn_13 = isbn_13 + str(check_digit)
            return f"{isbn_13[0:3]}-{isbn_13[3]}-{isbn_13[4:7]}-{isbn_13[7:12]}-{isbn_13[12]}"

        return cleaned


def validate_isbn(isbn: str) -> tuple[bool, str]:
    """
    Validate ISBN and return formatted result.

    Args:
        isbn: ISBN string

    Returns:
        Tuple of (is_valid, formatted_isbn)
    """
    if not ISBNValidator.is_valid(isbn):
        return False, ""

    return True, ISBNValidator.format_isbn_13(isbn)
