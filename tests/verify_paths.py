"""
Quick script to verify the output path structure
"""
from pathlib import Path
from datetime import datetime

# Test parameters
symbol = "NVDA"
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Create the path
output_dir = Path("analysis_results") / symbol
output_file = output_dir / f"{symbol}_{timestamp}.md"

print("Path Verification")
print("=" * 60)
print(f"Symbol: {symbol}")
print(f"Timestamp: {timestamp}")
print(f"Output Directory: {output_dir}")
print(f"Output File: {output_file}")
print()
print("Full structure will be:")
print(f"  analysis_results/")
print(f"    └── {symbol}/")
print(f"        └── {symbol}_{timestamp}.md")
print("=" * 60)

# Test with multiple symbols
print("\nExample with multiple symbols:")
for symbol in ["NVDA", "AAPL", "MSFT"]:
    output_dir = Path("analysis_results") / symbol
    output_file = output_dir / f"{symbol}_{timestamp}.md"
    print(f"  {output_file}")
