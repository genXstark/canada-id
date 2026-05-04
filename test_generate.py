"""
Test script for Canada ID Generator
Tests all document generation functions with sample data.
"""

import os
from id_generator import (
    generate_ontario_dl,
    generate_quebec_dl,
    generate_passport,
    generate_pr_card,
    OUTPUT_DIR,
)
from PIL import Image

# Create test photo if needed
def create_test_photo():
    """Create a placeholder test photo."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    test_photo = os.path.join(OUTPUT_DIR, "test_photo.png")
    
    if not os.path.exists(test_photo):
        photo_img = Image.new("RGB", (300, 400), color="#C0C0C0")
        from PIL import ImageDraw
        draw = ImageDraw.Draw(photo_img)
        draw.rectangle([(50, 50), (250, 350)], outline="#808080", width=2)
        draw.text((100, 180), "PHOTO", fill="#808080")
        photo_img.save(test_photo)
        print(f"Created test photo: {test_photo}")
    
    return test_photo


# Sample data
sample_data = {
    "photo": create_test_photo(),
    "surname": "SMITH",
    "given_names": "JOHN ALEXANDER",
    "dob": "1995-05-23",
    "sex": "M",
    "height": "175",
    "eyes": "BRO",
    "hair": "BRO",
    "address": "123 Main Street",
    "city": "Toronto",
    "province": "ON",
    "postal_code": "M5H 2N2",
    "license_number": "S1234-56789-01234",
    "issue_date": "2024-01-15",
    "expiry_date": "2029-05-23",
    "passport_number": "AB123456",
    "pr_number": "1234567890",
    "place_of_birth": "Toronto",
}


def test_ontario_dl():
    """Test Ontario driver's license generation."""
    print("\n" + "=" * 50)
    print("TEST: Ontario Driver's License")
    print("=" * 50)
    
    front, back = generate_ontario_dl(sample_data)
    assert os.path.exists(front), "Front image not created"
    assert os.path.exists(back), "Back image not created"
    print(f"✅ PASSED")
    print(f"   Front: {front}")
    print(f"   Back: {back}")


def test_quebec_dl():
    """Test Quebec driver's license generation."""
    print("\n" + "=" * 50)
    print("TEST: Quebec Driver's License")
    print("=" * 50)
    
    qc_data = sample_data.copy()
    qc_data["province"] = "QC"
    qc_data["license_number"] = "D1234-567890-12"
    
    front, back = generate_quebec_dl(qc_data)
    assert os.path.exists(front), "Front image not created"
    assert os.path.exists(back), "Back image not created"
    print(f"✅ PASSED")
    print(f"   Front: {front}")
    print(f"   Back: {back}")


def test_passport():
    """Test passport generation."""
    print("\n" + "=" * 50)
    print("TEST: Canadian Passport")
    print("=" * 50)
    
    path = generate_passport(sample_data)
    assert os.path.exists(path), "Passport image not created"
    print(f"✅ PASSED")
    print(f"   Path: {path}")


def test_pr_card():
    """Test PR card generation."""
    print("\n" + "=" * 50)
    print("TEST: Permanent Resident Card")
    print("=" * 50)
    
    front, back = generate_pr_card(sample_data)
    assert os.path.exists(front), "Front image not created"
    assert os.path.exists(back), "Back image not created"
    print(f"✅ PASSED")
    print(f"   Front: {front}")
    print(f"   Back: {back}")


def run_all_tests():
    """Run all document generation tests."""
    print("\n" + "#" * 60)
    print("# CANADA ID GENERATOR - TEST SUITE")
    print("#" * 60)
    
    # Setup test photo
    sample_data["photo"] = create_test_photo()
    
    results = {}
    
    tests = {
        "Ontario DL": test_ontario_dl,
        "Quebec DL": test_quebec_dl,
        "Passport": test_passport,
        "PR Card": test_pr_card,
    }
    
    for name, test_func in tests.items():
        try:
            test_func()
            results[name] = True
        except Exception as e:
            print(f"❌ FAILED: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print(f"Output directory: {os.path.abspath(OUTPUT_DIR)}")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
