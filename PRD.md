# About
orgID is an API that turns text strings describing academic entities ("affliation strings") into OpenAlex and ROR IDs. 

# API endpoints

## GET /institutions
Get a list of matching Institution objects from an affiliation string. 

### Parameters

* Query parameters:
  * `affiliation_string`: The affiliation string to match against.

### Response

* `result`: A Result object


## POST /institutions
Get a list of matching Institution objects from a list of affiliation strings. 

### Parameters

* Request body:
  * `affiliation_strings`: A list of affiliation strings to match against.

### Response

* `results`: A list of Result objects


## GET /tests-results/:status
Tests the /institutions endpoint using the data in the gold standard CSV, and resport results.

### Parameters
* URL parameters:
  * `status` (optional): The status of the test results to display. Possible values: `match`, `precision_error`, `recall_error`

### Response
A list of TestResult objects, filtered by the `status` parameter.

### notes
See the Testing section below for more details.



## Creation of lookup table

We create a lookup table in memory when the app boots. This lookup table is a dictionary:
*Key:* A normalized institution name (using the `normalize()` function). There is exactly one key for every normalized institution name string. There will be way more keys than institutions, since most institutions have multiple names.
*Value:* a list (of length 1-many) of institutions (with their ROR IDs, OpenAlex IDs, and geonames) that match this key.

 We also create a reverse lookup table where the key is the ROR ID and the value is the Institution object.

## Tokenization using `tokenize()`

Since each query string can contain multiple institutions, we split the query string into tokens, where each token represents a _single potential institution_. We won't know if a token is a real institution until we look it up; that comes later. This is just finding _potential_ institutions.  Here's the tokenization function, which we'll call `tokenize()`. It proceeds in order as follows:

1. words in all-uppercase become tokens and are removed from the string.
2. Words or phrases within parantheses become tokens and are removed from the string (parentheses are discarded).
3. The rest of the string is split on dividers. These are the dividers: commas, semicolons, and any type of dash or hyphen (em dash, en dash, etc). 

Once we've got our tokens, we remove any tokens shorter than 3 characters, because there's not enough information in them to create a confident match.

## Normalizing tokens using `normalize()`

We normalize each token to make it easier to look up. Here's the normalization function, which we'll call `normalize()`. For each token, we:

1. Trim whitespace from the start and end of the string. (e.g. `  MIT  ` becomes `MIT`)
2. Collapse all repeated whitespace to a single space. (e.g. `univ   florida` becomes `univ florida`)
3. Lowercase all characters _unless the word is all-uppercase_ (e.g. `Florida` becomes `florida` but `MIT` stays `MIT`).
4. Remove all punctuation.
5. Where possible, replace accented characters with their unaccented equivalents. (e.g. `é` becomes `e`)

## Matching tokens to institutions

For each normalized token, we look up the institution in the in-memory lookup table. We'll find that the token matches 0, 1, or >1 institutions. 

What we do next depends on the number of matches:
* 0 matched institutions: We move on to the next token.
* 1 matched institution: We add this institution to the list of matching Institutions that will be returned
* >1 matched institutions: We use the geonames found in the overall affiliation string to narrow down the list of matched institutions. See the Geonames section of this document for more details.

### Geocoding
Affiliation strings often include geonames (country, city, etc). These are super useful for disambiguation, but they are scattered sort of randomly throughout the string, so we can't connect them to tokens.

In affiliation strings, various geonames are often scattered all over the string. so we can't connect them to tokens unfortunately, but they can still be useful for disambiguating common institution names.

Sometimes a given token might match multiple institutions. In that case, we use the geonames found in the overall affiliation string to narrow down the list of matched institutions, in the hopes that we can narrow it down to a single match.

For each institution that matched, we look for a match between any of the geonames found in the overall affiliation string, and the location_name, country_subdivision_name, or country_name of each institution, as found in the lookup table. If there's exactly one match, we use that institution. If there's more than one match, we skip this token.

For example, let's say we have the following affiliation string: "MIT, Cambridge, USA". The token "MIT" matches two institutions: Mumbai Institute of Technology and Massachusetts Institute of Technology, so we're kind of stuck...which should we pick? Well, we can use the geonames found in the overall affiliation string to narrow it down. The geonames found in the overall affiliation string are "Cambridge" and "USA". 

In our lookup table, we see that Massachusetts Institute of Technology has "Cambridge" as its location_name, but Mumbai Institute of Technology doesn't. So we use Massachusetts Institute of Technology.

## Testing

We test the system under test (SUT) against the gold standard included as CSV data in the app. The gold standard is a list of in-out pairs: an affiliation string (in) with expected institution IDs (out). Because some some affilation strings contain multiple institutions, there are often mulitple in-out pairs with the same affiliation string.

We run the tests all together, like this: 

1. We load the gold standard CSV data into memory.
2. We make a list of all the _unique_ affiliation strings in the gold standard.
3. We iterate over this list of unique affiliation strings, running the `/institutions` endpoint (SUT) for each one. 
4. We save all the SUT results as a list of SUT in-out pairs. Since some affiliation strings will return multiple institutions, naturally these generate  _multiple_ SUT in-out pairs. 
5. We compare the SUT in-out pairs with the gold standard in-out pairs, and report the results as a list of TestResult objects. We hydrate the TestResult objects by converting IDs to Institution objects using the reverse lookup table...this makes the results more useful for debugging.

There are three types of TestResult objects, corresponding to the value of the `status` field:

| `status`  | description | pos/neg |
| --- | --- | --- |
| `match` | in both SUT results and gold standard | true positive |
| `precision_error` | in SUT results but not gold standard | false positive |
| `recall_error` | in gold standard but not SUT results | false negative |

 We use the `/tests-results/:status` endpoint to get a list of test results, filtered by the `status` parameter. 


# API objects

## Result

* `affiliation_string`: The submitted affiliation string that we matched against
* `geonames`: A list of geonames found in the submitted affiliation string
* `matches`: A list describing matching institutions
  * `token`: The token we matched on
  * `institution`: The matching Institution object
  * `is_token_unique`: A boolean indicating whether the token was unique, or if there were multiple institutions that matched

## Institution

* `id`: The OpenAlex ID of the institution
* `name`: The primary display name of the institution
* `ror`: The ROR ID of the institution
* `alternate_names`: A list of alternate names for the institution


## TestResult

* `test_id`: The ID of the test
* `affiliation_string`: The original affiliation string (in).
* `sut_institution`: An Institution object from the SUT. `null` if `status` is `recall_error`
* `gold_standard_institution`: The Institution object from the gold standard. `null` if `status` is `precision_error`
* `status`: A string indicating whether the SUT institution matches the gold standard institution. See the table in the Testing section for more details.





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