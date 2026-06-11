from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# Stub data for testing
STUB_INSTITUTIONS = [
    {
        "id": "https://openalex.org/I136199984",
        "ror_id": "https://ror.org/042nb2s44",
        "name": "Massachusetts Institute of Technology",
        "country": "United States",
        "location": "Cambridge, MA"
    },
    {
        "id": "https://openalex.org/I17837138",
        "ror_id": "https://ror.org/00cvxb145",
        "name": "University of Washington",
        "country": "United States", 
        "location": "Seattle, WA"
    },
    {
        "id": "https://openalex.org/I86982357",
        "ror_id": "https://ror.org/013meh722",
        "name": "University of Cambridge",
        "country": "United Kingdom",
        "location": "Cambridge, UK"
    }
]

@app.route('/')
def home():
    return jsonify({
        "message": "Welcome to orgID API",
        "version": "0.1.0-stub",
        "endpoints": {
            "GET /institutions": "Match single affiliation string to institutions",
            "POST /institutions": "Match multiple affiliation strings to institutions",
            "GET /tests-results/<status>": "Get test results by status"
        }
    })

@app.route('/institutions', methods=['GET'])
def get_institutions():
    affiliation_string = request.args.get('affiliation_string', '')
    
    if not affiliation_string:
        return jsonify({"error": "affiliation_string parameter is required"}), 400
    
    # Stub matching logic - just return institutions that contain keywords
    keywords = affiliation_string.lower().split()
    matched_institutions = []
    
    for institution in STUB_INSTITUTIONS:
        if any(keyword in institution['name'].lower() or 
               keyword in institution['location'].lower() 
               for keyword in keywords):
            matched_institutions.append(institution)
    
    return jsonify({
        "result": {
            "affiliation_string": affiliation_string,
            "matched_institutions": matched_institutions,
            "match_count": len(matched_institutions),
            "status": "stub_implementation"
        }
    })

@app.route('/institutions', methods=['POST'])
def post_institutions():
    data = request.get_json()
    
    if not data or 'affiliation_strings' not in data:
        return jsonify({"error": "affiliation_strings field is required in request body"}), 400
    
    affiliation_strings = data['affiliation_strings']
    
    if not isinstance(affiliation_strings, list):
        return jsonify({"error": "affiliation_strings must be a list"}), 400
    
    results = []
    
    for affiliation_string in affiliation_strings:
        # Stub matching logic - same as GET endpoint
        keywords = affiliation_string.lower().split()
        matched_institutions = []
        
        for institution in STUB_INSTITUTIONS:
            if any(keyword in institution['name'].lower() or 
                   keyword in institution['location'].lower() 
                   for keyword in keywords):
                matched_institutions.append(institution)
        
        results.append({
            "affiliation_string": affiliation_string,
            "matched_institutions": matched_institutions,
            "match_count": len(matched_institutions),
            "status": "stub_implementation"
        })
    
    return jsonify({"results": results})

@app.route('/tests-results/<status>', methods=['GET'])
def get_test_results(status):
    # Stub test results
    stub_test_results = {
        "match": [
            {
                "affiliation_string": "MIT, Cambridge, MA",
                "expected_ror_id": "https://ror.org/042nb2s44",
                "matched_ror_id": "https://ror.org/042nb2s44",
                "status": "match",
                "confidence": 0.95
            }
        ],
        "precision_error": [
            {
                "affiliation_string": "University of Cambridge, UK",
                "expected_ror_id": "https://ror.org/013meh722",
                "matched_ror_id": "https://ror.org/00cvxb145",
                "status": "precision_error",
                "confidence": 0.78
            }
        ],
        "recall_error": [
            {
                "affiliation_string": "Stanford University, California",
                "expected_ror_id": "https://ror.org/00f54p054",
                "matched_ror_id": None,
                "status": "recall_error",
                "confidence": 0.0
            }
        ]
    }
    
    if status not in stub_test_results:
        return jsonify({"error": f"Invalid status. Must be one of: {', '.join(stub_test_results.keys())}"}), 400
    
    return jsonify({
        "status": status,
        "results": stub_test_results[status],
        "total_count": len(stub_test_results[status]),
        "note": "This is stub data for testing purposes"
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
