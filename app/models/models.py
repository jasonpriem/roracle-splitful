from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class Institution(BaseModel):
    """Institution model representing academic institutions."""
    id: str = Field(..., description="The OpenAlex ID of the institution")
    name: str = Field(..., description="The name of the institution")
    ror: str = Field(..., description="The ROR ID of the institution")
    alternate_names: List[str] = Field(default_factory=list, description="A list of alternate names for the institution")

class Match(BaseModel):
    """Match model representing a matching institution for a token."""
    token: str = Field(..., description="The token we matched on")
    institution: Institution = Field(..., description="The matching Institution object")
    is_token_unique: bool = Field(..., description="Whether the token was unique or not")

class QueryResult(BaseModel):
    """Result model for institution queries."""
    query: str = Field(..., description="The original query string")
    geonames: List[str] = Field(default_factory=list, description="A list of geonames found in the query")
    matches: List[Match] = Field(default_factory=list, description="A list of matching institutions")

class TestMatch(BaseModel):
    """Model for test results."""
    correct: List[Match] = Field(default_factory=list, description="Correct matches")
    overmatched: List[Match] = Field(default_factory=list, description="Overmatched results")
    undermatched: List[Institution] = Field(default_factory=list, description="Undermatched institutions")

class Test(BaseModel):
    """Test model for evaluating the API."""
    id: str = Field(..., description="The ID of the test")
    query: str = Field(..., description="The original query")
    is_passing: bool = Field(..., description="Whether the test passed")
    results: TestMatch = Field(..., description="Test results")

class TestResult(BaseModel):
    """Result model for test runs."""
    meta: Dict[str, Any] = Field(..., description="Metadata about test run")
    results: List[Test] = Field(default_factory=list, description="List of test results")
