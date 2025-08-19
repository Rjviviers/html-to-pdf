#!/usr/bin/env python3
"""
Minimal test to isolate the WeasyPrint issue.
"""

import os
from pathlib import Path

def test_minimal_weasyprint():
    """Test WeasyPrint with minimal configuration."""
    try:
        print("1. Importing weasyprint...")
        import weasyprint
        print("✅ WeasyPrint imported")
        
        print("2. Testing HTML class...")
        html_content = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><h1>Hello World</h1><p>This is a test.</p></body>
</html>"""
        
        html_doc = weasyprint.HTML(string=html_content)
        print("✅ HTML object created")
        
        print("3. Testing write_pdf without font_config...")
        pdf_bytes = html_doc.write_pdf()
        print(f"✅ PDF generated: {len(pdf_bytes)} bytes")
        
        # Write to file
        output_path = Path("pdf-export/minimal-test.pdf")
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        
        print(f"✅ PDF saved to: {output_path}")
        
        # Verify file
        if output_path.exists():
            size = output_path.stat().st_size
            print(f"✅ File verified: {size} bytes")
            return True
        else:
            print("❌ File not created")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_file_conversion():
    """Test converting the actual sample file."""
    try:
        print("\n4. Testing file conversion...")
        import weasyprint
        
        input_file = Path("html-drop/sample-document.html")
        if not input_file.exists():
            print("❌ Sample file not found")
            return False
        
        print(f"✅ Found input file: {input_file}")
        
        # Simple conversion without font config
        html_doc = weasyprint.HTML(filename=str(input_file))
        pdf_bytes = html_doc.write_pdf()
        
        output_file = Path("pdf-export/file-test.pdf")
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'wb') as f:
            f.write(pdf_bytes)
        
        print(f"✅ Converted to: {output_file}")
        print(f"✅ Size: {len(pdf_bytes)} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ File conversion error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔬 Minimal WeasyPrint Test")
    print("=" * 30)
    
    success1 = test_minimal_weasyprint()
    success2 = test_file_conversion() if success1 else False
    
    if success1 and success2:
        print("\n🎉 ALL TESTS PASSED!")
        print("WeasyPrint is working correctly!")
    else:
        print("\n❌ Some tests failed")
    
    exit(0 if (success1 and success2) else 1)
