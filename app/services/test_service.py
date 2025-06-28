import csv
import requests
from typing import List, Dict, Any
import pandas as pd
from io import StringIO

from app.models.models import Test, TestMatch, Institution
from app.services.institution_service import InstitutionService
from app.core.config import settings

class TestService:
    """Service for handling tests."""
    
    def __init__(self, institution_service: InstitutionService):
        """Initialize the test service."""
        self.institution_service = institution_service
        self.tests = []
        self.test_data_url = settings.TEST_DATA_URL
        self.openalex_api_key = settings.OPENALEX_API_KEY
    
    async def load_tests(self, dataset: str):
        """Load tests from the CSV file."""
        try:
            # Fresh download of test data from Google Sheets
            headers = {"User-Agent": f"orgID API/1.0 (mailto:info@ourresearch.org) openalex-api-key:{self.openalex_api_key}"}
            response = requests.get(self.test_data_url, headers=headers)
            response.raise_for_status()
            
            # Use pandas to read the CSV data
            df = pd.read_csv(StringIO(response.text))
            
            # Filter tests for the specified dataset
            dataset_tests = df[df['dataset'] == dataset]
            
            self.tests = dataset_tests.to_dict('records')
            
            return self.tests
        except Exception as e:
            print(f"Error loading tests: {e}")
            return []
    
    async def run_tests(self, test_specs: List[Dict]) -> List[Test]:
        """Run tests based on the provided specifications."""
        results = []
        
        # If test_specs is provided, use those; otherwise use loaded tests
        tests_to_run = test_specs if test_specs else self.tests
        
        for test_spec in tests_to_run:
            test_id = test_spec.get('id', '')
            query = test_spec.get('query', '')
            expected_entities = test_spec.get('expected_entities', [])
            
            # Process the query
            query_result = await self.institution_service.process_query(query)
            
            # Extract expected institution IDs
            expected_ids = [entity.get('id') for entity in expected_entities if entity.get('id')]
            
            # Check if all expected institutions were found
            found_ids = [match.institution.id for match in query_result.matches]
            is_passing = all(expected_id in found_ids for expected_id in expected_ids) and len(found_ids) == len(expected_ids)
            
            # Create test result objects
            correct_matches = []
            overmatched = []
            undermatched = []
            
            # Classify matches
            for match in query_result.matches:
                if match.institution.id in expected_ids:
                    correct_matches.append(match)
                else:
                    overmatched.append(match)
            
            # Find undermatched entities
            for entity in expected_entities:
                entity_id = entity.get('id')
                if entity_id and entity_id not in found_ids:
                    institution = Institution(
                        id=entity_id,
                        name=entity.get('name', ''),
                        ror=entity.get('ror', ''),
                        alternate_names=entity.get('alternate_names', [])
                    )
                    undermatched.append(institution)
            
            # Create test result
            test_result = Test(
                id=test_id,
                query=query,
                is_passing=is_passing,
                results=TestMatch(
                    correct=correct_matches,
                    overmatched=overmatched,
                    undermatched=undermatched
                )
            )
            
            results.append(test_result)
        
        return results
    
    def calculate_metrics(self, test_results: List[Test]) -> tuple:
        """Calculate precision and recall metrics for test results."""
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        
        for test in test_results:
            true_positives += len(test.results.correct)
            false_positives += len(test.results.overmatched)
            false_negatives += len(test.results.undermatched)
        
        precision = true_positives / (true_positives + false_positives) if true_positives + false_positives > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if true_positives + false_negatives > 0 else 0
        
        return precision, recall
