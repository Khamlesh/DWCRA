#!/usr/bin/env python3
"""
Script to convert DWCRA User Guide HTML to PDF
Requires: pip install weasyprint
"""

import os
from weasyprint import HTML

def convert_html_to_pdf():
    """Convert the HTML user guide to PDF"""
    try:
        # Input and output file paths
        html_file = 'static/DWCRA_USER_GUIDE.html'
        pdf_file = 'static/DWCRA_USER_GUIDE.pdf'
        
        # Check if HTML file exists
        if not os.path.exists(html_file):
            print(f"Error: HTML file not found at {html_file}")
            return False
        
        # Convert HTML to PDF
        print(f"Converting {html_file} to PDF...")
        HTML(html_file).write_pdf(pdf_file)
        
        # Check if PDF was created successfully
        if os.path.exists(pdf_file):
            file_size = os.path.getsize(pdf_file) / (1024 * 1024)  # Size in MB
            print(f"✅ Successfully created {pdf_file}")
            print(f"📄 File size: {file_size:.2f} MB")
            return True
        else:
            print("❌ PDF file was not created")
            return False
            
    except ImportError:
        print("❌ Error: weasyprint not installed")
        print("Install it with: pip install weasyprint")
        return False
    except Exception as e:
        print(f"❌ Error converting to PDF: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔄 DWCRA User Guide HTML to PDF Converter")
    print("=" * 50)
    
    success = convert_html_to_pdf()
    
    if success:
        print("\n🎉 Conversion completed successfully!")
        print("📁 PDF file is available at: static/DWCRA_USER_GUIDE.pdf")
        print("🔗 You can now update the home.html link to point to the PDF file")
    else:
        print("\n❌ Conversion failed. Please check the error messages above.") 