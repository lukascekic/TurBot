#!/usr/bin/env python3
"""
TurBot Token Consumption Test
============================

Runs 20 diverse tourism queries and tracks total token consumption
for accurate cost analysis and budget planning.

Usage: python test_token_consumption.py
"""

import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Any
import uuid
import requests

# Test Configuration
BASE_URL = "http://localhost:8000"
SESSION_ID = f"token_test_{uuid.uuid4().hex[:8]}"

# 20 Diverse Tourism Queries - Mix of simple and complex
TEST_QUERIES = [
    # Basic destination queries (Standard response - 400 chars/chunk)
    "Tražim hotel u Rimu",
    "Ima li nešto za Amsterdam?", 
    "Šta imate za Istanbul?",
    "Ponuda za Grčku",
    "Letovanje u Turskoj",
    
    # Detailed queries (Full chunk response - no limit)
    "Koliko košta putovanje u Amsterdam i koji je program?",
    "Detaljni opis aranžmana za Rim sa cenama",
    "Kada su datumi polaska za Istanbul i šta je uključeno?",
    "Potreban mi je cenovnik za Grčku sa svim troškovima",
    "Program putovanja za Maroko - detaljno objašnjenje",
    
    # Context-aware follow-up queries
    "Koliko košta?",
    "Ima li spa?",
    "A parking?",
    "Šta je sa doručkom?",
    "Možete li mi reći više?",
    
    # Budget and preference queries
    "Budžet mi je 500 EUR",
    "Za četvoročlanu porodicu",
    "All inclusive opcije",
    "Luksuzni hoteli",
    "Romantična putovanja za dvoje"
]

class TokenConsumptionTracker:
    """Tracks token usage and costs across multiple queries"""
    
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.query_results = []
        self.start_time = None
        self.end_time = None
        
        # GPT-4o-mini pricing (as of June 2025)
        self.input_token_cost = 0.00000015  # $0.150 per 1M tokens
        self.output_token_cost = 0.00000060  # $0.600 per 1M tokens
    
    def start_tracking(self):
        """Start the tracking session"""
        self.start_time = time.time()
        print("🚀 STARTING TOKEN CONSUMPTION TEST")
        print("=" * 60)
        print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🆔 Session ID: {SESSION_ID}")
        print(f"📊 Test Queries: {len(TEST_QUERIES)}")
        print(f"💰 Pricing: ${self.input_token_cost:.6f}/input token, ${self.output_token_cost:.6f}/output token")
        print("=" * 60)
    
    def track_query(self, query_num: int, query: str, response_data: Dict[str, Any], response_time: float):
        """Track a single query's token usage"""
        
        # Extract response data
        response_text = response_data.get('response', '')
        sources = response_data.get('sources', [])
        confidence = response_data.get('confidence', 0.0)
        
        # Estimate tokens (rough calculation: 4 chars = 1 token)
        estimated_input_tokens = len(query) // 4 + 900  # Query + system prompt estimate
        estimated_output_tokens = len(response_text) // 4
        estimated_total_tokens = estimated_input_tokens + estimated_output_tokens
        estimated_cost = (estimated_input_tokens * self.input_token_cost) + (estimated_output_tokens * self.output_token_cost)
        
        # Update totals
        self.total_input_tokens += estimated_input_tokens
        self.total_output_tokens += estimated_output_tokens
        self.total_cost += estimated_cost
        
        # Determine query type
        detail_keywords = ['koliko', 'košta', 'program', 'detaljno', 'cenovnik', 'kada', 'datumi', 'uključeno']
        is_detailed = any(keyword in query.lower() for keyword in detail_keywords)
        
        # Store result
        result = {
            'query_num': query_num,
            'query': query,
            'query_type': 'detailed' if is_detailed else 'standard',
            'response_length': len(response_text),
            'sources_count': len(sources),
            'confidence': confidence,
            'response_time': response_time,
            'estimated_input_tokens': estimated_input_tokens,
            'estimated_output_tokens': estimated_output_tokens,
            'estimated_total_tokens': estimated_total_tokens,
            'estimated_cost': estimated_cost
        }
        
        self.query_results.append(result)
        
        # Print query result
        print(f"📝 Query {query_num:2d}: {query[:50]}{'...' if len(query) > 50 else ''}")
        print(f"   Type: {result['query_type'].upper()}")
        print(f"   Response: {len(response_text)} chars, {len(sources)} sources, {confidence:.2f} confidence")
        print(f"   Tokens: ~{estimated_input_tokens} in + ~{estimated_output_tokens} out = ~{estimated_total_tokens} total")
        print(f"   Cost: ~${estimated_cost:.6f}")
        print(f"   Time: {response_time:.2f}s")
        print()
    
    def finish_tracking(self):
        """Complete tracking and generate summary"""
        self.end_time = time.time()
        total_time = self.end_time - self.start_time
        
        print("=" * 60)
        print("📊 TOKEN CONSUMPTION SUMMARY")
        print("=" * 60)
        
        # Basic stats
        print(f"🕒 Total Test Time: {total_time:.1f} seconds")
        print(f"⚡ Average Response Time: {total_time/len(TEST_QUERIES):.2f}s per query")
        print()
        
        # Token usage
        print(f"🔢 TOKEN USAGE:")
        print(f"   Input Tokens:  {self.total_input_tokens:,}")
        print(f"   Output Tokens: {self.total_output_tokens:,}")
        print(f"   Total Tokens:  {self.total_input_tokens + self.total_output_tokens:,}")
        print()
        
        # Cost analysis
        print(f"💰 COST ANALYSIS:")
        print(f"   Total Cost: ${self.total_cost:.6f}")
        print(f"   Cost per Query: ${self.total_cost/len(TEST_QUERIES):.6f}")
        print()
        
        # Extrapolations
        cost_per_1000 = (self.total_cost / len(TEST_QUERIES)) * 1000
        queries_for_15_dollars = 15 / (self.total_cost / len(TEST_QUERIES))
        
        print(f"📈 EXTRAPOLATIONS:")
        print(f"   Cost per 1,000 queries: ${cost_per_1000:.2f}")
        print(f"   Queries possible with $15 budget: {queries_for_15_dollars:,.0f}")
        print()
        
        # Query type breakdown
        standard_queries = [r for r in self.query_results if r['query_type'] == 'standard']
        detailed_queries = [r for r in self.query_results if r['query_type'] == 'detailed']
        
        if standard_queries:
            avg_standard_cost = sum(r['estimated_cost'] for r in standard_queries) / len(standard_queries)
            avg_standard_tokens = sum(r['estimated_total_tokens'] for r in standard_queries) / len(standard_queries)
            print(f"📋 STANDARD QUERIES ({len(standard_queries)} queries):")
            print(f"   Average Cost: ${avg_standard_cost:.6f}")
            print(f"   Average Tokens: {avg_standard_tokens:.0f}")
            print()
        
        if detailed_queries:
            avg_detailed_cost = sum(r['estimated_cost'] for r in detailed_queries) / len(detailed_queries)
            avg_detailed_tokens = sum(r['estimated_total_tokens'] for r in detailed_queries) / len(detailed_queries)
            print(f"📋 DETAILED QUERIES ({len(detailed_queries)} queries):")
            print(f"   Average Cost: ${avg_detailed_cost:.6f}")
            print(f"   Average Tokens: {avg_detailed_tokens:.0f}")
            print()
        
        # Performance metrics
        avg_confidence = sum(r['confidence'] for r in self.query_results) / len(self.query_results)
        total_sources = sum(r['sources_count'] for r in self.query_results)
        
        print(f"🎯 PERFORMANCE METRICS:")
        print(f"   Average Confidence: {avg_confidence:.2f}")
        print(f"   Total Sources Used: {total_sources}")
        print(f"   Average Sources per Query: {total_sources/len(TEST_QUERIES):.1f}")
        print()
        
        # Budget recommendations
        print(f"💡 BUDGET RECOMMENDATIONS:")
        if cost_per_1000 < 0.50:
            print(f"   ✅ EXCELLENT: Very cost-effective at ${cost_per_1000:.2f}/1000 queries")
        elif cost_per_1000 < 1.00:
            print(f"   ✅ GOOD: Cost-effective at ${cost_per_1000:.2f}/1000 queries")
        elif cost_per_1000 < 2.00:
            print(f"   ⚠️  MODERATE: Acceptable cost at ${cost_per_1000:.2f}/1000 queries")
        else:
            print(f"   ❌ HIGH: Consider optimization - ${cost_per_1000:.2f}/1000 queries")
        
        print("=" * 60)
        
        return {
            'total_queries': len(TEST_QUERIES),
            'total_time': total_time,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_tokens': self.total_input_tokens + self.total_output_tokens,
            'total_cost': self.total_cost,
            'cost_per_query': self.total_cost / len(TEST_QUERIES),
            'cost_per_1000_queries': cost_per_1000,
            'queries_for_15_dollars': queries_for_15_dollars,
            'average_confidence': avg_confidence,
            'query_results': self.query_results
        }

