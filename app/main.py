#!/usr/bin/env python3
"""
Main application file for orgID API.
"""

import time
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app.models.models import QueryResult, Institution, Test, TestResult
from app.services.institution_service import InstitutionService
from app.services.test_service import TestService

# Initialize the app
app = FastAPI(
    title="orgID API",
    description="An API that turns text strings describing academic entities into OpenAlex and ROR IDs",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
institution_service = InstitutionService()

@app.on_event("startup")
async def startup_event():
    """Load data on startup."""
    await institution_service.load_data()

@app.get("/entities/institutions", response_model=QueryResult)
async def get_institutions(query: str = Query(..., description="The text string to match against")):
    """Get a list of matching institution IDs from a text string."""
    return await institution_service.process_query(query)

@app.post("/entities/institutions", response_model=list[QueryResult])
async def post_institutions(request: dict):
    """Process multiple queries in batch."""
    queries = request.get("queries", [])
    results = []
    for query in queries:
        result = await institution_service.process_query(query)
        results.append(result)
    return results

@app.post("/tests/{dataset}", response_model=TestResult)
async def run_tests(dataset: str, request: dict = None):
    """Run a batch of tests from a particular dataset."""
    test_service = TestService(institution_service)
    
    start_time = time.time()
    setup_start = time.time()
    
    # Load tests
    await test_service.load_tests(dataset)
    
    setup_time = time.time() - setup_start
    
    # Run tests
    tests = request.get("tests", []) if request else []
    results = await test_service.run_tests(tests)
    
    total_time = time.time() - start_time
    test_time = total_time - setup_time
    
    # Calculate metrics
    total_tests = len(results)
    passing_tests = sum(1 for test in results if test.is_passing)
    failing_tests = total_tests - passing_tests
    
    # Calculate precision and recall
    precision, recall = test_service.calculate_metrics(results)
    
    return TestResult(
        meta={
            "total": total_tests,
            "passing": passing_tests,
            "failing": failing_tests,
            "performance": {
                "percentage_passing": (passing_tests / total_tests * 100) if total_tests > 0 else 0,
                "precision": precision,
                "recall": recall,
            },
            "timing": {
                "total": total_time,
                "setup": setup_time,
                "per_test": (test_time / total_tests) if total_tests > 0 else 0,
            },
        },
        results=results
    )
