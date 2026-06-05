#!/usr/bin/env python3
"""
Comprehensive script to create detailed PDF user guides from HTML content
"""

import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from bs4 import BeautifulSoup

def extract_html_content(html_file):
    """Extract content from HTML file using BeautifulSoup"""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        return soup
    except Exception as e:
        print(f"Error reading HTML file {html_file}: {e}")
        return None

def create_english_pdf_from_html():
    """Create comprehensive English PDF from HTML content"""
    soup = extract_html_content('static/DWCRA_USER_GUIDE.html')
    if not soup:
        return False
    
    doc = SimpleDocTemplate("static/dwcra_user_guide_english.pdf", pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#3F51B5'),
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=14,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.grey,
        fontName='Helvetica'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=15,
        spaceBefore=20,
        textColor=colors.HexColor('#3F51B5'),
        fontName='Helvetica-Bold'
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=14,
        spaceAfter=10,
        spaceBefore=15,
        textColor=colors.HexColor('#5C6BC0'),
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8,
        alignment=TA_JUSTIFY,
        fontName='Helvetica'
    )
    
    step_style = ParagraphStyle(
        'StepStyle',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8,
        leftIndent=20,
        fontName='Helvetica'
    )
    
    # Title
    story.append(Paragraph("DWCRA System - Complete User Guide", title_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Step-by-Step Instructions for All Users", subtitle_style))
    story.append(Paragraph("Development of Women and Children in Rural Areas", subtitle_style))
    story.append(Spacer(1, 30))
    
    # Extract and process content
    sections = soup.find_all('div', class_='section')
    
    for section in sections:
        # Get section title
        h2 = section.find('h2')
        if h2:
            title_text = h2.get_text().strip()
            # Remove emoji and clean title
            title_text = re.sub(r'[📋🎯🚀📝🔐👥👤🔧👤🚪🔧📋📞📊]', '', title_text).strip()
            story.append(Paragraph(title_text, heading_style))
        
        # Process content
        for element in section.children:
            if element.name == 'h3':
                sub_title = element.get_text().strip()
                sub_title = re.sub(r'[📋🎯🚀📝🔐👥👤🔧👤🚪🔧📋📞📊]', '', sub_title).strip()
                story.append(Paragraph(sub_title, subheading_style))
            
            elif element.name == 'div' and 'step' in element.get('class', []):
                step_text = element.get_text().strip()
                story.append(Paragraph(step_text, step_style))
            
            elif element.name == 'p':
                p_text = element.get_text().strip()
                if p_text:
                    story.append(Paragraph(p_text, normal_style))
            
            elif element.name == 'ul':
                for li in element.find_all('li'):
                    li_text = li.get_text().strip()
                    if li_text:
                        story.append(Paragraph(f"• {li_text}", step_style))
            
            elif element.name == 'ol':
                for i, li in enumerate(element.find_all('li'), 1):
                    li_text = li.get_text().strip()
                    if li_text:
                        story.append(Paragraph(f"{i}. {li_text}", step_style))
            
            elif element.name == 'table':
                # Process tables
                table_data = []
                for row in element.find_all('tr'):
                    row_data = []
                    for cell in row.find_all(['th', 'td']):
                        cell_text = cell.get_text().strip()
                        row_data.append(cell_text)
                    if row_data:
                        table_data.append(row_data)
                
                if table_data:
                    table = Table(table_data)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3F51B5')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 12),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 10),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 15))
        
        story.append(Spacer(1, 20))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.grey,
        fontName='Helvetica'
    )
    story.append(Spacer(1, 30))
    story.append(Paragraph("© 2025 DWCRA Portal. All rights reserved.", footer_style))
    
    doc.build(story)
    print("✅ Comprehensive English PDF created successfully")
    return True

def create_telugu_pdf_from_html():
    """Create comprehensive Telugu PDF from HTML content"""
    soup = extract_html_content('static/DWCRA_TELUGU_GUIDE.html')
    if not soup:
        return False
    
    doc = SimpleDocTemplate("static/dwcra_user_guide_telugu.pdf", pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Custom styles for Telugu
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#3F51B5'),
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=14,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.grey,
        fontName='Helvetica'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=15,
        spaceBefore=20,
        textColor=colors.HexColor('#3F51B5'),
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8,
        alignment=TA_JUSTIFY,
        fontName='Helvetica'
    )
    
    # Title
    story.append(Paragraph("DWCRA వినియోగదారు గైడ్", title_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("అన్ని వినియోగదారులకు స్టెప్-బై-స్టెప్ సూచనలు", subtitle_style))
    story.append(Spacer(1, 30))
    
    # Extract content from Telugu HTML
    header = soup.find('div', class_='header')
    if header:
        h1 = header.find('h1')
        if h1:
            story.append(Paragraph(h1.get_text().strip(), heading_style))
        
        p_tags = header.find_all('p')
        for p in p_tags:
            p_text = p.get_text().strip()
            if p_text:
                story.append(Paragraph(p_text, normal_style))
    
    # Process sections
    sections = soup.find_all('div', class_='section')
    for section in sections:
        h2 = section.find('h2')
        if h2:
            title_text = h2.get_text().strip()
            story.append(Paragraph(title_text, heading_style))
        
        # Process content
        for element in section.children:
            if element.name == 'p':
                p_text = element.get_text().strip()
                if p_text:
                    story.append(Paragraph(p_text, normal_style))
            
            elif element.name == 'ul':
                for li in element.find_all('li'):
                    li_text = li.get_text().strip()
                    if li_text:
                        story.append(Paragraph(f"• {li_text}", normal_style))
        
        story.append(Spacer(1, 20))
    
    # Add comprehensive Telugu content since the HTML is placeholder
    comprehensive_sections = [
        ("సిస్టమ్ అవలోకనం", "DWCRA (గ్రామీణ ప్రాంతాలలో మహిళలు మరియు పిల్లల అభివృద్ధి) సిస్టమ్ అనేది స్వయం సహాయక సమూహాలు, రుణాలు మరియు చెల్లింపులను నిర్వహించడానికి రూపొందించబడిన సమగ్ర వెబ్-ఆధారిత ప్లాట్‌ఫార్మ్."),
        ("వినియోగదారు రకాలు", "• సమూహ నాయకులు: సమూహాలను నిర్వహించడం మరియు రుణాలకు దరఖాస్తు చేయడం\n• సమూహ సభ్యులు: చెల్లింపులు చేయడం మరియు చరిత్రను ట్రాక్ చేయడం\n• నిర్వాహకులు: మొత్తం సిస్టమ్‌ను పర్యవేక్షించడం"),
        ("ప్రారంభించడం", "1. మీ వెబ్ బ్రౌజర్‌ను తెరవండి\n2. DWCRA సిస్టమ్ URL‌కి నావిగేట్ చేయండి\n3. మీకు ఖాతా లేకపోతే 'New User? Register Here' క్లిక్ చేయండి\n4. మీ ధృవీకరణలను నమోదు చేసి లాగిన్ చేయండి"),
        ("నమోదు ప్రక్రియ", "అన్ని అవసరమైన ఫీల్డ్‌లను పూరించండి: ఏకైక ID, పూర్తి పేరు, ఇమెయిల్, బ్యాంక్ పేరు, పాస్‌వర్డ్ మరియు పాత్ర ఎంపిక."),
        ("లాగిన్ ప్రక్రియ", "మీ ఏకైక ID మరియు పాస్‌వర్డ్‌ను నమోదు చేసి, మీ డాష్‌బోర్డ్‌కి ప్రవేశించడానికి 'Secure Login' క్లిక్ చేయండి."),
        ("సమూహ నాయకుడు వర్క్‌ఫ్లో", "1. గుర్తింపు ధృవీకరణను పూర్తి చేయండి\n2. 6 మంది సభ్యులతో సమూహాన్ని సృష్టించండి\n3. రుణాలకు దరఖాస్తు చేయండి\n4. సమూహ స్థితిని పర్యవేక్షించండి"),
        ("సమూహ సభ్యుడు వర్క్‌ఫ్లో", "1. గుర్తింపు ధృవీకరణను పూర్తి చేయండి\n2. చెల్లింపులు చేయండి\n3. చెల్లింపు చరిత్రను చూడండి\n4. చెల్లింపు స్థితిని పర్యవేక్షించండి"),
        ("నిర్వాహక వర్క్‌ఫ్లో", "1. వినియోగదారులు మరియు సమూహాలను నిర్వహించండి\n2. గుర్తింపు ధృవీకరణలను ఆమోదించండి\n3. రుణాలను సమీక్షించి ఆమోదించండి\n4. నివేదికలను ఉత్పన్నం చేయండి"),
        ("ప్రొఫైల్ నిర్వహణ", "ప్రొఫైల్ విభాగం ద్వారా వ్యక్తిగత సమాచారాన్ని నవీకరించండి, గుర్తింపు ధృవీకరణను పూర్తి చేయండి మరియు పాస్‌వర్డ్‌లను నిర్వహించండి."),
        ("లాగౌట్ ప్రక్రియ", "మీ సెషన్‌ను సురక్షితంగా ముగించడానికి మరియు లాగిన్ పేజీకి తిరిగి రావడానికి 'Logout' బటన్‌ను క్లిక్ చేయండి."),
        ("షూటింగ్", "లాగిన్ సమస్యలు, నమోదు సమస్యలు, చెల్లింపు సమస్యలు మరియు సిస్టమ్ యాక్సెస్ కోసం సాధారణ సమస్యలు మరియు పరిష్కారాలు."),
        ("సిస్టమ్ అవసరాలు", "బ్రౌజర్ అనుకూలత, ఇంటర్నెట్ అవసరాలు మరియు సరైన సిస్టమ్ పనితీరు కోసం పరికర వివరాలు.")
    ]
    
    for title, content in comprehensive_sections:
        story.append(Paragraph(title, heading_style))
        story.append(Paragraph(content, normal_style))
        story.append(Spacer(1, 15))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.grey,
        fontName='Helvetica'
    )
    story.append(Spacer(1, 30))
    story.append(Paragraph("© 2025 DWCRA పోర్టల్. అన్ని హక్కులు ప్రత్యేకించబడ్డాయి.", footer_style))
    
    doc.build(story)
    print("✅ Comprehensive Telugu PDF created successfully")
    return True

def main():
    """Main function"""
    print("🔄 Creating Comprehensive DWCRA User Guide PDFs...")
    print("=" * 60)
    
    try:
        # Install BeautifulSoup if not available
        try:
            import bs4
        except ImportError:
            print("Installing BeautifulSoup...")
            os.system("pip install beautifulsoup4")
            import bs4
        
        # Create English PDF
        print("\n📖 Creating Comprehensive English User Guide PDF...")
        if create_english_pdf_from_html():
            print("✅ English PDF created with full content")
        else:
            print("❌ Failed to create English PDF")
        
        # Create Telugu PDF
        print("\n📖 Creating Comprehensive Telugu User Guide PDF...")
        if create_telugu_pdf_from_html():
            print("✅ Telugu PDF created with full content")
        else:
            print("❌ Failed to create Telugu PDF")
        
        print("\n🎉 PDF Creation Summary:")
        print("📁 PDF files are available in the static/ directory:")
        print("   • static/dwcra_user_guide_english.pdf")
        print("   • static/dwcra_user_guide_telugu.pdf")
        print("🔗 User guide buttons should now work properly!")
        print("📄 PDFs contain comprehensive content from HTML guides")
        
    except Exception as e:
        print(f"❌ Error creating PDFs: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    main() 