def make_chat_request(query: str) -> tuple[Dict[str, Any], float]:
    """Make a chat request and measure response time"""
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={
                "message": query,
                "session_id": SESSION_ID,
                "user_type": "client"
            },
            timeout=30
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        if response.status_code == 200:
            return response.json(), response_time
        else:
            print(f"   ❌ ERROR: HTTP {response.status_code}")
            return {}, response_time
            
    except requests.exceptions.Timeout:
        print(f"   ⏰ TIMEOUT: Query took longer than 30 seconds")
        return {}, 30.0
    except requests.exceptions.RequestException as e:
        print(f"   ❌ REQUEST ERROR: {e}")
        return {}, 0.0

def check_server_health() -> bool:
    """Check if the server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

async def run_token_consumption_test():
    """Run the complete token consumption test"""
    
    # Check server health
    print("🔍 Checking server health...")
    if not check_server_health():
        print("❌ Server is not running! Please start the backend server:")
        print("   uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        return
    
    print("✅ Server is healthy!")
    print()
    
    # Initialize tracker
    tracker = TokenConsumptionTracker()
    tracker.start_tracking()
    
    # Run all queries
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"🔄 Processing query {i}/{len(TEST_QUERIES)}...")
        
        response_data, response_time = make_chat_request(query)
        
        if response_data:
            tracker.track_query(i, query, response_data, response_time)
        else:
            print(f"   ❌ Failed to get response for query {i}")
            print()
        
        # Small delay between requests to avoid overwhelming the server
        await asyncio.sleep(0.5)
    
    # Generate final summary
    summary = tracker.finish_tracking()
    
    # Save detailed results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"token_consumption_results_{timestamp}.json"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"💾 Detailed results saved to: {results_file}")
    print()
    print("🎉 Token consumption test completed!")

if __name__ == "__main__":
    asyncio.run(run_token_consumption_test()) 