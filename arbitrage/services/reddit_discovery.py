import requests
import json
import time
import os

class RedditDiscovery:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def search_subreddits(self, query):
        url = f"https://www.reddit.com/subreddits/search.json?q={query}&limit=50"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                return data.get('data', {}).get('children', [])
            else:
                print(f"Error fetching subreddits: {response.status_code}")
                return []
        except Exception as e:
            print(f"Exception: {e}")
            return []

    def filter_subreddits(self, subreddits):
        valid_subs = []
        for sub in subreddits:
            data = sub['data']
            name = data.get('display_name')
            subscribers = data.get('subscribers', 0)
            submission_type = data.get('submission_type', 'any')
            public_description = data.get('public_description', '').lower()
            description = data.get('description', '').lower()

            # Filter 1: Min subscribers > 50k
            if subscribers <= 50000:
                continue

            # Filter 2: Link or Text posts (usually all public subs allow one or the other)
            # submission_type: 'link', 'self', 'any'
            post_type_allowed = "both"
            if submission_type == 'link':
                post_type_allowed = "link"
            elif submission_type == 'self':
                post_type_allowed = "text"
            
            # Filter 3: Not explicitly banning affiliate links
            # Naive check in description
            banned_keywords = ["no affiliate", "ban affiliate", "no referral", "ban referral"]
            if any(k in public_description for k in banned_keywords) or \
               any(k in description for k in banned_keywords):
                continue
            
            # Basic rules summary (from description)
            rules_summary = data.get('public_description', 'No public description available.')

            valid_subs.append({
                "subreddit_name": name,
                "post_type_allowed": post_type_allowed,
                "rules_summary": rules_summary,
                "subscriber_count": subscribers
            })
        
        return valid_subs

    def run(self, category):
        print(f"Searching for subreddits in category: {category}")
        raw_results = self.search_subreddits(category)
        print(f"Found {len(raw_results)} subreddits. Filtering...")
        filtered = self.filter_subreddits(raw_results)
        
        output_file = f"discovery_{category}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(filtered, f, indent=2)
        
        print(f"Saved {len(filtered)} valid subreddits to {output_file}")
        return filtered

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        category = sys.argv[1]
    else:
        category = "deals" # Default for testing
    
    service = RedditDiscovery()
    service.run(category)
