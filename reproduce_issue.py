import sys
import os
from pathlib import Path

# Add src-backend to path
sys.path.insert(0, str(Path(__file__).parent / 'src-backend'))

from converter import HTMLToPDFConverter

def reproduce():
    converter = HTMLToPDFConverter()
    
    # Snippet 1: Height 100% on body (potential issue with injected padding)
    html_height_100 = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            html, body { height: 100%; margin: 0; }
            .content { height: 100%; background: lightblue; }
        </style>
    </head>
    <body>
        <div class="content">This has height: 100%. If padding is added to body, it might overflow.</div>
    </body>
    </html>
    """
    
    # Snippet 2: Large element with page-break-inside: avoid
    html_page_break_avoid = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            .container { page-break-inside: avoid; border: 1px solid red; height: 1500px; }
        </style>
    </head>
    <body>
        <h1>Large block with page-break-inside: avoid</h1>
        <div class="container">This block is taller than a single page and has page-break-inside: avoid.</div>
    </body>
    </html>
    """
    
    # Snippet 3: Overflow: hidden on body
    html_overflow_hidden = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { overflow: hidden; }
        </style>
    </head>
    <body>
        <h1>Overflow Hidden</h1>
        <div style="height: 2000px; background: yellow;">This is a very tall div.</div>
    </body>
    </html>
    """

    test_cases = {
        "height_100.html": html_height_100,
        "page_break_avoid.html": html_page_break_avoid,
        "overflow_hidden.html": html_overflow_hidden
    }

    os.makedirs("reproduction", exist_ok=True)

    for filename, content in test_cases.items():
        html_path = f"reproduction/{filename}"
        pdf_path = f"reproduction/{filename.replace('.html', '.pdf')}"
        
        with open(html_path, "w") as f:
            f.write(content)
            
        print(f"Testing {filename}...")
        result = converter.convert_file(html_path, pdf_path)
        print(f"Result for {filename}: {result['status']}")
        if result['status'] == 'success':
            size = os.path.getsize(pdf_path)
            print(f"PDF Size: {size} bytes")

if __name__ == "__main__":
    reproduce()
