#!/usr/bin/env python3
"""
Simple test script for HTML-to-PDF conversion.
"""

import os
import sys
from pathlib import Path

# Add the src-backend directory to Python path
sys.path.insert(0, 'src-backend')

def test_direct_conversion():
    """Test the converter directly."""
    try:
        from converter import HTMLToPDFConverter
        print("✅ Converter imported successfully")
        
        # Check sample file
        input_file = Path("html-drop/sample-document.html")
        if not input_file.exists():
            print("❌ Sample file not found")
            return False
        
        print(f"✅ Found sample file: {input_file}")
        
        # Set up output
        output_dir = Path("pdf-export")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "test-output.pdf"
        
        # Remove existing file
        if output_file.exists():
            output_file.unlink()
        
        # Create converter and convert
        converter = HTMLToPDFConverter()
        print(f"🔄 Converting {input_file.name}...")
        
        result = converter.convert_file(str(input_file), str(output_file))
        
        print(f"📊 Conversion result: {result}")
        
        if result['status'] == 'success' and output_file.exists():
            file_size = output_file.stat().st_size
            print(f"✅ SUCCESS! PDF created: {file_size:,} bytes")
            print(f"📁 Location: {output_file.absolute()}")
            
            # Try to check if it's a valid PDF
            with open(output_file, 'rb') as f:
                header = f.read(10)
                if header.startswith(b'%PDF'):
                    print("✅ File has valid PDF header")
                else:
                    print("⚠️ File may not be a valid PDF")
            
            return True
        else:
            print(f"❌ Conversion failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Simple HTML-to-PDF Conversion Test")
    print("=" * 40)
    
    success = test_direct_conversion()
    
    if success:
        print("\n🎉 Test PASSED! Your converter is working!")
    else:
        print("\n❌ Test FAILED. Check the error messages above.")
    
    sys.exit(0 if success else 1)
