#!/usr/bin/env python3
"""
Download and process all PDFs from the Hugging Face dataset.
This script downloads PDFs from the text_data folder and extracts structured data.

Requirements:
    pip install datasets pdfplumber huggingface_hub requests

Usage:
    python download_all_pdfs.py
"""

import json
import os
import sys
from pathlib import Path
import re

try:
    from huggingface_hub import HfApi, hf_hub_download
    from datasets import load_dataset
except ImportError:
    print("❌ Error: Required libraries not found")
    print("   Install with: pip install datasets huggingface_hub pdfplumber requests")
    sys.exit(1)

try:
    import pdfplumber
except ImportError:
    print("⚠️  Warning: 'pdfplumber' not found")
    print("   Install with: pip install pdfplumber")
    pdfplumber = None

def parse_pdf_text(pdf_text):
    """Parse PDF text to extract structured scheme information"""
    if not pdf_text or not isinstance(pdf_text, str):
        return {}
    
    scheme_data = {
        'schemeName': '',
        'schemeShortTitle': '',
        'detailedDescription_md': '',
        'eligibilityDescription_md': '',
        'benefits': [],
        'documents_required': [],
        'applicationProcess': [],
        'faqs': [],
        'state': '',
        'level': '',
        'nodalMinistryName': '',
        'tags': [],
        'schemeCategory': []
    }
    
    text = pdf_text.strip()
    
    # Extract scheme name (usually at the beginning, before common UI elements)
    lines = text.split('\n')
    scheme_name = None
    
    # Look for scheme name in first 30 lines, skip UI elements
    skip_patterns = ['sign in', 'sign out', 'cancel', 'apply now', 'check eligibility', 
                     'english', 'hindi', 'feedback', 'something went wrong']
    
    for i, line in enumerate(lines[:30]):
        line_clean = line.strip()
        if not line_clean or len(line_clean) < 10:
            continue
        
        # Skip UI elements
        if any(pattern in line_clean.lower() for pattern in skip_patterns):
            continue
        
        # Check if it looks like a scheme name
        if (len(line_clean) > 15 and len(line_clean) < 200 and 
            any(keyword in line_clean.lower() for keyword in ['scheme', 'yojana', 'program', 'initiative', 'subsidy', 'grant'])):
            scheme_name = line_clean
            break
    
    if scheme_name:
        scheme_data['schemeName'] = scheme_name
        # Create short title from name
        words = re.findall(r'\b\w+', scheme_name)
        if len(words) > 0:
            scheme_data['schemeShortTitle'] = ''.join([w[0].upper() for w in words[:5] if w[0].isalnum()])
    
    # Extract sections using common headers
    sections = {
        'introduction': 'detailedDescription_md',
        'details': 'detailedDescription_md',
        'objective': 'detailedDescription_md',
        'eligibility': 'eligibilityDescription_md',
        'benefits': 'benefits',
        'documents required': 'documents_required',
        'application process': 'applicationProcess',
        'frequently asked questions': 'faqs',
        'faq': 'faqs',
        'exclusions': 'eligibilityDescription_md'
    }
    
    current_section = None
    current_content = []
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_content:
                current_content.append('')
            continue
        
        # Check if this line is a section header
        is_header = False
        line_lower = line.lower()
        
        for header, field in sections.items():
            if header in line_lower and len(line) < 150 and not line_lower.startswith('http'):
                # Save previous section
                if current_section and current_content:
                    content_text = '\n'.join(current_content).strip()
                    if content_text:
                        if current_section == 'benefits':
                            # Try to split into individual benefits
                            benefits = re.split(r'\n[•\-\*]\s*|\n\d+[\.\)]\s*', content_text)
                            benefits = [b.strip() for b in benefits if b.strip() and len(b) > 10]
                            scheme_data['benefits'] = [
                                {'title': b.split(':')[0] if ':' in b else b[:50], 
                                 'description': b} 
                                for b in benefits[:15]
                            ]
                        elif current_section == 'documents_required':
                            # Try to split into individual documents
                            docs = [d.strip() for d in content_text.split('\n') 
                                   if d.strip() and len(d) > 5 and not d.lower().startswith('http')]
                            scheme_data['documents_required'] = [
                                {'document': d.split(':')[0] if ':' in d else d, 
                                 'description': d.split(':', 1)[1] if ':' in d else ''} 
                                for d in docs[:25]
                            ]
                        elif current_section == 'applicationProcess':
                            steps = [s.strip() for s in content_text.split('\n') 
                                    if s.strip() and len(s) > 10 and not s.lower().startswith('http')]
                            scheme_data['applicationProcess'] = [
                                {'mode': 'Online', 'process': steps[:30]}
                            ]
                        elif current_section == 'faqs':
                            # Try to extract Q&A pairs
                            qa_pairs = []
                            # Split by question marks
                            parts = re.split(r'([A-Z][^?]*\?)', content_text)
                            for i in range(1, len(parts), 2):
                                if i + 1 < len(parts):
                                    q = parts[i].strip()
                                    a = parts[i + 1].strip().split('\n')[0][:500]
                                    if len(q) > 10 and len(a) > 10:
                                        qa_pairs.append({'question': q, 'answer': a})
                            scheme_data['faqs'] = qa_pairs[:25]
                        else:
                            # For description fields, clean up the text
                            cleaned = re.sub(r'\s+', ' ', content_text)
                            scheme_data[current_section] = cleaned[:5000]
                
                # Start new section
                current_section = field
                current_content = []
                is_header = True
                break
        
        if not is_header and current_section:
            # Skip UI elements and URLs
            if not any(skip in line.lower() for skip in skip_patterns + ['http', 'www.', '.com']):
                current_content.append(line)
    
    # Save last section
    if current_section and current_content:
        content_text = '\n'.join(current_content).strip()
        if content_text:
            if current_section == 'benefits':
                benefits = re.split(r'\n[•\-\*]\s*|\n\d+[\.\)]\s*', content_text)
                benefits = [b.strip() for b in benefits if b.strip() and len(b) > 10]
                scheme_data['benefits'] = [
                    {'title': b.split(':')[0] if ':' in b else b[:50], 
                     'description': b} 
                    for b in benefits[:15]
                ]
            elif current_section == 'documents_required':
                docs = [d.strip() for d in content_text.split('\n') 
                       if d.strip() and len(d) > 5 and not d.lower().startswith('http')]
                scheme_data['documents_required'] = [
                    {'document': d.split(':')[0] if ':' in d else d, 
                     'description': d.split(':', 1)[1] if ':' in d else ''} 
                    for d in docs[:25]
                ]
            elif current_section == 'applicationProcess':
                steps = [s.strip() for s in content_text.split('\n') 
                        if s.strip() and len(s) > 10 and not s.lower().startswith('http')]
                scheme_data['applicationProcess'] = [
                    {'mode': 'Online', 'process': steps[:30]}
                ]
            elif current_section == 'faqs':
                qa_pairs = []
                parts = re.split(r'([A-Z][^?]*\?)', content_text)
                for i in range(1, len(parts), 2):
                    if i + 1 < len(parts):
                        q = parts[i].strip()
                        a = parts[i + 1].strip().split('\n')[0][:500]
                        if len(q) > 10 and len(a) > 10:
                            qa_pairs.append({'question': q, 'answer': a})
                scheme_data['faqs'] = qa_pairs[:25]
            else:
                cleaned = re.sub(r'\s+', ' ', content_text)
                scheme_data[current_section] = cleaned[:5000]
    
    # Extract state/level from text
    text_lower = text.lower()
    states = ['andhra pradesh', 'assam', 'bihar', 'gujarat', 'haryana', 'karnataka', 
              'kerala', 'maharashtra', 'odisha', 'punjab', 'rajasthan', 'tamil nadu',
              'telangana', 'uttar pradesh', 'west bengal', 'lakshadweep', 'delhi',
              'goa', 'himachal pradesh', 'jammu and kashmir', 'jharkhand', 'madhya pradesh',
              'manipur', 'meghalaya', 'mizoram', 'nagaland', 'sikkim', 'tripura',
              'uttarakhand', 'arunachal pradesh', 'chhattisgarh']
    
    for state in states:
        if state in text_lower:
            scheme_data['state'] = state.title()
            break
    
    if 'union territory' in text_lower or 'ut' in text_lower:
        scheme_data['level'] = 'State/ UT'
    elif 'central' in text_lower or 'government of india' in text_lower or 'ministry' in text_lower:
        scheme_data['level'] = 'Central'
    elif scheme_data['state']:
        scheme_data['level'] = 'State'
    
    # Extract ministry/department
    ministry_patterns = [
        r'ministry of [^\.\n]+',
        r'department of [^\.\n]+',
        r'govt\.? of [^\.\n]+'
    ]
    
    for pattern in ministry_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            scheme_data['nodalMinistryName'] = match.group(0).strip()
            break
    
    # If no structured data extracted, use raw text as description
    if not scheme_data['detailedDescription_md']:
        # Get first substantial paragraph
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 100]
        if paragraphs:
            scheme_data['detailedDescription_md'] = paragraphs[0][:2000]
        else:
            scheme_data['detailedDescription_md'] = text[:2000]
    
    # Extract tags from scheme name and description
    keywords = ['subsidy', 'grant', 'loan', 'scholarship', 'pension', 'housing', 
                'education', 'health', 'employment', 'agriculture', 'business', 
                'women', 'youth', 'senior', 'farmer', 'entrepreneur']
    found_tags = [kw for kw in keywords if kw in text_lower]
    scheme_data['tags'] = found_tags[:10]
    
    return scheme_data

