import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import smtplib
from email.message import EmailMessage
import requests

CLIENT_ID = ""
CLIENT_SECRET = ""

# Email configuration
SMTP_SERVER = ""
SMTP_PORT =
SMTP_USER = ""
SMTP_PASSWORD = ""
RECIPIENT = ""

QUERIES = []
# URL of the *raw* file on GitHub
url = "https://raw.githubusercontent.com/flockhost/ebaypy/refs/heads/main/queries.txt"

response = requests.get(url)
response.raise_for_status()  # ensures an error is raised for bad responses

# Split into a list of lines
QUERIES = response.text.splitlines()

print(QUERIES)

def get_oauth_token():
    url = "https://api.ebay.com/identity/v1/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope"
    }

    response = requests.post(url, headers=headers, data=data,
                             auth=(CLIENT_ID, CLIENT_SECRET))
    response.raise_for_status()
    return response.json()["access_token"]

def send_email(subject, body):
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = RECIPIENT
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(msg)

def search_ebay_browse(query, token):
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    filters = [
        "buyingOptions:{AUCTION}",
        "price:[0..1[",
        "priceCurrency:EUR",
        "deliveryCountry:DE"
        #,"category_ids:{25619}" # Toys & Hobbies → Games → Board & Traditional Games
    ]

    params = {
        "q": query,
        "filter": ",".join(filters),
        "limit": 100
    }

    headers = {"Authorization": f"Bearer {token}"
        ,"X-EBAY-C-MARKETPLACE-ID": "EBAY_DE"
               }

    print("Fetching:", url)
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    #print(response.json())
    return response.json().get("itemSummaries", [])


def extract_price(item):
    if "price" in item:
        return float(item["price"]["value"])
    if "currentBidPrice" in item:
        return float(item["currentBidPrice"]["value"])
    if "minimumPrice" in item:
        return float(item["minimumPrice"]["value"])
    return None


def filter_items(items):
    results = []
    #now = datetime.now(timezone.utc)
    now = datetime.now(ZoneInfo("Europe/Berlin"))
    cutoff = now + timedelta(hours=24)

    for item in items:
        price = extract_price(item)
        if price is None:
            continue

        shipping = float(item.get("shippingOptions", [{}])[0]
                         .get("shippingCost", {"value": 999})["value"])

        bids = item.get("bidCount", 0)

        end_time = datetime.fromisoformat(
            item["itemEndDate"] #.replace("Z", "+00:00")
        )

        if price <= 1 and bids <= 1 and shipping <= 7 and end_time <= cutoff:
            print(item["itemEndDate"])
            results.append({
                "title": item["title"] + ("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" if end_time <= now + timedelta(hours=3) else ""),
                "price": price,
                "bids": bids,
                "shipping": shipping,
                #"end_time": end_time,
                "end_time": end_time.astimezone(ZoneInfo("Europe/Berlin")),
                "url": item["itemWebUrl"]
            })
        results.sort(key=lambda x: x["end_time"])

    return results



def main():
    email_body = ""
    token = get_oauth_token()

    for query in QUERIES:
        print(f"\n🔍 Searching for: {query}")
        items = search_ebay_browse(query, token)
        filtered = filter_items(items)

        if not filtered:
            print("No matching auctions found.")
            continue

        for item in filtered:
            print("\n---------------------------")
            print(f"Title: {item['title']}")
            print(f"Price: {item['price']} €")
            print(f"Bids: {item['bids']}")
            print(f"Shipping: {item['shipping']} €")
            print(f"Ends: {item['end_time']}")
            print(f"Item URL: {item['url']}")
            print("---------------------------")
            email_body += (
                "\n---------------------------\n"
                f"Title: {item['title']}\n"
                f"Price: {item['price']} €\n"
                f"Bids: {item['bids']}\n"
                f"Shipping: {item['shipping']} €\n"
                f"Ends: {item['end_time']}\n"
                f"Item URL: {item['url']}\n"
            )

        send_email("eBay Auction Results " + query, email_body)
        email_body = ""
        print("Email sent to Andre.")


if __name__ == "__main__":
    main()
