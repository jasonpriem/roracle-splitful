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
GET /entities/institutions?query=University%20of%20Washington%2C%20Seattle
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

## API Objects

- **QueryResult**: Result of a query containing matches
- **Institution**: Representation of an academic institution
- **Test**: Test case for evaluating the API

## Data Processing

The application:
1. Uses geocoding to find location names in affiliation strings
2. Tokenizes input strings following specific rules
3. Normalizes tokens for case-insensitive matching
4. Looks up institutions and handles disambiguation

## Note

This application requires the `ror_with_openalex.csv` file in the root directory to function properly.
