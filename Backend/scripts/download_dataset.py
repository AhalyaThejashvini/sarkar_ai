#!/usr/bin/env python3
"""
Helper script to download the gov_myscheme dataset from Hugging Face
and save it as JSON for the Node.js seed script.

Requirements:
    pip install datasets pdfplumber

Usage:
    python download_dataset.py
"""

import json
import os
import sys
from pathlib import Path

try:
    from datasets import load_dataset
except ImportError:
    print("❌ Error: 'datasets' library not found")
    print("   Install it with: pip install datasets")
    sys.exit(1)

try:
    import pdfplumber
except ImportError:
    print("⚠️  Warning: 'pdfplumber' not found")
    print("   The dataset contains PDF files. Installing pdfplumber...")
    print("   Run: pip install pdfplumber")
    print("   Or the script will try to install it automatically")
    pdfplumber = None

def install_pdfplumber():
    """Try to install pdfplumber if not available"""
    import subprocess
    try:
        print("   Installing pdfplumber...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber", "-q"])
        import pdfplumber
        return pdfplumber
    except Exception as e:
        print(f"   ⚠️  Could not install pdfplumber: {e}")
        return None

def download_dataset():
    """Download the dataset from Hugging Face and save as JSON"""
    
    # Get the script directory
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / 'data'
    output_file = data_dir / 'schemes_data.json'
    
    print("📥 Downloading dataset from Hugging Face...")
    print(f"   Dataset: shrijayan/gov_myscheme")
    
    # Check if pdfplumber is needed and install if missing
    global pdfplumber
    if pdfplumber is None:
        pdfplumber = install_pdfplumber()
        if pdfplumber is None:
            print("\n❌ pdfplumber is required but could not be installed.")
            print("   Please install manually: pip install pdfplumber")
            print("\n   Or try downloading the data manually from:")
            print("   https://huggingface.co/datasets/shrijayan/gov_myscheme/tree/main/text_data")
            return False
    
    try:
        # Load the dataset
        print("   Loading dataset...")
        print("   (This may take a moment as it processes PDF files...)")
        dataset = load_dataset('shrijayan/gov_myscheme', split='train')
        
        # Convert to list of dictionaries and extract PDF content
        print("   Converting to JSON format...")
        print("   Extracting and parsing text from PDFs...")
        data = []
        
        # First, let's check the structure of the first item
        if len(dataset) > 0:
            first_item = dataset[0]
            print(f"   Dataset structure: {list(first_item.keys())}")
        
        def parse_pdf_text(pdf_text):
            """Parse PDF text to extract structured scheme information"""
            if not pdf_text or not isinstance(pdf_text, str):
                return {}
            
            scheme_data = {
                'pdf_text': pdf_text,  # Keep raw text for reference
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
            
            # Extract scheme name (usually at the beginning)
            # Look for patterns like "25% Capital Investment Subsidy Scheme"
            name_match = None
            lines = text.split('\n')
            for i, line in enumerate(lines[:20]):  # Check first 20 lines
                line = line.strip()
                if len(line) > 10 and len(line) < 200:
                    # Likely a scheme name
                    if any(keyword in line.lower() for keyword in ['scheme', 'yojana', 'program', 'initiative']):
                        name_match = line
                        break
            
            if name_match:
                scheme_data['schemeName'] = name_match
                # Create short title from name
                words = name_match.split()
                if len(words) > 0:
                    scheme_data['schemeShortTitle'] = ''.join([w[0].upper() for w in words[:5]])
            
            # Extract sections using common headers
            sections = {
                'Introduction': 'detailedDescription_md',
                'Details': 'detailedDescription_md',
                'Objective': 'detailedDescription_md',
                'Eligibility': 'eligibilityDescription_md',
                'Benefits': 'benefits',
                'Documents Required': 'documents_required',
                'Application Process': 'applicationProcess',
                'Frequently Asked Questions': 'faqs',
                'FAQ': 'faqs'
            }
            
            current_section = None
            current_content = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this line is a section header
                is_header = False
                for header, field in sections.items():
                    if header.lower() in line.lower() and len(line) < 100:
                        # Save previous section
                        if current_section and current_content:
                            content_text = '\n'.join(current_content)
                            if current_section == 'benefits':
                                # Try to split into individual benefits
                                benefits = [b.strip() for b in content_text.split('\n•') if b.strip()]
                                scheme_data['benefits'] = [{'title': b.split(':')[0] if ':' in b else b, 'description': b} for b in benefits[:10]]
                            elif current_section == 'documents_required':
                                # Try to split into individual documents
                                docs = [d.strip() for d in content_text.split('\n') if d.strip() and len(d) > 5]
                                scheme_data['documents_required'] = [{'document': d, 'description': ''} for d in docs[:20]]
                            elif current_section == 'applicationProcess':
                                steps = [s.strip() for s in content_text.split('\n') if s.strip() and len(s) > 5]
                                scheme_data['applicationProcess'] = [{'mode': 'Online', 'process': steps[:20]}]
                            elif current_section == 'faqs':
                                # Try to extract Q&A pairs
                                qa_pairs = []
                                parts = content_text.split('?')
                                for i in range(len(parts) - 1):
                                    q = parts[i].split('\n')[-1] + '?'
                                    a = parts[i + 1].split('\n')[0] if parts[i + 1] else ''
                                    if len(q) > 5 and len(a) > 5:
                                        qa_pairs.append({'question': q.strip(), 'answer': a.strip()})
                                scheme_data['faqs'] = qa_pairs[:20]
                            else:
                                scheme_data[current_section] = content_text
                        
                        # Start new section
                        current_section = field
                        current_content = []
                        is_header = True
                        break
                
                if not is_header and current_section:
                    current_content.append(line)
            
            # Save last section
            if current_section and current_content:
                content_text = '\n'.join(current_content)
                if current_section == 'benefits':
                    benefits = [b.strip() for b in content_text.split('\n•') if b.strip()]
                    scheme_data['benefits'] = [{'title': b.split(':')[0] if ':' in b else b, 'description': b} for b in benefits[:10]]
                elif current_section == 'documents_required':
                    docs = [d.strip() for d in content_text.split('\n') if d.strip() and len(d) > 5]
                    scheme_data['documents_required'] = [{'document': d, 'description': ''} for d in docs[:20]]
                elif current_section == 'applicationProcess':
                    steps = [s.strip() for s in content_text.split('\n') if s.strip() and len(s) > 5]
                    scheme_data['applicationProcess'] = [{'mode': 'Online', 'process': steps[:20]}]
                elif current_section == 'faqs':
                    qa_pairs = []
                    parts = content_text.split('?')
                    for i in range(len(parts) - 1):
                        q = parts[i].split('\n')[-1] + '?'
                        a = parts[i + 1].split('\n')[0] if parts[i + 1] else ''
                        if len(q) > 5 and len(a) > 5:
                            qa_pairs.append({'question': q.strip(), 'answer': a.strip()})
                    scheme_data['faqs'] = qa_pairs[:20]
                else:
                    scheme_data[current_section] = content_text
            
            # Extract state/level from text
            if 'lakshadweep' in text.lower() or 'union territory' in text.lower():
                scheme_data['state'] = 'Lakshadweep'
                scheme_data['level'] = 'State'
            elif 'central' in text.lower() or 'government of india' in text.lower():
                scheme_data['level'] = 'Central'
            
            # Extract ministry/department
            if 'department' in text.lower():
                dept_match = None
                for line in lines[:50]:
                    if 'department' in line.lower():
                        dept_match = line.strip()
                        break
                if dept_match:
                    scheme_data['nodalMinistryName'] = dept_match
            
            # If no structured data extracted, use raw text as description
            if not scheme_data['detailedDescription_md']:
                scheme_data['detailedDescription_md'] = text[:2000]  # First 2000 chars
            
            return scheme_data
        
        for i, item in enumerate(dataset):
            try:
                # Extract PDF text
                pdf_text = ""
                for key, value in item.items():
                    if hasattr(value, 'extract_text'):
                        try:
                            pdf_text = value.extract_text()
                            break
                        except:
                            pass
                    elif isinstance(value, str) and len(value) > 100:
                        pdf_text = value
                        break
                
                if not pdf_text:
                    print(f"   ⚠️  No text extracted from item {i}")
                    continue
                
                # Parse the PDF text into structured data
                scheme_dict = parse_pdf_text(pdf_text)
                
                # Ensure required fields
                if not scheme_dict.get('schemeName'):
                    scheme_dict['schemeName'] = f"Scheme {i+1}"
                if not scheme_dict.get('schemeShortTitle'):
                    scheme_dict['schemeShortTitle'] = f"SCH{i+1}"
                
                data.append(scheme_dict)
                
                if (i + 1) % 10 == 0 or (i + 1) == len(dataset):
                    print(f"   Processed: {i + 1}/{len(dataset)}")
            except Exception as e:
                print(f"   ⚠️  Error processing item {i}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"   ✅ Downloaded and processed {len(data)} schemes")
        
        # Create data directory if it doesn't exist
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to JSON file
        print(f"   Saving to {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Dataset saved successfully!")
        print(f"   File: {output_file}")
        print(f"   Total schemes: {len(data)}")
        print(f"\n   Now you can run: npm run seed")
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error downloading dataset: {error_msg}")
        
        if "pdfplumber" in error_msg.lower():
            print("\n💡 Solution:")
            print("   The dataset contains PDF files. Install pdfplumber:")
            print("   pip install pdfplumber")
            print("\n   Then run this script again.")
        elif "JSON serializable" in error_msg or "PDF" in error_msg:
            print("\n💡 Note:")
            print("   The dataset contains PDF objects. The script should extract")
            print("   text from them automatically. If this error persists,")
            print("   the dataset structure may be different than expected.")
            print("\n   Try checking the dataset structure or use manual download.")
        else:
            print("\nAlternative methods:")
            print("1. Install pdfplumber: pip install pdfplumber")
            print("2. Visit: https://huggingface.co/datasets/shrijayan/gov_myscheme")
            print("3. Check the 'text_data' folder for JSON/CSV files")
            print("4. Download manually and place in Backend/data/schemes_data.json")
        
        return False

if __name__ == "__main__":
    download_dataset()

