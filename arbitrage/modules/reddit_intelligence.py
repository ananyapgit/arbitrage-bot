import json
import os
import sys
import argparse
import random

# Ensure we can import from parent directory if run as script
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from arbitrage.utils.reddit_compliance import RedditCompliance

class RedditIntelligence:
    def __init__(self):
        self.compliance_checker = RedditCompliance()
        self.db_file = "subreddit_db.json"

    def analyze_subreddits(self, subreddits):
        results = []
        print(f"{'Subreddit':<20} | {'Score':<5} | {'Class':<10} | {'Reasoning'}")
        print("-" * 80)

        for sub in subreddits:
            sub = sub.strip()
            if not sub:
                continue
                
            compliance = self.compliance_checker.check_compliance(sub)
            analysis = self.calculate_score(compliance)
            
            # Generate content if safe/caution
            if analysis['classification'] in ['safe', 'caution']:
                analysis['content_templates'] = self.generate_content_templates(sub)
            else:
                analysis['content_templates'] = None

            results.append(analysis)
            
            # Print row
            reasoning_short = analysis['reasoning'][:40] + "..." if len(analysis['reasoning']) > 40 else analysis['reasoning']
            print(f"{sub:<20} | {analysis['score']:<5} | {analysis['classification']:<10} | {reasoning_short}")

        self.save_results(results)
        return results

    def calculate_score(self, compliance):
        score = 100
        reasons = []

        # Affiliate check
        if compliance['affiliate_allowed'] == 'no':
            score = 0
            reasons.append("Affiliate banned")
        elif compliance['affiliate_allowed'] == 'unclear':
            score -= 30
            reasons.append("Affiliate unclear (-30)")
        
        # Link post check
        if compliance['link_post_allowed'] == 'no':
            score -= 40
            reasons.append("No link posts (-40)")
            
        # Frequency limit
        if compliance['frequency_limit'] is not None:
            score -= 10
            reasons.append(f"Freq limit: {compliance['frequency_limit']} (-10)")
            
        # Strict moderation (rule count)
        if compliance.get('rule_count', 0) > 10:
            score -= 10
            reasons.append(f"Strict rules ({compliance['rule_count']}) (-10)")

        # Ensure score doesn't go below 0 if not already 0'd by ban
        if score < 0:
            score = 0

        # Classification
        if score >= 70:
            classification = "safe"
        elif score >= 40:
            classification = "caution"
        else:
            classification = "avoid"

        return {
            "subreddit_name": compliance['subreddit_name'],
            "score": score,
            "classification": classification,
            "reasoning": ", ".join(reasons) if reasons else "Looks good",
            "rules_summary": compliance.get('rules_summary', []),
            "details": compliance
        }

    def generate_content_templates(self, subreddit):
        """
        Generates neutral, non-promotional content templates.
        """
        titles = [
            "Price drop on {product_name}",
            "Found this deal on {product_name}",
            "Is this a good price for {product_name}?",
            "{product_name} currently at {price}",
            "Saw {product_name} on sale today"
        ]
        
        comments = [
            "Saw this while browsing today. Thought I'd share in case anyone is looking.",
            "Noticed this price drop. Not affiliated, just sharing.",
            "Seems like a decent deal compared to usual prices."
        ]
        
        return {
            "titles": titles,
            "comments": comments
        }

    def save_results(self, results):
        # Save to project root
        root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        file_path = os.path.join(root_path, self.db_file)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved analysis of {len(results)} subreddits to {file_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reddit Intelligence Layer")
    parser.add_argument("subreddits", nargs="*", help="List of subreddits to analyze")
    parser.add_argument("--file", "-f", help="Text file containing subreddit names (one per line)")
    
    args = parser.parse_args()
    
    subs_to_check = []
    if args.subreddits:
        subs_to_check.extend(args.subreddits)
    
    if args.file:
        try:
            with open(args.file, 'r') as f:
                subs_to_check.extend([line.strip() for line in f.readlines() if line.strip()])
        except Exception as e:
            print(f"Error reading file: {e}")

    if not subs_to_check:
        print("Usage: python reddit_intelligence.py [sub1 sub2 ...] OR --file subs.txt")
        print("No input provided. Running test on ['deals', 'buildapcsales', 'videos']...")
        subs_to_check = ['deals', 'buildapcsales', 'videos']

    intelligence = RedditIntelligence()
    intelligence.analyze_subreddits(subs_to_check)
