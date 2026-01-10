from scrapers.amazon import get_amazon_product
from scrapers.courses import get_free_courses

if __name__ == "__main__":
    # Test Amazon scraper
    amazon_url = "https://www.amazon.in/dp/B0C9J3Z7FP"
    product = get_amazon_product(amazon_url)

    if product:
        print("Amazon Product:")
        print(product)
    else:
        print("Amazon product not found")

    print("Running free course scraper...")


    # Test free courses scraper
    free_courses_url = "https://www.discudemy.com/all"
    courses = get_free_courses(free_courses_url)

    print(f"Found {len(courses)} free courses")
    for course in courses[:5]:
        print(course)
