import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# URL of the webpage
url = "https://www.jutecomm.gov.in/Supply_Distribution_Position_of_Raw_Jute.html"

# Function to scrape jute data
def scrape_jute_data(url):
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()  # Ensure valid response

        soup = BeautifulSoup(response.text, "html.parser")

        # Find all tables on the page
        tables = soup.find_all("table")

        if not tables:
            print("No tables found on the page.")
            return None

        # Select the first table
        table = tables[0]
        
        # Extract all rows
        rows = table.find_all("tr")

        # Extract headers
        headers = [th.text.strip() for th in rows[0].find_all(["th", "td"])]
        print(f"Extracted Headers: {headers}")

        data = []
        for row in rows[1:]:  # Skip header row
            cols = row.find_all("td")
            cols = [col.text.strip() if col.text.strip() != "--" else "0" for col in cols]  # Replace "--" with 0

            # Ensure row matches header count (Adjust dynamically)
            if len(cols) < len(headers):
                cols += [""] * (len(headers) - len(cols))  # Fill missing values with empty strings
            elif len(cols) > len(headers):
                cols = cols[:len(headers)]  # Trim extra values

            data.append(cols)

        # Convert to DataFrame
        df = pd.DataFrame(data, columns=headers)

        return df

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

# Scrape the data
jute_df = scrape_jute_data(url)

if jute_df is not None and not jute_df.empty:
    # Save to JSON file
    jute_data = jute_df.to_dict(orient="records")
    with open("jute_data.json", "w") as f:
        json.dump(jute_data, f, indent=4)

    print("Data extracted and saved to jute_data.json")
    print(jute_df.head())  # Print first few rows for verification
else:
    print("No data extracted.")
