import requests
import json
import re

class RedditCompliance:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_subreddit_rules(self, subreddit_name):
        url = f"https://www.reddit.com/r/{subreddit_name}/about/rules.json"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None

    def get_subreddit_about(self, subreddit_name):
        url = f"https://www.reddit.com/r/{subreddit_name}/about.json"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None

    def check_compliance(self, subreddit_name):
        rules_data = self.get_subreddit_rules(subreddit_name)
        about_data = self.get_subreddit_about(subreddit_name)
        
        affiliate_allowed = "unclear"
        link_post_allowed = "no"
        frequency_limit = None
        
        # Check link posts from about
        if about_data and 'data' in about_data:
            submission_type = about_data['data'].get('submission_type', 'any')
            if submission_type in ['link', 'any']:
                link_post_allowed = "yes"
        
        # Check rules for affiliate keywords
        rules_list = []
        if rules_data:
            rules_list = rules_data.get('rules', [])
        
        rule_count = len(rules_list)

        for rule in rules_list:
            desc = (rule.get('description') or "") + " " + (rule.get('short_name') or "")
            desc_lower = desc.lower()
            
            # Affiliate check
            if "affiliate" in desc_lower or "referral" in desc_lower:
                if "no " in desc_lower or "ban" in desc_lower or "forbidden" in desc_lower or "don't" in desc_lower or "do not" in desc_lower:
                    affiliate_allowed = "no"
                elif "allowed" in desc_lower:
                    affiliate_allowed = "yes"
            
            # Frequency check
            if "post" in desc_lower and ("limit" in desc_lower or "day" in desc_lower or "week" in desc_lower or "hour" in desc_lower):
                # Try to extract a number
                # Matches "1 post per day", "3 posts every 24 hours", "limit of 2 posts"
                match = re.search(r'(\d+)\s+posts?', desc_lower)
                if match:
                    try:
                        frequency_limit = int(match.group(1))
                    except:
                        pass
                
                # If regex fails but rule exists, default to something or keep as None if not explicitly a number
                # The user asked for "integer or null". If we can't parse an int, maybe just don't set it or set a safe default.
                # However, if we found "limit" but no number, it's risky.
                # Let's try another regex for "limit of X"
                if frequency_limit is None:
                    match = re.search(r'limit\s+of\s+(\d+)', desc_lower)
                    if match:
                        frequency_limit = int(match.group(1))

        return {
            "subreddit_name": subreddit_name,
            "affiliate_allowed": affiliate_allowed,
            "link_post_allowed": link_post_allowed,
            "frequency_limit": frequency_limit,
            "rule_count": rule_count,
            "rules_summary": [r.get('short_name') for r in rules_list]
        }

if __name__ == "__main__":
    import sys
    sub = sys.argv[1] if len(sys.argv) > 1 else "deals"
    checker = RedditCompliance()
    result = checker.check_compliance(sub)
    print(json.dumps(result, indent=2))
