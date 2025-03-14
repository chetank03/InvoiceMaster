import re
import sys


class RegexConverter:
    """A class for converting plain strings to regex patterns and testing them."""

    def __init__(self):
        # Define regex special characters that need escaping
        self.regex_special_chars = r".^$*+?()[]{}|\\"

    def string_to_regex(
        self,
        input_string,
        generic_matching=True,
        full_match=False,
    ):
        """
        Convert a plain string to a regex pattern.

        Args:
            input_string: The string to convert
            generic_matching: If True, letters match any letter, numbers match any number,
                              and quoted text is matched exactly
            full_match: If True, add anchors ^ and $ to match the entire string

        Returns:
            A regex pattern string
        """
        result = ""

        if not generic_matching:
            # Standard conversion (original behavior)
            # Escape special regex characters
            pattern = "".join(
                [f"\\{c}" if c in self.regex_special_chars else c for c in input_string]
            )
            result = pattern
        else:
            # Generic matching mode - handle quoted sections and convert letters/numbers
            parts = []
            i = 0
            in_quotes = False
            quote_buffer = ""

            while i < len(input_string):
                char = input_string[i]

                # Handle quotes
                if char == '"':
                    if in_quotes:
                        # End of quoted section - escape any special regex chars and add to result
                        escaped = "".join(
                            [
                                f"\\{c}" if c in self.regex_special_chars else c
                                for c in quote_buffer
                            ]
                        )
                        parts.append(escaped)
                        quote_buffer = ""
                        in_quotes = False
                    else:
                        # Start of quoted section
                        in_quotes = True
                    i += 1
                    continue

                if in_quotes:
                    # Inside quotes - collect characters
                    quote_buffer += char
                    i += 1
                    continue

                # Handle spaces - preserve them exactly
                if char.isspace():
                    # Count consecutive spaces
                    space_count = 1
                    j = i + 1
                    while j < len(input_string) and input_string[j].isspace():
                        space_count += 1
                        j += 1

                    if space_count > 1:
                        parts.append(f"\\s{{{space_count}}}")
                    else:
                        parts.append("\\s")
                    i += space_count
                    continue

                # Optimize for consecutive characters of the same type
                elif char.isalpha():
                    # Count consecutive letters
                    letter_count = 1
                    j = i + 1
                    while j < len(input_string) and input_string[j].isalpha():
                        letter_count += 1
                        j += 1

                    # Use quantifier for multiple letters
                    if letter_count > 1:
                        parts.append(f"[a-zA-Z]{{{letter_count}}}")
                        i += letter_count
                    else:
                        parts.append("[a-zA-Z]")
                        i += 1

                elif char.isdigit():
                    # Count consecutive digits
                    digit_count = 1
                    j = i + 1
                    while j < len(input_string) and input_string[j].isdigit():
                        digit_count += 1
                        j += 1

                    # Use quantifier for multiple digits
                    if digit_count > 1:
                        parts.append(f"\\d{{{digit_count}}}")
                        i += digit_count
                    else:
                        parts.append("\\d")
                        i += 1

                else:
                    # Escape special regex characters
                    if char in self.regex_special_chars:
                        parts.append(f"\\{char}")
                    else:
                        parts.append(char)
                    i += 1

            # Handle any remaining quoted text
            if quote_buffer:
                escaped = "".join(
                    [
                        f"\\{c}" if c in self.regex_special_chars else c
                        for c in quote_buffer
                    ]
                )
                parts.append(escaped)

            result = "".join(parts)

        # Add anchors if full match is requested
        if full_match:
            result = f"^{result}$"

        return result

    def test_regex(self):
        """Test the current regex against the test text"""
        pattern = self.regex_edit.text()
        test_text = self.test_edit.text()
        if not pattern or not test_text:
            return

        try:
            import re

            # Check if pattern has capture groups
            has_capture_group = "(" in pattern and re.search(r"\([^)]*\)", pattern)

            regex = re.compile(pattern)
            match = regex.search(test_text)

            if match:
                if match.groups():
                    self.test_result_label.setText(
                        f"MATCH! Found: '{match.group(0)}', Captured: '{match.group(1)}'"
                    )
                    self.test_result_label.setStyleSheet("color: green;")
                else:
                    # Warning for missing capture groups
                    self.test_result_label.setText(
                        f"MATCH! Found: '{match.group(0)}' - WARNING: NO CAPTURE GROUP! Add parentheses."
                    )
                    self.test_result_label.setStyleSheet("color: orange;")

                    # Suggest fix by adding capture groups
                    suggested_pattern = f"({pattern})"
                    reply = QMessageBox.question(
                        self,
                        "Missing Capture Group",
                        f"Your pattern doesn't have capture groups, which are required for extraction.\n\n"
                        f"Would you like to add them automatically? \n\nSuggested: {suggested_pattern}",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes,
                    )
                    if reply == QMessageBox.Yes:
                        self.regex_edit.setText(suggested_pattern)
                        # Test again with new pattern
                        self.test_regex()
            else:
                self.test_result_label.setText("No match.")
                self.test_result_label.setStyleSheet("")
        except Exception as e:
            self.test_result_label.setText(f"Error: {str(e)}")
            self.test_result_label.setStyleSheet("color: red;")

    def compile_pattern(
        self,
        input_string,
        generic_matching=True,
        full_match=False,
    ):
        """
        Convert string to regex and compile it in one step

        Returns:
            Compiled regex pattern
        """
        pattern = self.string_to_regex(input_string, generic_matching, full_match)
        return re.compile(pattern)


def main():
    """Run the converter as a standalone application"""
    print("Convert String to Regular Expression")
    print("===================================")

    converter = RegexConverter()

    # Get input string
    if len(sys.argv) > 1:
        input_string = sys.argv[1]
    else:
        input_string = input("Enter string to convert to regex: ")

    # Always use generic matching and don't require full match
    generic_matching = True
    full_match = False

    # Convert to regex
    regex_pattern = converter.string_to_regex(
        input_string, generic_matching, full_match
    )

    # Display the result
    print("\nRegex Pattern:")
    print(regex_pattern)

    # Offer to test the pattern
    test_pattern = input("\nTest this pattern? (y/n): ").lower().startswith("y")
    if test_pattern:
        print("Enter test strings (empty line to finish):")
        test_strings = []
        while True:
            test_input = input("> ")
            if not test_input:
                break
            test_strings.append(test_input)

        if test_strings:
            print("\nTest Results:")
            for string, matched, matched_text in converter.test_regex(
                regex_pattern, test_strings, full_match
            ):
                result = "MATCH" if matched else "NO MATCH"
                if matched:
                    print(f"{string}: {result} (matched: '{matched_text}')")
                else:
                    print(f"{string}: {result}")


if __name__ == "__main__":
    main()
