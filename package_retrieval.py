import aiohttp
import asyncio
import json
import os
import time

directory = "npmDetails/" # where you want JSON files to be stored

BATCH_SIZE = 10000
MAX_RETRIES = 3 # How many times a failed request will be retried
RETRY_DELAY = 0.1  # 100 milliseconds

# Load package names
with open('names.json', 'r') as f:
    names = json.load(f)

num_packages_to_retrieve = len(names)
total_requests = names[:num_packages_to_retrieve]
total_batches = len(total_requests) // BATCH_SIZE + (len(total_requests) % BATCH_SIZE > 0)
failed_packages = []
error_messages = []

def clean_package_name(package_name):
    # Maps npm package name characters to Windows-safe characters.
    cipher = {
        "/": "&=%", 
        "*": "&!=%",
    }
    
    updated_package_name = ''.join(cipher.get(char, char) for char in package_name)
    return updated_package_name

async def retrieve_package_details(session, package_name):
    shared_link = "https://registry.npmjs.org/"
    url = f"{shared_link}{package_name}"
    custom_file_path = os.path.join(directory, clean_package_name(package_name) + ".json")
    for attempt in range(MAX_RETRIES):
        try:
            async with session.get(url) as response:
                if response.status != 200:  # If the status code is not 200 (meaning there has been an error)
                    raise Exception(f"HTTP error {response.status}")
                package_data = json.loads(await response.text())
                json_string = json.dumps(package_data, indent=2)
                with open(custom_file_path, 'w') as f:
                    f.write(json_string)
                return
        except Exception as e:
            if attempt < MAX_RETRIES - 1:  # i.e. if not the last attempt
                await asyncio.sleep(RETRY_DELAY)
            else:
                print(f"Error: {package_name} {e}")
                failed_packages.append(package_name)
                if response.status != 404:
                    error_messages.append(f"{package_name}: {e}") #Log non 404 errors because we want to check those out             

async def main():
    start_time = time.time()
    async with aiohttp.ClientSession() as session:
        for batch in range(total_batches):
            start_index = batch * BATCH_SIZE
            end_index = start_index + BATCH_SIZE
            batch_requests = total_requests[start_index:end_index]
            tasks = [retrieve_package_details(session, name) for name in batch_requests]
            await asyncio.gather(*tasks)
            print(f"Batch {batch + 1}/{total_batches} completed.")

    with open('failed_packages.json', 'w') as f:
        json.dump(failed_packages, f, indent=2) 
    with open('error_messages.txt', 'w') as f:
        json.dump(error_messages, f, indent=2)
    end_time = time.time()
    execution_time = end_time - start_time
    print("Total execution time: " + str(execution_time) + " seconds.")

asyncio.run(main())