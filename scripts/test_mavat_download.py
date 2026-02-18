import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mavat_client import MavatClient

def test_download():
    print("Testing MavatClient...")
    client = MavatClient(output_dir=os.path.join("tmp", "mavat_plans"))
    # Use the example plan from the docstring
    plan_number = "102-0909267" 
    print(f"Downloading plan {plan_number}...")
    result = client.download_horaot(plan_number)
    print("Result:", result)

if __name__ == "__main__":
    test_download()
