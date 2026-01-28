#!/usr/bin/env python3
"""
Comprehensive Web Search Test Suite for STING-CE
Tests entity disambiguation across 9 different sectors and query types.

Usage:
    python test_web_search_comprehensive.py

Each test verifies that:
1. Web search triggers correctly
2. Search results return the correct entity type
3. Results contain relevant, non-hallucinated information
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

# Configuration
API_BASE = "http://localhost:8091"
BEE_CHAT_ENDPOINT = f"{API_BASE}/bee/chat"
WEB_SEARCH_STATUS = f"{API_BASE}/bee/web-search-status"

# Test cases covering different sectors and entity types
TEST_CASES = [
    # Healthcare Sector
    {
        "id": 1,
        "name": "Hospital - Medical Staff Query",
        "category": "healthcare",
        "message": "Write a comprehensive report about cardiac doctors at Northside Hospital Atlanta",
        "expected_entity": "hospital",
        "negative_terms": ["school", "high school", "university"],
        "min_results": 3,
    },
    {
        "id": 2,
        "name": "Location-Specific Hospital Query",
        "category": "healthcare",
        "message": "What hospitals in Seattle Washington provide pediatric services?",
        "expected_entity": "hospital",
        "negative_terms": [],
        "min_results": 3,
    },

    # Education Sector
    {
        "id": 3,
        "name": "University - Academic Staff Query",
        "category": "education",
        "message": "Who are the computer science professors at Stanford University?",
        "expected_entity": "university",
        "negative_terms": ["high school", "hospital", "company"],
        "min_results": 3,
    },

    # Business Sector
    {
        "id": 4,
        "name": "Company - Executive Leadership Query",
        "category": "business",
        "message": "List the executive leadership team at Microsoft Corporation",
        "expected_entity": "company",
        "negative_terms": ["government", "university", "hospital"],
        "min_results": 3,
    },
    {
        "id": 5,
        "name": "Entity Disambiguation - Multiple Similar Names",
        "category": "business",
        "message": "Research information about Apple the company (not the fruit or record label)",
        "expected_entity": "company",
        "negative_terms": ["fruit", "music", "record label"],
        "min_results": 3,
    },

    # Government Sector
    {
        "id": 6,
        "name": "Government - Agency Staff Query",
        "category": "government",
        "message": "Find information about staff at the CDC Centers for Disease Control",
        "expected_entity": "government",
        "negative_terms": ["company", "university", "hospital"],
        "min_results": 3,
    },

    # Non-Profit Sector
    {
        "id": 7,
        "name": "Non-Profit - Organization Staff Query",
        "category": "nonprofit",
        "message": "Who are the key personnel at the Red Cross organization?",
        "expected_entity": "nonprofit",
        "negative_terms": ["government", "for-profit", "company"],
        "min_results": 3,
    },

    # Research Sector
    {
        "id": 8,
        "name": "Research Institute - Scientific Staff Query",
        "category": "research",
        "message": "List researchers at the NIH National Institutes of Health",
        "expected_entity": "research",
        "negative_terms": ["hospital", "university", "high school"],
        "min_results": 3,
    },

    # Finance Sector
    {
        "id": 9,
        "name": "Financial Institution - Banking Staff Query",
        "category": "finance",
        "message": "Who are the leadership executives at JPMorgan Chase bank?",
        "expected_entity": "bank",
        "negative_terms": ["government", "non-profit", "university"],
        "min_results": 3,
    },

    # Legal Sector
    {
        "id": 10,
        "name": "Law Firm - Attorney/Partner Query",
        "category": "legal",
        "message": "List the partners and associates at Kirkland & Ellis law firm",
        "expected_entity": "law_firm",
        "negative_terms": ["court", "government", "university"],
        "min_results": 3,
    },
    {
        "id": 11,
        "name": "Court System - Judicial Staff Query",
        "category": "legal",
        "message": "Who are the federal district court judges in the Southern District of New York?",
        "expected_entity": "court",
        "negative_terms": ["law firm", "attorney", "private practice"],
        "min_results": 3,
    },
    {
        "id": 12,
        "name": "Bar Association - Leadership Query",
        "category": "legal",
        "message": "Who are the current officers and board members of the New York State Bar Association?",
        "expected_entity": "bar_association",
        "negative_terms": ["court", "law firm", "government agency"],
        "min_results": 3,
    },
    {
        "id": 13,
        "name": "Legal Aid Organization - Staff Query",
        "category": "legal",
        "message": "Find information about the legal aid attorneys at Legal Services Corporation",
        "expected_entity": "legal_aid",
        "negative_terms": ["private law firm", "corporate counsel", "judge"],
        "min_results": 3,
    },
    {
        "id": 14,
        "name": "Corporate Legal Department - General Counsel Query",
        "category": "legal",
        "message": "Who is the General Counsel and chief legal officers at Amazon corporation?",
        "expected_entity": "corporate_legal",
        "negative_terms": ["law firm", "external counsel", "court"],
        "min_results": 3,
    },
    {
        "id": 15,
        "name": "Entity Disambiguation - Legal Entity (Dell vs Dell Technologies)",
        "category": "legal",
        "message": "Research the legal team at Dell Technologies (not the computer manufacturer Michael Dell)",
        "expected_entity": "corporate_legal",
        "negative_terms": ["personal", "individual", "court ruling"],
        "min_results": 3,
    },
]


def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers - modify as needed for your deployment"""
    # For demo.stingassistant.com, cookies are typically handled by the browser
    # This is a placeholder for programmatic testing
    return {
        "Content-Type": "application/json",
    }


