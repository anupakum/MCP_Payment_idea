"""Test case query fix for UUID pattern matching."""

import re

def test_case_id_extraction():
    """Test that case ID extraction works with UUID format."""
    
    # Test case 1: Case status query with UUID
    request1 = "case status 8492cbd8-2ce4-4813-88c3-bc29f28933a4"
    request_lower1 = request1.lower()
    
    # Old pattern (broken)
    old_pattern = r'(case|dsp)[_\-]?[\w\d]+'
    old_match = re.search(old_pattern, request_lower1)
    print(f"Test 1 - Case Status Query")
    print(f"  Request: {request1}")
    print(f"  Old pattern match: {old_match.group(0) if old_match else 'None'}")
    
    # New pattern (fixed)
    new_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    new_match = re.search(new_pattern, request_lower1)
    case_id = new_match.group(0) if new_match else None
    print(f"  New pattern match: {case_id}")
    print(f"  ✓ FIXED!" if case_id else "  ✗ FAILED")
    print()
    
    # Test case 2: My cases query
    request2 = "my cases CUST001"
    request_lower2 = request2.lower()
    
    customer_match = re.search(r'cust\d+', request_lower2)
    customer_id = customer_match.group(0).upper() if customer_match else None
    
    has_my_cases = 'my cases' in request_lower2 or 'customer cases' in request_lower2
    
    print(f"Test 2 - My Cases Query")
    print(f"  Request: {request2}")
    print(f"  Customer ID extracted: {customer_id}")
    print(f"  Has 'my cases': {has_my_cases}")
    print(f"  Will route to get_customer_cases: {has_my_cases and customer_id is not None}")
    print(f"  ✓ WORKING!" if (has_my_cases and customer_id) else "  ✗ FAILED")
    print()
    
    # Test case 3: Multiple UUID formats
    test_uuids = [
        "8492cbd8-2ce4-4813-88c3-bc29f28933a4",
        "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "00000000-0000-0000-0000-000000000000"
    ]
    
    print(f"Test 3 - Multiple UUID Formats")
    for uuid in test_uuids:
        match = re.search(new_pattern, uuid.lower())
        result = "✓" if match else "✗"
        print(f"  {result} {uuid}: {match.group(0) if match else 'No match'}")
    

if __name__ == "__main__":
    test_case_id_extraction()
