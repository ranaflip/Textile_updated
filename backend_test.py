import requests
import unittest
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')

# Get the backend URL from environment variables
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL')
API_URL = f"{BACKEND_URL}/api"

class WebScraperAPITest(unittest.TestCase):
    """Test suite for the Web Scraper API"""

    def setUp(self):
        """Setup for each test"""
        self.test_urls = [
            "https://httpbin.org/html",
            "https://quotes.toscrape.com/",
            "https://books.toscrape.com/"
        ]
        self.job_id = None

    def test_01_root_endpoint(self):
        """Test the root API endpoint"""
        print("\n🔍 Testing root endpoint...")
        response = requests.get(f"{API_URL}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("version", data)
        print("✅ Root endpoint test passed")

    def test_02_create_scraping_job(self):
        """Test creating a new scraping job"""
        print("\n🔍 Testing job creation...")
        payload = {"urls": self.test_urls}
        response = requests.post(f"{API_URL}/scrape", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["total_urls"], len(self.test_urls))
        self.assertEqual(data["processed_urls"], 0)
        
        # Save job ID for subsequent tests
        WebScraperAPITest.job_id = data["id"]
        print(f"✅ Job creation test passed - Job ID: {WebScraperAPITest.job_id}")

    def test_03_get_jobs_list(self):
        """Test getting the list of scraping jobs"""
        print("\n🔍 Testing jobs list retrieval...")
        response = requests.get(f"{API_URL}/jobs")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        
        # Check if our created job is in the list
        if WebScraperAPITest.job_id:
            job_ids = [job["id"] for job in data]
            self.assertIn(WebScraperAPITest.job_id, job_ids)
        print("✅ Jobs list retrieval test passed")

    def test_04_get_specific_job(self):
        """Test getting a specific job by ID"""
        if not WebScraperAPITest.job_id:
            self.skipTest("No job ID available from previous test")
        
        print(f"\n🔍 Testing specific job retrieval for job ID: {WebScraperAPITest.job_id}...")
        response = requests.get(f"{API_URL}/jobs/{WebScraperAPITest.job_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], WebScraperAPITest.job_id)
        print("✅ Specific job retrieval test passed")

    def test_05_wait_for_job_completion(self):
        """Wait for the job to complete and check results"""
        if not WebScraperAPITest.job_id:
            self.skipTest("No job ID available from previous test")
        
        print(f"\n🔍 Waiting for job {WebScraperAPITest.job_id} to complete...")
        max_wait_time = 60  # Maximum wait time in seconds
        wait_interval = 5   # Check interval in seconds
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            response = requests.get(f"{API_URL}/jobs/{WebScraperAPITest.job_id}")
            data = response.json()
            
            if data["status"] in ["completed", "failed"]:
                print(f"Job status: {data['status']}")
                break
                
            print(f"Current status: {data['status']} - Processed: {data['processed_urls']}/{data['total_urls']}")
            time.sleep(wait_interval)
            elapsed_time += wait_interval
        
        # Check if job completed or is still in progress
        self.assertIn(data["status"], ["completed", "in_progress", "failed"])
        
        # If job completed, check results
        if data["status"] == "completed":
            print("✅ Job completed successfully")
            self.assertEqual(data["processed_urls"], data["total_urls"])
        elif data["status"] == "in_progress":
            print("⚠️ Job still in progress after wait time - continuing tests")
        else:
            print(f"⚠️ Job failed with error: {data.get('error_message', 'Unknown error')}")

    def test_06_get_job_results(self):
        """Test getting the results for a specific job"""
        if not WebScraperAPITest.job_id:
            self.skipTest("No job ID available from previous test")
        
        print(f"\n🔍 Testing job results retrieval for job ID: {WebScraperAPITest.job_id}...")
        response = requests.get(f"{API_URL}/jobs/{WebScraperAPITest.job_id}/results")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        
        # Print summary of results
        print(f"Retrieved {len(data)} result(s)")
        for i, result in enumerate(data):
            print(f"Result {i+1}: URL={result['url']}")
            if result.get('error'):
                print(f"  Error: {result['error']}")
            else:
                print(f"  Title: {result.get('title', 'No title')}")
                print(f"  Tables: {len(result.get('tables', []))}")
                print(f"  Items: {len(result.get('items', []))}")
                print(f"  Prices: {len(result.get('prices', []))}")
        
        print("✅ Job results retrieval test passed")

def run_tests():
    """Run the test suite"""
    print(f"🧪 Testing Web Scraper API at {API_URL}")
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

if __name__ == "__main__":
    run_tests()