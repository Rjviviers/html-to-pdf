"""
HTML to PDF converter module using WeasyPrint.
Handles individual file conversion with automatic bookmark generation.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import weasyprint
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, NumberObject

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HTMLToPDFConverter:
    """Handles conversion of HTML files to PDF with bookmarks."""
    
    def __init__(self):
        """Initialize the converter with font configuration."""
        self.font_config = FontConfiguration()
        # Reserve space so any fixed-position headers/footers in HTML won't cover content
        # Can be tuned via env vars HEADER_SPACE_MM / FOOTER_SPACE_MM, or disabled with DISABLE_SAFE_HEADER_FOOTER
        try:
            header_space_mm = float(os.getenv('HEADER_SPACE_MM', '18'))
        except ValueError:
            header_space_mm = 18.0
        try:
            footer_space_mm = float(os.getenv('FOOTER_SPACE_MM', '16'))
        except ValueError:
            footer_space_mm = 16.0
        self._disable_safe_header_footer = os.getenv('DISABLE_SAFE_HEADER_FOOTER') is not None
        # Note: we avoid overriding @page margins; we rely on body padding so existing
        # document margins/sizes are respected while ensuring content doesn't sit under
        # fixed headers/footers.
        self._safety_css = (
            """
            /* Injected to prevent overlap of fixed headers/footers with page content */
            html, body { margin: 0; }
            body {
              padding-top: %(header_mm).3fmm;
              padding-bottom: %(footer_mm).3fmm;
            }
            /* Common header/footer selectors pinned to page edges */
            header, .header, #header, .page-header, #page-header {
              position: fixed;
              top: 0; left: 0; right: 0;
            }
            footer, .footer, #footer, .page-footer, #page-footer {
              position: fixed;
              bottom: 0; left: 0; right: 0;
            }
            /* Keep content from slipping behind fixed elements near page edges */
            main { margin: 0; }
            """
            % {"header_mm": header_space_mm, "footer_mm": footer_space_mm}
        )
    
    def convert_file(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """
        Convert a single HTML file to PDF.
        
        Args:
            input_path: Path to the input HTML file
            output_path: Path for the output PDF file
            
        Returns:
            Dictionary with conversion result information
        """
        try:
            # Validate input file exists
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"Input file not found: {input_path}")
            
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # Convert HTML to PDF with WeasyPrint
            logger.info(f"Converting {input_path} to {output_path}")
            
            # Load HTML document
            html_doc = HTML(filename=input_path)
            
            # Generate PDF with automatic bookmarks from headings
            # WeasyPrint automatically creates bookmarks from h1-h6 elements
            extra_stylesheets = None if self._disable_safe_header_footer else [CSS(string=self._safety_css)]
            pdf_bytes = html_doc.write_pdf(
                font_config=self.font_config,
                optimize_images=True,  # Optimize images for better performance
                stylesheets=extra_stylesheets
            )
            
            # Write PDF to file
            with open(output_path, 'wb') as pdf_file:
                pdf_file.write(pdf_bytes)

            # Optionally collapse bookmarks by default (skipped for large PDFs)
            try:
                disable = os.getenv('DISABLE_COLLAPSE')
                max_mb_env = os.getenv('COLLAPSE_MAX_MB', '5')
                try:
                    max_mb = float(max_mb_env)
                except ValueError:
                    max_mb = 5.0
                should_collapse = (disable is None)
                if should_collapse:
                    out_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    if out_size_mb <= max_mb:
                        self._collapse_pdf_bookmarks_in_place(output_path)
                    else:
                        logger.info(
                            f"Skipping bookmark collapse for large PDF ({out_size_mb:.1f} MB > {max_mb:.1f} MB)"
                        )
            except Exception as collapse_err:
                logger.warning(f"Bookmark collapse skipped: {collapse_err}")
            
            # Get file sizes for reporting
            input_size = os.path.getsize(input_path)
            output_size = os.path.getsize(output_path)
            
            result = {
                'status': 'success',
                'input_file': input_path,
                'output_file': output_path,
                'input_size': input_size,
                'output_size': output_size,
                'message': f'Successfully converted {os.path.basename(input_path)}'
            }
            
            logger.info(f"Conversion successful: {input_path} -> {output_path}")
            return result
            
        except Exception as e:
            error_msg = f"Failed to convert {input_path}: {str(e)}"
            logger.error(error_msg)
            
            return {
                'status': 'error',
                'input_file': input_path,
                'output_file': output_path,
                'error': str(e),
                'message': error_msg
            }

    def _collapse_pdf_bookmarks_in_place(self, pdf_path: str) -> None:
        """Collapse all bookmarks in the PDF so they are closed by default."""
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        writer.clone_document_from_reader(reader)

        root = writer._root_object
        outlines_ref = root.get(NameObject('/Outlines'))
        if outlines_ref is None:
            # No outlines present; just rewrite and return
            with open(pdf_path, 'wb') as out_f:
                writer.write(out_f)
            return

        def count_descendants(item_ref) -> int:
            total = 0
            item = item_ref.get_object()
            child_ref = item.get(NameObject('/First'))
            while child_ref is not None:
                total += 1
                total += count_descendants(child_ref)
                child_ref = child_ref.get_object().get(NameObject('/Next'))
            return total

        def collapse_item(item_ref) -> None:
            item = item_ref.get_object()
            num_desc = count_descendants(item_ref)
            if num_desc > 0:
                item[NameObject('/Count')] = NumberObject(-num_desc)
                child_ref = item.get(NameObject('/First'))
                while child_ref is not None:
                    collapse_item(child_ref)
                    child_ref = child_ref.get_object().get(NameObject('/Next'))

        first_ref = outlines_ref.get_object().get(NameObject('/First'))
        while first_ref is not None:
            collapse_item(first_ref)
            first_ref = first_ref.get_object().get(NameObject('/Next'))

        with open(pdf_path, 'wb') as out_f:
            writer.write(out_f)
    
    def validate_html_file(self, file_path: str) -> bool:
        """
        Validate if a file is a valid HTML file.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            True if file is valid HTML, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                return False
            
            # Check file extension
            if not file_path.lower().endswith(('.html', '.htm')):
                return False
            
            # Try to load with WeasyPrint to validate
            HTML(filename=file_path)
            return True
            
        except Exception as e:
            logger.warning(f"Invalid HTML file {file_path}: {e}")
            return False


def convert_single_file(args: tuple) -> Dict[str, Any]:
    """
    Worker function for multiprocessing conversion.
    
    Args:
        args: Tuple containing (input_path, output_path)
        
    Returns:
        Conversion result dictionary
    """
    input_path, output_path = args
    converter = HTMLToPDFConverter()
    return converter.convert_file(input_path, output_path)


if __name__ == "__main__":
    # Test the converter
    converter = HTMLToPDFConverter()
    
    # Example usage
    test_input = "test.html"
    test_output = "test.pdf"
    
    if os.path.exists(test_input):
        result = converter.convert_file(test_input, test_output)
        print(f"Conversion result: {result}")
    else:
        print(f"Test file {test_input} not found")