import sys
import os
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mavat_plan_extractor import extractor

def test_extractor():
    plan_number = "102-0909267"
    print(f"Testing extraction for plan: {plan_number}")
    print("-" * 50)
    
    try:
        result = extractor.process_plan(plan_number)
        
        print("\n--- RESULT ---")
        print(f"Status: {result.get('status')}")
        if result.get('error'):
            print(f"Error: {result.get('error')}")
            
        print(f"PDF Path: {result.get('pdf_path')}")
        
        extracted = result.get('extracted_data', {})
        print(f"\nKeywords Found: {extracted.get('keywords_found')}")
        
        print("\nText Preview (first 200 chars):")
        print(extracted.get('text_preview', '')[:200])
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_extractor()
