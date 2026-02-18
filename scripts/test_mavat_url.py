import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mavat_plan_extractor import extractor

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)

def test_url_extraction():
    url = "https://mavat.iplan.gov.il/SV4/1/6005341020/310"
    print(f"Testing extraction for URL: {url}")
    print("-" * 50)
    
    try:
        result = extractor.process_plan(url)
        
        print("\n--- RESULT ---")
        print(f"Status: {result.get('status')}")
        if result.get('error'):
            print(f"Error: {result.get('error')}")
            
        pdf_path = result.get('pdf_path')
        print(f"PDF Path: {pdf_path}")
        
        if pdf_path and os.path.exists(pdf_path):
            print(f"CONFIRMED: File exists at {pdf_path}")
            print(f"File size: {os.path.getsize(pdf_path)} bytes")
        
        extracted = result.get('extracted_data', {})
        print(f"\nKeywords Found: {extracted.get('keywords_found')}")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_url_extraction()
