# orgID API

An API that turns text strings describing academic entities ("affiliation strings") into OpenAlex and ROR IDs.

## Features

- Match academic affiliation strings to institution IDs
- Batch processing of multiple queries
- Test endpoints for evaluating accuracy
- Geocoding for improved disambiguation

## Setup

1. Ensure you have Python 3.8+ installed
2. Set up a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the application

To start the application:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8742 --reload
```

This will start the API server at http://localhost:8742.

## API Endpoints

### `GET /entities/institutions`

Get a list of matching institution IDs from a text string.

**Example:**
```
curl "http://localhost:5001/institutions?affiliation_string=University%20of%20Washington%2C%20Seattle"
```

### `POST /entities/institutions`

Process multiple queries in batch.

**Example:**
```json
{
  "queries": [
    "University of Washington, Seattle",
    "Harvard Medical School (HMS)"
  ]
}
```

### `POST /tests/:dataset`

Run a batch of tests from a particular dataset.

**Example:**
```json
{
  "tests": [
    {
      "id": "1",
      "query": "University of Washington, Seattle",
      "expected_entities": [
        {
          "id": "https://openalex.org/I12345678",
          "name": "University of Washington",
          "ror": "https://ror.org/01234567"
        }
      ]
    }
  ]
}
```

### GET /tests-results/:status
Get test results by status.

**URL Parameters:**
- `status`: One of `match`, `precision_error`, `recall_error`

**Response:**
```json
{
  "status": "match",
  "results": [...],
  "total_count": 1,
  "note": "This is stub data for testing purposes"
}
```

## Development Status

 **This is currently a stub implementation** for testing the API structure.

### Current Features
- Basic API structure with all endpoints
- Stub data for testing
- Simple keyword matching
- JSON request/response handling

### Coming Soon
- Data loading from CSV files
- Proper tokenization and normalization
- Geonames-based disambiguation
- Real institution matching logic
- Gold standard testing

## Data Files

- `data/ror_with_openalex.csv`: Institution data with ROR and OpenAlex IDs
- `data/gold_random.tsv`: Gold standard test data

## Next Steps

1. Set up Python virtual environment
2. Add proper dependencies (pandas, etc.)
3. Implement data loading from CSV files
4. Build the tokenization and normalization functions
5. Add geonames extraction and matching
6. Implement proper institution matching logic
7. Add comprehensive testing against gold standard
8. Deploy to Heroku
This application requires the `ror_with_openalex.csv` file in the root directory to function properly.