def download_and_process_pdfs():
    """Download all PDFs from Hugging Face and process them"""
    
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / 'data'
    output_file = data_dir / 'schemes_data.json'
    pdf_dir = data_dir / 'pdfs'
    
    print("📥 Downloading PDFs from Hugging Face dataset...")
    print("   Dataset: shrijayan/gov_myscheme")
    print("   Folder: text_data\n")
    
    if pdfplumber is None:
        print("❌ pdfplumber is required. Install with: pip install pdfplumber")
        return False
    
    # Create directories
    data_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Initialize Hugging Face API
        api = HfApi()
        
        # List all files in the text_data folder
        print("📋 Listing files in text_data folder...")
        repo_files = api.list_repo_files("shrijayan/gov_myscheme", repo_type="dataset")
        
        # Filter PDF files
        pdf_files = [f for f in repo_files if f.endswith('.pdf') and 'text_data' in f]
        
        print(f"   Found {len(pdf_files)} PDF files\n")
        
        if len(pdf_files) == 0:
            print("⚠️  No PDF files found. Trying alternative method...")
            # Try loading dataset directly
            dataset = load_dataset('shrijayan/gov_myscheme', split='train')
            print(f"   Dataset has {len(dataset)} items")
            pdf_files = list(range(len(dataset)))
        
        schemes = []
        processed = 0
        failed = 0
        
        for i, pdf_file in enumerate(pdf_files):
            try:
                print(f"   Processing {i+1}/{len(pdf_files)}: {pdf_file if isinstance(pdf_file, str) else f'Item {pdf_file}'}...", end=' ')
                
                pdf_text = ""
                
                if isinstance(pdf_file, str):
                    # Download PDF file
                    pdf_path = hf_hub_download(
                        repo_id="shrijayan/gov_myscheme",
                        filename=pdf_file,
                        repo_type="dataset",
                        local_dir=str(pdf_dir)
                    )
                    
                    # Extract text from PDF
                    with pdfplumber.open(pdf_path) as pdf:
                        pdf_text = '\n'.join([page.extract_text() or '' for page in pdf.pages])
                else:
                    # Try to get from dataset
                    dataset = load_dataset('shrijayan/gov_myscheme', split='train')
                    item = dataset[pdf_file]
                    if 'pdf' in item:
                        pdf_obj = item['pdf']
                        if hasattr(pdf_obj, 'extract_text'):
                            pdf_text = pdf_obj.extract_text()
                        elif isinstance(pdf_obj, str):
                            pdf_text = pdf_obj
                
                if not pdf_text or len(pdf_text) < 50:
                    print("⚠️  No text extracted")
                    failed += 1
                    continue
                
                # Parse the PDF text
                scheme_data = parse_pdf_text(pdf_text)
                
                # Ensure required fields
                if not scheme_data.get('schemeName'):
                    scheme_data['schemeName'] = f"Scheme {i+1}"
                if not scheme_data.get('schemeShortTitle'):
                    scheme_data['schemeShortTitle'] = f"SCH{i+1:04d}"
                
                schemes.append(scheme_data)
                processed += 1
                print("✅")
                
                # Save progress every 10 files
                if (i + 1) % 10 == 0:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(schemes, f, ensure_ascii=False, indent=2)
                    print(f"   💾 Progress saved: {processed} schemes processed")
                
            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}")
                failed += 1
                continue
        
        # Save final results
        print(f"\n💾 Saving {len(schemes)} schemes to {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(schemes, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Complete!")
        print(f"   - Processed: {processed}")
        print(f"   - Failed: {failed}")
        print(f"   - Total schemes: {len(schemes)}")
        print(f"\n   Now run: npm run seed")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    download_and_process_pdfs()

