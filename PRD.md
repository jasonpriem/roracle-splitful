# About
orgID is an API that turns text strings describing academic entities ("affliation strings") into OpenAlex and ROR IDs. 

# API endpoints


## GET /entities/institutions
Get a list of matching institution IDs from a text string. 

### Parameters

* Query parameters:
  * `query`: The text string match against.

### Response

* `query`: The original query
* `entities`: A list of Institution objects for that query. Note this is a list, because each query string can have multiple institution matches in it.

### How it works

### Geocoding
We use the Python flashgeotext library to find geonames in the query string. We save these for later. Geonames are often scattered all over the string, so we can't connect them to tokens unfortunately, but they can still be useful for disambiguating common institution names.

#### Tokenization
We split the query string into tokens. Each token represents a potential institution name. Here's the tokenization:
  1. words in all-uppercase become tokens and are removed from the string.
  2. Words or phrases within parantheses become tokens and are removed from the string (parentheses are discarded).
  3. The rest of the string is split on commas, semicolons, and any type of dash or hyphen (em dash, en dash, etc). 
  4. Remove any tokens shorter than 3 chars.

#### Normalization

For each token, we:
1. Collapse all whitespace to a single space.
2. Lowercase all characters unless the word is all-uppercase.
3. Remove all punctuation.
4. Replace all accented characters with their unaccented equivalents.

#### Institution lookup
For each normalized token, we look up the institution in the in-memory lookup table. What we do next depends on the number of matches:
* 0 matches: We skip this token.
* 1 match: We add this institution to the list of matching Institutions that will be returned to the user
* >1 match: look for a match between any of the geonames found in the overall affiliation string, and the location_name, country_subdivision_name, or country_name of each institution. If there's one match, we use that institution. If there's more than one match, we skip this token.


## POST /entities/institutions
Same as GET /entities/institutions, but in a batch.

### Parameters

none

### Request body

* `queries`: A list of text strings to match against.

### Response

* `queries`: A list of queries with their matches
  * `query`: The original query
  * `geonames`: A list of geonames found in the overall affiliation string
  * `matches`: A list describing matching institutions
    * `token`: The token we matched on
    * `institution`: The matching Institution object
    * `is_token_unique`: A boolean indicating whether the token was unique, or if there were multiple institutions that matched


## POST /tests/:dataset
Run a batch of tests from a particular dataset.

### Parameters

* `dataset`: The dataset of tests to use, as defined in the "dataset" column of the tests csv.

### Request body

* `tests`: A list of tests to run.
  * `id`: The ID of the test.
  * `query`: The text string to match against.
  * `expected_entities`: A list of expected Institution objects.

### Response

* `meta`:
  * `total`: The total number of tests run
  * `passing`: The number of passing tests
  * `failing`: The number of failing tests
  * `performance`: A dictionary of performance metrics
    * `percentage_passing`: The percentage of passing tests
    * `precision`: The precision of the tests
    * `recall`: The recall of the tests
  * `timing`: A dictionary of timing metrics
    * `total`: The total time taken to run the tests
    * `setup`: The time taken to setup the tests
    * `per_test`: The average time taken per test. This doesn't include setup time. 
* `results`: A list of Test objects

### How it works
When the test endpoint is called, it:
1. Pulls all the tests from a CSV here: https://docs.google.com/spreadsheets/d/e/2PACX-1vR_sVx4ts9ndZJ6UP8mPqKd-Rw_v-_A_ShaIvgIE4QhmdPeNb5H7GUPZIBZiMEXvLax1iAChlH6Mk6W/pub?output=csv. Don't save the tests anywhere; load them fresh every time the endpoint is called.
2. Filters the tests to run only the ones from the specified dataset.
3. Runs each test by calling the same function used by `GET /entities/institutions`
4. Returns the results. The expected entities are hydrated into Institution objects using data from the ror_with_openalex.csv file.



# API objects

## QueryResult

* `query`: The original query
* `geonames`: A list of geonames found in the overall affiliation string
* `matches`: A list describing matching institutions
  * `token`: The token we matched on
  * `institution`: The matching Institution object
  * `is_token_unique`: A boolean indicating whether the token was unique, or if there were multiple institutions that matched

## Institution

* `id`: The OpenAlex ID of the institution
* `name`: The name of the institution
* `ror`: The ROR ID of the institution
* `alternate_names`: A list of alternate names for the institution


## Test

* `id`: The ID of the test
* `query`: The original query
* `is_passing`: A boolean indicating whether the test passed
* `results`:
  * `correct`: A list of QueryResult objects that matched the expected institution
  * `overmatched`: A list of QueryResult objects that did NOT match the expected institution
  * `undermatched`: A list of Institution objects that should have been matched, but weren't


  ## Key functions

  ### normalize(str)
  Normalize a string by:
  1. Collapsing all whitespace to a single space.
  2. Lowercasing all characters unless the word is all-uppercase.
  3. Removing all punctuation.
  4. Replacing all accented characters with their unaccented equivalents.



# App boot

When the app boots, it builds a few dictionaries as lookup tables in memory: 
* `normalized_name_to_ror_id`: 
  * key: The normalized name of the institution (using the `normalize` function)
  * value: A list of ROR IDs that match that name
* `ror_id_to_record`: 
  * key: The ROR ID of the institution
  * value: The Institution object

# Stack
The app is build in Python 3, using the FastAPI framework. The app is deployed on Vercel