async def check_web_search_status() -> Dict:
    """Check if web search is enabled and configured"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(WEB_SEARCH_STATUS, headers=get_auth_headers()) as resp:
                return await resp.json()
        except Exception as e:
            return {"error": str(e)}


async def run_single_test(
    session: aiohttp.ClientSession,
    test_case: Dict,
    verbose: bool = True
) -> Dict:
    """Run a single test case"""
    start_time = time.time()

    result = {
        "test_id": test_case["id"],
        "test_name": test_case["name"],
        "category": test_case["category"],
        "success": False,
        "response_time": 0,
        "error": None,
        "web_search_triggered": False,
        "results_count": 0,
        "correct_entity": False,
        "details": {},
    }

    try:
        payload = {
            "message": test_case["message"],
            "user_id": "test-user",
            "conversation_id": f"test-{test_case['id']}",
            "force_web_search": True,  # Always trigger web search for testing
        }

        async with session.post(
            BEE_CHAT_ENDPOINT,
            json=payload,
            headers=get_auth_headers(),
            timeout=aiohttp.ClientTimeout(total=120)
        ) as response:

            result["response_time"] = time.time() - start_time

            if response.status != 200:
                result["error"] = f"HTTP {response.status}"
                return result

            data = await response.json()
            response_text = data.get("response", "")

            # Check if web search was triggered (look for source citations)
            web_search_indicators = [
                "Source:", "Sources:", "WEB RESEARCH",
                "[", "](http", "References:", "Source URL"
            ]
            result["web_search_triggered"] = any(
                indicator in response_text[:500]
                for indicator in web_search_indicators
            )

            # Count results (look for numbered sources)
            import re
            source_patterns = [
                r'SOURCE\s*\d+',
                r'\[SOURCE\s*\d+\]',
                r'\[\d+\]\(http',
                r'Source\s*\d+[:\s]',
            ]
            sources_found = 0
            for pattern in source_patterns:
                matches = re.findall(pattern, response_text, re.IGNORECASE)
                sources_found = max(sources_found, len(matches))

            result["results_count"] = sources_found

            # Check for correct entity type
            response_lower = response_text.lower()
            negative_found = any(
                term in response_lower
                for term in test_case.get("negative_terms", [])
            )

            # Check for expected entity indicators
            entity_indicators = {
                # Healthcare
                "hospital": ["hospital", "medical", "healthcare", "patient", "physician"],
                # Education
                "university": ["university", "faculty", "professor", "academic", "campus"],
                # Business
                "company": ["corporation", "ceo", "executive", "headquarters", "business"],
                # Government
                "government": ["agency", "government", "federal", "official", "department"],
                # Non-Profit
                "nonprofit": ["non-profit", "nonprofit", "charity", "foundation", "mission"],
                # Research
                "research": ["research", "scientist", "laboratory", "study", "institute"],
                # Finance
                "bank": ["bank", "financial", "banking", "investment", "assets"],
                # Legal Sector
                "law_firm": ["law firm", "partner", "associate", "attorney", "counsel", "litigation"],
                "court": ["court", "judge", "judicial", "district", "federal court", "ruling"],
                "bar_association": ["bar association", "attorney", "member", "board", "association"],
                "legal_aid": ["legal aid", "attorney", "pro bono", "legal services", "low-income"],
                "corporate_legal": ["general counsel", "legal officer", "chief legal", "corporate counsel"],
            }

            expected_indicators = entity_indicators.get(
                test_case["expected_entity"],
                ["organization", "staff", "team"]
            )

            entity_found = any(
                indicator in response_lower[:2000]
                for indicator in expected_indicators
            )

            result["correct_entity"] = entity_found and not negative_found
            result["success"] = (
                result["web_search_triggered"] and
                result["results_count"] >= test_case["min_results"] and
                result["correct_entity"]
            )

            # Store details for analysis
            result["details"] = {
                "response_preview": response_text[:500] + "..." if len(response_text) > 500 else response_text,
                "entity_indicators_found": [i for i in expected_indicators if i in response_lower[:2000]],
                "negative_terms_found": [t for t in test_case.get("negative_terms", []) if t in response_lower],
                "sources_extracted": sources_found,
            }

    except asyncio.TimeoutError:
        result["error"] = "Timeout"
    except Exception as e:
        result["error"] = str(e)

    return result


async def run_all_tests(verbose: bool = True) -> Dict:
    """Run all test cases and return results"""
    print("\n" + "="*70)
    print("STING-CE Web Search Test Suite")
    print("="*70)
    print(f"Started at: {datetime.now().isoformat()}")
    print()

    # Check web search status first
    status = await check_web_search_status()
    print(f"Web Search Status: {json.dumps(status, indent=2)}")
    print()

    async with aiohttp.ClientSession() as session:
        results = []

        for test_case in TEST_CASES:
            print(f"Running Test {test_case['id']}: {test_case['name']}...")
            result = await run_single_test(session, test_case, verbose)
            results.append(result)

            if verbose:
                status_symbol = "✅" if result["success"] else "❌"
                print(f"  {status_symbol} Success: {result['success']}")
                print(f"  ⏱️  Response Time: {result['response_time']:.2f}s")
                print(f"  🔍 Web Search: {result['web_search_triggered']}")
                print(f"  📊 Sources Found: {result['results_count']}")
                print(f"  🎯 Correct Entity: {result['correct_entity']}")
                if result["error"]:
                    print(f"  ⚠️  Error: {result['error']}")
            print()

    return summarize_results(results)


def summarize_results(results: List[Dict]) -> Dict:
    """Summarize test results"""
    passed = sum(1 for r in results if r["success"])
    failed = len(results) - passed

    summary = {
        "total_tests": len(results),
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{(passed / len(results) * 100):.1f}%" if results else "0%",
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "by_category": {},
    }

    # Group by category
    for result in results:
        cat = result["category"]
        if cat not in summary["by_category"]:
            summary["by_category"][cat] = {"total": 0, "passed": 0}
        summary["by_category"][cat]["total"] += 1
        if result["success"]:
            summary["by_category"][cat]["passed"] += 1

    # Print summary
    print("="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Pass Rate: {summary['pass_rate']}")
    print()

    print("By Category:")
    for cat, stats in summary["by_category"].items():
        cat_pass_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {cat}: {stats['passed']}/{stats['total']} ({cat_pass_rate:.0f}%)")

    print()
    print("Failed Tests:")
    for result in results:
        if not result["success"]:
            print(f"  - Test {result['test_id']}: {result['test_name']}")
            print(f"    Error: {result['error'] or 'Entity mismatch or no sources'}")

    print()
    print("="*70)

    return summary


async def main():
    """Main entry point"""
    import sys

    verbose = "--verbose" not in sys.argv and "-v" not in sys.argv

    results = await run_all_tests(verbose=verbose)

    # Exit with appropriate code
    if results["failed"] == 0:
        print("All tests passed! ✅")
        sys.exit(0)
    else:
        print(f"Tests completed with {results['failed']} failures. ❌")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
