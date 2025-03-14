import re
import logging
import os
from PyQt5.QtCore import QSettings

# Try importing pdfplumber for PDF text extraction
try:
    import pdfplumber
except ImportError:
    logging.error(
        "pdfplumber not found. Please install it with: pip install pdfplumber"
    )

# Configure a module-specific logger to control log output
pdf_logger = logging.getLogger(__name__)
pdf_logger.setLevel(logging.INFO)  # Change to INFO to reduce debug output


class PDFExtractor:
    """Class to extract structured data from invoice PDFs"""

    def __init__(self):
        # Load regular expression patterns from settings or use defaults
        self.patterns = self.load_patterns()
        # Load GST to company mappings from persistent settings
        self.gst_company_mappings = self.load_gst_mappings()

    def load_patterns(self):
        """
        Load regex patterns from QSettings or return default patterns if not found.

        Returns:
            dict: Dictionary containing regex patterns for keys like 'gst_number',
                  'invoice_number', 'amount', and 'company_name'.
        """
        try:
            settings = QSettings("MyCompany", "PDFOrganizer")
            if settings.contains("regex_patterns"):
                patterns = settings.value("regex_patterns")
                if patterns:
                    return patterns
        except Exception as e:
            pdf_logger.error(f"Failed to load regex patterns from settings: {e}")

        # Default regex patterns if settings loading fails
        return {
            "gst_number": [
                r"GST(?:\s+|:|\s*No\.?\s*|Number\s*:?)\s*([0-9A-Z]{15})",
                r"GSTIN\s*:?\s*([0-9A-Z]{15})",
            ],
            "invoice_number": [
                r"Invoice\s+(?:No\.?|Number|#)\s*:?\s*([\w\d\-/]+)",
                r"Bill\s+(?:No\.?|Number|#)\s*:?\s*([\w\d\-/]+)",
                r"(?:Invoice|Bill)\s*:?\s*([\w\d\-/]+)",
            ],
            "amount": [
                r"Total\s+Amount\s*:?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)",
                r"Grand\s+Total\s*:?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)",
                r"Amount\s+(?:Due|Payable|Total)\s*:?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)",
                r"(?:Rs\.?|INR|₹)\s*([\d,]+\.?\d*)",
            ],
            "company_name": [
                r"(?:Company|Business|Vendor|Seller|From)[\s:]+([^\n]+)",
                r"(?:^|\n)([A-Z][A-Za-z\s]+(?:Ltd|Limited|Inc|LLC|LLP|Pvt|Corporation|Corp|\&\s*Co)\.?)(?:\n|$)",
                r"(?:^|\n)([A-Z][A-Za-z\s,]+)(?:\n)(?:[A-Za-z0-9\s,]+){1,2}(?:GST)",
            ],
        }

    def extract_from_pdf(self, pdf_path, all_matches=False):
        """
        Extract invoice data from a PDF file.

        This method reads the PDF content (currently processing only the first page for efficiency),
        prints the extracted text, then uses regular expression patterns to extract structured data.

        Args:
            pdf_path (str): Path to the PDF file.
            all_matches (bool): If True, collect all possible invoice number matches
                                and GST candidates.

        Returns:
            dict: Extracted data with keys 'company_name', 'gst_number', 'invoice_number', and 'amount'.
                  If all_matches is True, also includes 'invoice_number_candidates' (and possibly 'gst_number_candidates').
        """
        # Initialize result dictionary with empty strings
        result = {
            "company_name": "",
            "gst_number": "",
            "invoice_number": "",
            "amount": "",
        }

        # When collecting candidate matches, initialize an empty list for invoice numbers.
        if all_matches:
            result["invoice_number_candidates"] = []

        # If the PDF file does not exist, log an error and return the empty result.
        if not os.path.exists(pdf_path):
            pdf_logger.error(f"PDF file not found: {pdf_path}")
            return result

        try:
            # Open the PDF file using pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                # Extract text from the first page only for efficiency
                for i, page in enumerate(pdf.pages[:1]):  # Process only first page(s)
                    page_text = page.extract_text() or ""
                    text += page_text + "\n"

                # Print the extracted text to the console for debugging purposes
                print("\n" + "=" * 50)
                print(f"EXTRACTED TEXT FROM {os.path.basename(pdf_path)}:")
                print("=" * 50)
                print(text)
                print("=" * 50 + "\n")
                # Also log the extracted text (at debug level)
                pdf_logger.debug(f"Extracted text from {pdf_path}:\n{text}")

                # Iterate over regex patterns for each field (e.g., gst_number, invoice_number, etc.)
                for field, pattern_list in self.patterns.items():
                    for pattern in pattern_list:
                        try:
                            # For invoice numbers, if collecting all matches as candidates:
                            if field == "invoice_number" and all_matches:
                                matches = re.finditer(pattern, text, re.IGNORECASE)
                                for match in matches:
                                    try:
                                        candidate = match.group(1).strip()
                                        # Avoid duplicates in candidate list
                                        if (
                                            candidate
                                            and candidate
                                            not in result["invoice_number_candidates"]
                                        ):
                                            result["invoice_number_candidates"].append(
                                                candidate
                                            )
                                    except IndexError:
                                        candidate = match.group(0).strip()
                                        if (
                                            candidate
                                            and candidate
                                            not in result["invoice_number_candidates"]
                                        ):
                                            result["invoice_number_candidates"].append(
                                                candidate
                                            )
                                # Continue to next pattern once candidates are collected
                                continue

                            # For GST numbers, if all_matches is True, try to collect all candidates
                            if field == "gst_number" and all_matches:
                                matches = re.finditer(pattern, text, re.IGNORECASE)
                                gst_candidates = []
                                for match in matches:
                                    try:
                                        candidate = match.group(1).strip()
                                    except IndexError:
                                        candidate = match.group(0).strip()
                                    # Remove non-alphanumeric characters for clean GST number
                                    candidate = re.sub(r"[^0-9A-Za-z]", "", candidate)
                                    if candidate and candidate not in gst_candidates:
                                        gst_candidates.append(candidate)
                                if gst_candidates:
                                    # If there's a single candidate, use it; else, store all candidates
                                    if len(gst_candidates) == 1:
                                        result[field] = gst_candidates[0]
                                    else:
                                        result["gst_number_candidates"] = gst_candidates
                                        # Break out once multiple candidates are found
                                        break
                                continue

                            # For other fields, perform a simple search
                            match = re.search(pattern, text, re.IGNORECASE)
                            if match:
                                try:
                                    result[field] = match.group(1).strip()
                                except IndexError:
                                    result[field] = match.group(0).strip()
                                    pdf_logger.warning(
                                        f"Pattern {pattern} doesn't have a capture group, using full match"
                                    )
                                # For GST numbers, reformat by removing non-alphanumeric characters
                                if field == "gst_number":
                                    result[field] = re.sub(
                                        r"[^0-9A-Za-z]", "", result[field]
                                    )
                                pdf_logger.info(
                                    f"Found {field}: '{result[field]}' using pattern: {pattern}"
                                )
                                # Once a matching pattern is found, stop testing further patterns for this field
                                break
                        except Exception as e:
                            pdf_logger.error(f"Error with pattern '{pattern}': {e}")
                            continue

                # Post-process the amount field to remove any commas (for numerical conversion)
                if result["amount"]:
                    result["amount"] = result["amount"].replace(",", "")

                # If a GST number is found but company_name is empty, try to fill it using mappings
                if result["gst_number"] and not result["company_name"]:
                    if result["gst_number"] in self.gst_company_mappings:
                        result["company_name"] = self.gst_company_mappings[
                            result["gst_number"]
                        ]
                        pdf_logger.info(
                            f"Using mapped company name for GST {result['gst_number']}: {result['company_name']}"
                        )

            # Log the final extracted result and return it
            pdf_logger.info(f"Extracted from PDF: {result}")
            return result

        except Exception as e:
            pdf_logger.error(f"Error extracting data from PDF: {e}")
            return result

    def load_gst_mappings(self):
        """
        Load GST to company mappings from QSettings.

        Returns:
            dict: A mapping of GST numbers to company names.
        """
        try:
            settings = QSettings("MyCompany", "PDFOrganizer")
            return settings.value("gst_company_mappings", {}) or {}
        except Exception as e:
            pdf_logger.error(f"Failed to load GST company mappings: {e}")
            return {}
