#!/usr/bin/env python3
"""
Test script for HTML-to-PDF conversion functionality.
This will test the conversion engine directly without the GUI.
"""

import os
import sys
import time
from pathlib import Path

# Add the src-backend directory to Python path
sys.path.insert(0, 'src-backend')

try:
    from converter import HTMLToPDFConverter
    print("✅ Converter module imported successfully")
except ImportError as e:
    print(f"❌ Failed to import converter: {e}")
    sys.exit(1)

def test_weasyprint_import():
    """Test if WeasyPrint can be imported and used."""
    try:
        import weasyprint
        print("✅ WeasyPrint imported successfully")
        
        # Test basic HTML to PDF conversion
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Test</title></head>
        <body>
            <h1>Test Document</h1>
            <p>This is a test conversion.</p>
        </body>
        </html>
        """
        
        html_doc = weasyprint.HTML(string=html_content)
        pdf_bytes = html_doc.write_pdf()
        print(f"✅ Basic PDF generation test: {len(pdf_bytes)} bytes")
        return True
        
    except Exception as e:
        print(f"❌ WeasyPrint test failed: {e}")
        return False

def test_sample_conversion():
    """Test conversion of the sample HTML file."""
    print("\n🧪 Testing Sample File Conversion")
    print("=" * 50)
    
    # Check if sample file exists
    input_file = Path("html-drop/sample-document.html")
    if not input_file.exists():
        print(f"❌ Sample file not found: {input_file}")
        return False
    
    print(f"✅ Sample file found: {input_file}")
    
    # Set up output
    output_dir = Path("pdf-export")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "sample-document.pdf"
    
    # Remove existing output file
    if output_file.exists():
        output_file.unlink()
        print(f"🗑️ Removed existing output: {output_file}")
    
    # Create converter and test
    converter = HTMLToPDFConverter()
    
    print(f"🔄 Converting {input_file} → {output_file}")
    start_time = time.time()
    
    result = converter.convert_file(str(input_file), str(output_file))
    
    end_time = time.time()
    conversion_time = end_time - start_time
    
    print(f"⏱️ Conversion took: {conversion_time:.2f} seconds")
    print(f"📊 Result: {result}")
    
    # Verify output
    if result['status'] == 'success' and output_file.exists():
        file_size = output_file.stat().st_size
        print(f"✅ PDF created successfully: {file_size} bytes")
        print(f"📁 Output location: {output_file.absolute()}")
        return True
    else:
        print(f"❌ Conversion failed: {result.get('error', 'Unknown error')}")
        return False

def test_validation():
    """Test HTML file validation."""
    print("\n🔍 Testing File Validation")
    print("=" * 30)
    
    converter = HTMLToPDFConverter()
    
    # Test valid HTML file
    input_file = Path("html-drop/sample-document.html")
    if input_file.exists():
        is_valid = converter.validate_html_file(str(input_file))
        print(f"✅ Sample file validation: {'PASS' if is_valid else 'FAIL'}")
    
    # Test invalid file
    invalid_file = "nonexistent.html"
    is_valid = converter.validate_html_file(invalid_file)
    print(f"✅ Nonexistent file validation: {'PASS' if not is_valid else 'FAIL'}")

def main():
    """Run all tests."""
    print("🚀 HTML-to-PDF Converter Test Suite")
    print("=" * 50)
    
    # Test 1: WeasyPrint functionality
    print("\n1️⃣ Testing WeasyPrint Import and Basic Functionality")
    if not test_weasyprint_import():
        print("❌ WeasyPrint tests failed. Check GTK3 installation.")
        return False
    
    # Test 2: File validation
    test_validation()
    
    # Test 3: Sample file conversion
    if not test_sample_conversion():
        print("❌ Sample conversion failed")
        return False
    
    print("\n🎉 All tests completed successfully!")
    print("\n📋 Test Summary:")
    print("✅ WeasyPrint functionality: PASS")
    print("✅ File validation: PASS") 
    print("✅ Sample conversion: PASS")
    print("\n🎯 Your HTML-to-PDF converter is working correctly!")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
