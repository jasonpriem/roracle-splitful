#!/usr/bin/env python3
"""
Script to download the latest ROR data dump from Zenodo
Based on instructions from: https://ror.readme.io/docs/data-dump

This script specifically targets the schema v2 JSON file and automatically extracts it
if it comes in a ZIP archive.
"""

import os
import sys
import requests
import json
from tqdm import tqdm
import zipfile
import shutil
import csv
import time
from collections import defaultdict
import concurrent.futures
import threading
import queue
import argparse

def get_latest_ror_data_url():
    """
    Get the URL of the latest ROR data dump from Zenodo
    Specifically targeting schema v2 JSON file
    """
    # Based on the updated Zenodo API (after Oct 13, 2023)
    api_url = "https://zenodo.org/api/communities/ror-data/records?q=&sort=newest"
    
    print("Fetching latest ROR data record from Zenodo...")
    response = requests.get(api_url)
    
    if response.status_code != 200:
        print(f"Error: Failed to fetch data from Zenodo API. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)
    
    data = response.json()
    
    # Check if we have any hits
    if not data.get('hits', {}).get('hits', []):
        print("Error: No records found in the ROR data community.")
        sys.exit(1)
    
    # Get the most recent record
    latest_record = data['hits']['hits'][0]
    
    print(f"Latest version: {latest_record.get('metadata', {}).get('version', 'Unknown')}")
    print(f"Published: {latest_record.get('created', 'Unknown date')}")
    
    # Check if there are any files
    if 'files' not in latest_record:
        print("Error: No files entry found in the latest record.")
        print("API response structure:", json.dumps(latest_record.keys(), indent=2))
        sys.exit(1)
    
    # Get file information
    files = latest_record['files']
    
    if not files:
        print("Error: No files found in the latest record.")
        sys.exit(1)
    
    # Print available files with proper error handling
    print("\nAvailable files:")
    for i, file in enumerate(files):
        # Handle different API response formats
        if isinstance(file, dict):
            name = file.get('key', file.get('filename', 'Unknown'))
            size = file.get('size', file.get('filesize', 0))
            print(f"{i+1}. {name} ({format_size(size)})")
    
    # First priority: Look for schema v2 JSON file directly
    schema_v2_json_file = None
    json_in_zip = None
    
    for file in files:
        if not isinstance(file, dict):
            continue
            
        filename = file.get('key', file.get('filename', ''))
        if not filename:
            continue
        
        # Look for schema v2 JSON directly
        if filename.endswith('_schema_v2.json'):
            schema_v2_json_file = file
            break
            
        # Check if it's a ZIP file that might contain schema v2 JSON
        if filename.endswith('.zip'):
            json_in_zip = file
    
    # If no schema v2 JSON file found directly, use ZIP file that might contain it
    target_file = schema_v2_json_file if schema_v2_json_file else json_in_zip
    
    if not target_file:
        print("Error: Could not find a suitable schema v2 JSON file or ZIP that might contain it.")
        sys.exit(1)
    
    # Try different keys for download URL based on Zenodo API changes
    download_url = None
    if 'links' in target_file and 'self' in target_file['links']:
        download_url = target_file['links']['self']
    elif 'links' in target_file and 'download' in target_file['links']:
        download_url = target_file['links']['download']
    
    if not download_url:
        print("Error: Could not find download URL in the file information.")
        print("File structure:", json.dumps(target_file, indent=2))
        sys.exit(1)
    
    # Get filename using different possible keys
    filename = target_file.get('key', target_file.get('filename', 'ror-data.json'))
    
    # Get filesize using different possible keys
    filesize = target_file.get('size', target_file.get('filesize', 0))
    
    return download_url, filename, filesize

def format_size(size_bytes):
    """Format file size in human-readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names)-1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"

def download_file(url, filename, filesize):
    """
    Download a file with progress bar
    """
    download_dir = 'downloads'
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    local_filename = os.path.join(download_dir, filename)
    
    print(f"\nDownloading {filename} ({format_size(filesize)})...")
    print(f"Download URL: {url}")
    
    # Stream the download to show progress
    response = requests.get(url, stream=True)
    
    if response.status_code != 200:
        print(f"Error: Failed to download file. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)
    
    # Get total size
    total_size = int(response.headers.get('content-length', filesize))
    
    # Write the file with progress bar
    with open(local_filename, 'wb') as f:
        with tqdm(total=total_size, unit='B', unit_scale=True, unit_divisor=1024) as pbar:
            for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
    
    print(f"\nDownload complete! File saved to: {os.path.abspath(local_filename)}")
    return local_filename

def extract_schema_v2_json(downloaded_file):
    """
    Extract the schema v2 JSON file from the downloaded ZIP file
    """
    if not downloaded_file.endswith('.zip'):
        print(f"File is not a ZIP archive, no extraction needed: {downloaded_file}")
        return downloaded_file
    
    extract_dir = os.path.join(os.path.dirname(downloaded_file), 'extracted')
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)
    
    print(f"\nExtracting {os.path.basename(downloaded_file)} to find schema v2 JSON file...")
    
    schema_v2_file = None
    
    # Extract the ZIP file
    with zipfile.ZipFile(downloaded_file, 'r') as zip_ref:
        # List contents
        contents = zip_ref.namelist()
        
        # Look for schema v2 JSON file
        for item in contents:
            if item.endswith('_schema_v2.json'):
                schema_v2_file = item
                break
        
        if not schema_v2_file:
            print("Warning: Could not find schema v2 JSON file in the ZIP archive.")
            print("Extracting all contents instead.")
            zip_ref.extractall(extract_dir)
            return os.path.join(extract_dir, contents[0] if contents else '')
        
        # Extract only the schema v2 JSON file
        zip_ref.extract(schema_v2_file, extract_dir)
    
    extracted_file = os.path.join(extract_dir, schema_v2_file)
    print(f"Extracted schema v2 JSON file: {extracted_file}")
    return extracted_file

def convert_to_csv(json_file, include_openalex_column=True):
    """
    Convert ROR JSON data to CSV file with the specified columns.
    
    Columns:
    * id: the ROR ID, without the prefix (eg `04ttjf776`)
    * openalex_id: OpenAlex ID (included only if include_openalex_column is True)
    * display_name: ror_display name
    * acronyms
    * names: all other names
    * location_name: locations[0].name
    * country_subdivision_name: locations[0].country_subdivision_name
    * country_name: locations[0].country_name
    * country_code: locations[0].country_code
    * is_company: types includes "company"
    """
    print(f"Converting {json_file} to CSV...")
    
    # Output file path
    csv_file = os.path.join(os.path.dirname(json_file), 'ror.csv')
    
    # Read the JSON data
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Found {len(data)} ROR records to process.")
    
    # Define CSV headers
    headers = ['id']
    if include_openalex_column:
        headers.append('openalex_id')
    headers.extend([
        'display_name', 'acronyms', 'names', 'location_name',
        'country_subdivision_name', 'country_name', 'country_code', 'is_company'
    ])
    
    # Write to CSV
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        # Process each ROR record
        for record in tqdm(data, desc="Writing CSV", unit="record"):
            # Extract ID (without prefix)
            ror_id = record.get('id', '').replace('https://ror.org/', '')
            
            # Base row without openalex_id
            row = [ror_id]
            
            # Add empty openalex_id column if needed
            if include_openalex_column:
                row.append('')
            
            # Add other fields
            row.extend([
                record.get('name', ''),  # display_name
                ';'.join(record.get('acronyms', [])),  # acronyms
                ';'.join([n.get('value', '') for n in record.get('names', [])]),  # names
                record.get('addresses', [{}])[0].get('city', '') if record.get('addresses') else '',  # location_name
                record.get('addresses', [{}])[0].get('state', '') if record.get('addresses') else '',  # country_subdivision_name
                record.get('addresses', [{}])[0].get('country_name', '') if record.get('addresses') else '',  # country_name
                record.get('addresses', [{}])[0].get('country_code', '') if record.get('addresses') else '',  # country_code
                'Company' in record.get('types', [])  # is_company
            ])
            
            writer.writerow(row)
    
    print(f"CSV file created: {csv_file}")
    return csv_file

def add_openalex_ids_to_csv(csv_file):
    """
    Add OpenAlex IDs to the CSV file by fetching them from the OpenAlex API.
    
    Args:
        csv_file: Path to the CSV file
        
    Returns:
        Path to the enriched CSV file
    """
    print(f"Adding OpenAlex IDs to {csv_file}...")
    
    # Output file with OpenAlex IDs
    base_dir = os.path.dirname(csv_file)
    output_file = os.path.join(base_dir, "ror_with_openalex.csv")
    
    # Read all ROR IDs from the CSV file
    ror_ids = []
    with open(csv_file, 'r', encoding='utf-8', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            ror_ids.append(row['id'])
    
    print(f"Found {len(ror_ids)} ROR IDs in the CSV file")
    
    # Fetch OpenAlex IDs in batches
    api_key = "PevDKCMHv88RXESPAWpja4"  # Using the API key from user's memory
    ror_to_openalex = fetch_openalex_ids(ror_ids, api_key)
    
    # Count the ROR IDs without an OpenAlex ID
    missing_openalex_count = len(ror_ids) - len(ror_to_openalex)
    
    # Update the CSV file with OpenAlex IDs
    print(f"Updating CSV file with OpenAlex IDs...")
    with open(csv_file, 'r', encoding='utf-8', newline='') as input_file, \
         open(output_file, 'w', encoding='utf-8', newline='') as output_file:
        
        reader = csv.DictReader(input_file)
        writer = csv.DictWriter(output_file, fieldnames=reader.fieldnames)
        writer.writeheader()
        
        for row in tqdm(reader, total=len(ror_ids), desc="Updating CSV"):
            ror_id = row['id']
            openalex_id = ror_to_openalex.get(ror_id, '')
            row['openalex_id'] = openalex_id
            writer.writerow(row)
    
    print(f"CSV update complete! File saved to: {os.path.abspath(output_file)}")
    print(f"OpenAlex ID statistics:")
    print(f"  - ROR IDs with OpenAlex ID: {len(ror_to_openalex)}")
    print(f"  - ROR IDs without OpenAlex ID: {missing_openalex_count}")
    print(f"  - Percentage with OpenAlex ID: {(len(ror_to_openalex) / len(ror_ids) * 100):.2f}%")
    
    return output_file

def fetch_openalex_ids(ror_ids, api_key=None, max_retries=3, retry_delay=2, max_workers=10):
    """
    Fetch OpenAlex IDs for a list of ROR IDs in batches using parallel processing.
    Returns a dictionary mapping ROR IDs to OpenAlex IDs.
    
    Args:
        ror_ids: List of ROR IDs (without prefix)
        api_key: OpenAlex API key
        max_retries: Maximum number of retry attempts for failed requests
        retry_delay: Delay between retries in seconds
        max_workers: Maximum number of parallel workers for API requests
    
    Returns:
        Dictionary mapping ROR IDs to OpenAlex IDs
    """
    print("\nFetching OpenAlex IDs for ROR records...")
    
    # Create batches of 90 ROR IDs
    batches = []
    batch = []
    for ror_id in ror_ids:
        batch.append(ror_id)
        if len(batch) == 90:
            batches.append(batch)
            batch = []
    if batch:  # Add the remaining ROR IDs
        batches.append(batch)
    
    total_batches = len(batches)
    print(f"Processing {len(ror_ids)} ROR IDs in {total_batches} batches of up to 90 ROR IDs each...")
    print(f"Using parallel processing with up to {max_workers} workers")
    print(f"Enforcing OpenAlex API rate limit of 5 requests per second")
    
    # Initialize the mapping dictionary (ROR ID -> OpenAlex ID)
    ror_to_openalex = {}
    
    # Set up the headers with API key if provided
    headers = {}
    if api_key:
        print(f"Using provided OpenAlex API key")
        headers["X-API-Key"] = api_key
    
    # Thread-safe counter for progress tracking
    class Counter:
        def __init__(self):
            self.count = 0
            self.lock = threading.Lock()
            
        def increment(self):
            with self.lock:
                self.count += 1
                return self.count
    
    # Rate limiter for OpenAlex API (5 requests per second)
    class RateLimiter:
        def __init__(self, rate=5):
            self.rate = rate  # requests per second
            self.last_check = time.time()
            self.tokens = rate  # start with max tokens
            self.lock = threading.Lock()
            
        def wait_for_token(self):
            with self.lock:
                while True:
                    now = time.time()
                    time_passed = now - self.last_check
                    
                    # Add tokens based on time passed, up to max rate
                    self.tokens += time_passed * self.rate
                    if self.tokens > self.rate:
                        self.tokens = self.rate
                    
                    self.last_check = now
                    
                    # If we have at least one token, consume it and proceed
                    if self.tokens >= 1:
                        self.tokens -= 1
                        return
                    
                    # No tokens available, calculate sleep time and release lock temporarily
                    sleep_time = (1 - self.tokens) / self.rate
                    
                    # Don't hold the lock while sleeping
                    self.lock.release()
                    time.sleep(sleep_time)
                    self.lock.acquire()
    
    # Create rate limiter
    rate_limiter = RateLimiter(rate=5)  # 5 requests per second
    
    # Statistics for tracking
    counter = Counter()
    failed_batches = []
    start_time = time.time()
    found_count = 0
    lock = threading.Lock()  # Lock for thread-safe updates to shared resources
    
    # Function to process a single batch
    def process_batch(batch_with_idx):
        batch_idx, batch = batch_with_idx
        batch_results = {}
        success = False
        attempts = 0
        
        # Format the ROR IDs for the API request
        ror_filter = "|".join([f"https://ror.org/{ror_id}" for ror_id in batch])
        
        # Construct the API URL with per-page=90 to get all results in one page
        url = f"https://api.openalex.org/institutions?select=id,ror&filter=ror:{ror_filter}&per-page=90"
        
        # Try up to max_retries times
        while not success and attempts < max_retries:
            try:
                if attempts > 0:
                    print(f"  Retry attempt {attempts}/{max_retries} for batch {batch_idx+1}/{total_batches}")
                
                # Wait for rate limiting token before making the request
                rate_limiter.wait_for_token()
                
                # Make the request
                response = requests.get(url, headers=headers)
                
                # Check if the request was successful
                if response.status_code == 200:
                    data = response.json()
                    
                    # Process the results
                    found_in_batch = 0
                    for result in data.get('results', []):
                        openalex_id = result.get('id', '')
                        ror_url = result.get('ror', '')
                        
                        # Extract the ROR ID without the prefix
                        if ror_url and ror_url.startswith('https://ror.org/'):
                            ror_id = ror_url[16:]  # Remove the "https://ror.org/" prefix
                            
                            # Extract the OpenAlex ID with the "I" prefix
                            if openalex_id and openalex_id.startswith('https://openalex.org/I'):
                                openalex_id = "I" + openalex_id[22:]  # Keep the "I" prefix but remove "https://openalex.org/"
                                batch_results[ror_id] = openalex_id
                                found_in_batch += 1
                    
                    success = True
                    
                    # Update progress with thread safety
                    with lock:
                        nonlocal found_count
                        found_count += found_in_batch
                    
                    # Track progress
                    completed = counter.increment()
                    
                    # Calculate progress and estimates
                    elapsed_time = time.time() - start_time
                    if completed > 0:
                        avg_time_per_batch = elapsed_time / completed
                        remaining_batches = total_batches - completed
                        estimated_time_remaining = avg_time_per_batch * remaining_batches / max_workers
                        
                        # Print progress information
                        print(f"Batch {batch_idx+1}/{total_batches} completed: Found {found_in_batch}/{len(batch)} OpenAlex IDs")
                        print(f"Progress: {completed}/{total_batches} batches ({(completed/total_batches*100):.1f}%)")
                        print(f"Time: {elapsed_time:.1f}s elapsed, ~{estimated_time_remaining:.1f}s remaining, ETA: {time.strftime('%H:%M:%S', time.localtime(time.time() + estimated_time_remaining))}")
                
                elif response.status_code == 429:  # Rate limit exceeded
                    print(f"Rate limit exceeded for batch {batch_idx+1}/{total_batches}")
                    attempts += 1
                    
                    # Wait longer when rate limited
                    wait_time = retry_delay * 2
                    print(f"  Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                
                else:
                    print(f"Error fetching batch {batch_idx+1}/{total_batches}: Status code {response.status_code}")
                    print(f"Response: {response.text[:200]}...")  # Show truncated response for brevity
                    attempts += 1
                    
                    if attempts < max_retries:
                        print(f"  Waiting {retry_delay} seconds before retry...")
                        time.sleep(retry_delay)
                    else:
                        with lock:
                            failed_batches.append(batch_idx)
                        print(f"  Failed to fetch batch {batch_idx+1} after {max_retries} attempts")
            
            except Exception as e:
                print(f"Exception while fetching batch {batch_idx+1}/{total_batches}: {str(e)}")
                attempts += 1
                
                if attempts < max_retries:
                    print(f"  Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                else:
                    with lock:
                        failed_batches.append(batch_idx)
                    print(f"  Failed to fetch batch {batch_idx+1} after {max_retries} attempts")
        
        return batch_results
    
    # Process batches in parallel
    batch_idx_list = list(enumerate(batches))
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all batch processing tasks
        future_to_batch = {executor.submit(process_batch, batch_with_idx): batch_with_idx[0] for batch_with_idx in batch_idx_list}
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_batch):
            batch_idx = future_to_batch[future]
            try:
                batch_results = future.result()
                with lock:
                    ror_to_openalex.update(batch_results)
            except Exception as exc:
                print(f"Batch {batch_idx+1} generated an exception: {exc}")
                with lock:
                    failed_batches.append(batch_idx)
    
    # Report on failed batches
    if failed_batches:
        print(f"\nWarning: {len(failed_batches)} batches failed after {max_retries} retry attempts")
        print(f"Failed batch indices: {failed_batches}")
    
    # Final statistics
    total_time = time.time() - start_time
    print(f"\nOpenAlex ID fetching completed in {total_time:.1f} seconds")
    print(f"Found OpenAlex IDs for {len(ror_to_openalex)} out of {len(ror_ids)} ROR IDs ({(len(ror_to_openalex) / len(ror_ids) * 100):.2f}%)")
    
    return ror_to_openalex

def main():
    """
    Main function to download and process ROR data
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Download and process ROR data')
    parser.add_argument('--get-openalex-ids', action='store_true', 
                        help='Fetch OpenAlex IDs for ROR records (optional)')
    args = parser.parse_args()
    
    print("ROR Data Downloader (Schema v2 JSON)")
    print("====================================")
    
    # Step 1: Download ROR data
    download_start_time = time.time()
    print("STEP 1: Downloading ROR data dump...")
    
    try:
        # Get the latest ROR data dump URL
        latest_data_url = get_latest_ror_data_url()
        
        # Download the data
        download_path = download_file(latest_data_url[0], latest_data_url[1], latest_data_url[2])
        
        # Extract the schema v2 JSON file if it's a ZIP archive
        json_file = extract_schema_v2_json(download_path)
        
        download_end_time = time.time()
        download_duration = download_end_time - download_start_time
        print(f"\nSTEP 1 COMPLETED: ROR data downloaded and extracted in {download_duration:.2f} seconds")
        print(f"JSON file: {json_file}")
    except Exception as e:
        print(f"Error in Step 1: {str(e)}")
        sys.exit(1)
    
    # Step 2: Convert JSON to CSV
    csv_start_time = time.time()
    print("\nSTEP 2: Converting ROR data to CSV...")
    
    try:
        # Convert to CSV with or without OpenAlex IDs column based on the argument
        csv_file = convert_to_csv(json_file, include_openalex_column=args.get_openalex_ids)
        
        csv_end_time = time.time()
        csv_duration = csv_end_time - csv_start_time
        print(f"\nSTEP 2 COMPLETED: ROR data converted to CSV in {csv_duration:.2f} seconds")
        print(f"CSV file: {csv_file}")
    except Exception as e:
        print(f"Error in Step 2: {str(e)}")
        sys.exit(1)
    
    # Step 3: Fetch OpenAlex IDs and update CSV (only if --get-openalex-ids is provided)
    if args.get_openalex_ids:
        openalex_start_time = time.time()
        print("\nSTEP 3: Fetching OpenAlex IDs for ROR records...")
        
        try:
            # Process the CSV file to add OpenAlex IDs
            enriched_csv_file = add_openalex_ids_to_csv(csv_file)
            
            openalex_end_time = time.time()
            openalex_duration = openalex_end_time - openalex_start_time
            total_duration = openalex_end_time - download_start_time
            
            print(f"\nSTEP 3 COMPLETED: OpenAlex IDs added to CSV in {openalex_duration:.2f} seconds")
            print(f"Final CSV file: {enriched_csv_file}")
            print(f"\nAll steps completed in {total_duration:.2f} seconds!")
        except Exception as e:
            print(f"Error in Step 3: {str(e)}")
            sys.exit(1)
    else:
        # If not getting OpenAlex IDs, show completion message with total time
        total_duration = time.time() - download_start_time
        print(f"\nProcess completed in {total_duration:.2f} seconds!")
        print(f"Final CSV file: {csv_file}")

if __name__ == "__main__":
    main()
