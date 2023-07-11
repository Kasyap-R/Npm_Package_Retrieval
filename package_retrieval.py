import aiohttp
import asyncio
import json
import os
import time

# The directory where JSON files containing package details will be stored.
directory = "npmDetails/"

# Constants to manage the volume of requests and retries
BATCH_SIZE = 10000
MAX_RETRIES = 3  
RETRY_DELAY = 0.1 

# Load the list of package names from a JSON file
with open('names.json', 'r') as f:
    names = json.load(f)

# Determine the total number of packages and batches to be retrieved
num_packages_to_retrieve = len(names)
total_requests = names[:num_packages_to_retrieve]
total_batches = len(total_requests) // BATCH_SIZE + (len(total_requests) % BATCH_SIZE > 0)

# Create lists to track failed packages and error messages
failed_packages = []
error_messages = []

# This function returns a filename-safe version of the package name
def clean_package_name(package_name):
    cipher = {
        "/": "&=%", 
        "*": "&!=%",
    }
    updated_package_name = ''.join(cipher.get(char, char) for char in package_name)
    return updated_package_name

# This function retrieves the details of a given npm package
async def retrieve_package_details(session, package_name):
    shared_link = "https://registry.npmjs.org/"
    url = f"{shared_link}{package_name}"
    custom_file_path = os.path.join(directory, clean_package_name(package_name) + ".json")
    for attempt in range(MAX_RETRIES):
        try:
            # Send a GET request to the npm registry API
            async with session.get(url) as response:
                # If the status code is not 200, an error has occurred
                if response.status != 200:
                    raise Exception(f"HTTP error {response.status}")
                # Parse the response text as JSON and write it to a file
                package_data = json.loads(await response.text())
                json_string = json.dumps(package_data, indent=2)
                with open(custom_file_path, 'w') as f:
                    f.write(json_string)
                return
        except Exception as e:
            # Retry the request if it failed, unless this was the last attempt
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
            else:
                # If all retries failed, log the error and add the package to the list of failed packages
                print(f"Error: {package_name} {e}")
                failed_packages.append(package_name)
                if response.status != 404:
                    error_messages.append(f"{package_name}: {e}") 

# The main function orchestrates the entire operation
async def main():
    # Record the start time of the operation
    start_time = time.time()
    # Create an aiohttp ClientSession, which will be used for all requests
    async with aiohttp.ClientSession() as session:
        # Divide the list of packages into batches and process each batch
        for batch in range(total_batches):
            start_index = batch * BATCH_SIZE
            end_index = start_index + BATCH_SIZE
            batch_requests = total_requests[start_index:end_index]
            tasks = [retrieve_package_details(session, name) for name in batch_requests]
            await asyncio.gather(*tasks)
            print(f"Batch {batch + 1}/{total_batches} completed.")

    # Write the lists of failed packages and error messages to files
    with open('failed_packages.json', 'w') as f:
        json.dump(failed_packages, f, indent=2) 
    with open('error_messages.txt', 'w') as f:
        json.dump(error_messages, f, indent=2)
    
    # Calculate and print the total execution time
    end_time = time.time()
    execution_time = end_time - start_time
    print("Total execution time: " + str(execution_time) + " seconds.")

# Run the main function, starting the asynchronous operation
if __name__ == '__main__':
    asyncio.run(main())
