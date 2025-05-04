import string
import threading
import concurrent.futures
import time
import requests
import json
from bs4 import BeautifulSoup
import random
import yaml

# LOAD COMMON VARIABLES
with open("input\\config.yml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

bearer_token = config.get("bearer_token")
link_network = config.get("link_network")
title = config.get("title")
number_of_threads = config.get("number_of_threads")
number_post = config.get("number_post")
time_sleep_per_post = config.get("time_sleep_per_post")

cookie_file_path = "input\\cookies.txt"
user_file_path = "input\\user.txt"
url_get_info_ads = "https://ads.x.com"
url_get_media = "https://ads.x.com/studio/1/library/list.json"
file_write_lock = threading.Lock()

# CLASS
class Account_X:
    def __init__(self, user_name, cookie, proxy, account_id = None, adsAccountId = None, adsTargetUserId = None):
        self.user_name = user_name
        self.cookie = cookie
        self.proxy = proxy
        self.bearer_token = bearer_token
        self.account_id = account_id
        self.adsAccountId = adsAccountId
        self.ct0 = extract_ct0(cookie)
        self.adsTargetUserId = adsTargetUserId
        self.medias = []
        
# FUNCTIONS
def write_result_to_file(content):
    with file_write_lock:  # Đảm bảo chỉ một luồng ghi vào file tại một thời điểm
        with open("output\\result.txt", "a", encoding="utf-8") as f:
            f.write(content + "\n")

def extract_ct0(cookie_str):
    cookies = cookie_str.split('; ')
    for cookie in cookies:
        if cookie.startswith("ct0="):
            return cookie[len("ct0="):]
    return None  # Trả về None nếu không tìm thấy ct0

def get_account_info(account):
    headers = {
        "Cookie": account.cookie,
    }
    
    params = {
        "ref": "web-btc-24bxcadvertising-gbl-en"
    }

    try:
        response = requests.get(url_get_info_ads, headers=headers, params=params ,proxies=account.proxy, allow_redirects=False)
            
        location = response.headers.get('Location')
        if location:
            url_new = url_get_info_ads + location
            
            response = requests.get(url_new, headers=headers, params=params ,proxies=account.proxy)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")

                # Lấy script chứa dữ liệu JSON
                app_data_script = soup.find("script", {"id": "webaf-app-data"})
                navbar_data_script = soup.find("script", {"id": "webaf-navbar-data"})

                if app_data_script and navbar_data_script:
                    app_data = json.loads(app_data_script.string)
                    navbar_data = json.loads(navbar_data_script.string)

                    # Gán trực tiếp vào account object
                    account.account_id = app_data.get("scribing", {}).get("accountId")
                    account.adsAccountId = app_data.get("adsAccountId")
                    account.adsTargetUserId = navbar_data.get("adsTargetUserId")
                    

                else:
                    print("Không tìm thấy dữ liệu JSON cần thiết trong response.")
                    
                return response.status_code
            else:
                print(f"Error: {response.status_code} - {response.text}")
                return response.status_code
        else:
            print("Không có thông tin chuyển hướng trong response.")
            return response.status_code
    except Exception as e:
        print(f"Lỗi trong quá trình xử lý: {e}")
        return response.status_code
    
def get_list_media(account):
    headers = {
        'accept': '*/*',
        'accept-language': 'en-GB,en;q=0.9,vi-VN;q=0.8,vi;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4',
        'content-type': 'application/json',
        'priority': 'u=1, i',
        'referer': f'https://ads.x.com/accounts/{account.adsAccountId}/media',
        'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'x-csrf-token': account.ct0,
        'Cookie': account.cookie,
    }
    
    params = {
        "account_id" : account.account_id,
        "owner_id" : account.adsTargetUserId,
        "user_id" : account.adsTargetUserId,
        "limit" : 50,
        "offset" : 0,
        "free_text" : "",
        "shared" : False,
        "paginate_by_media_key" : True
    }
    
    # Send request with or without proxy
    response = requests.get(url_get_media, headers=headers, params=params, proxies=account.proxy)

    # Check if the response is successful (status code 200)
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        
        # Initialize an empty list to hold the media keys
        media_keys = []
        
        # Loop through the "results" in the response JSON
        for media in data.get('results', []):
            # Extract the media_key and append to the list
            media_keys.append(media.get('media_key'))
        
        # Assign the list of media_keys to the account object
        account.medias = media_keys
        
    else:
        print(f"Error: Unable to retrieve media data. Status code {response.status_code}")
        
    return response.status_code
        
def post_X(account):
    
    for i in range(number_post):
        url_register_media_ads = f"https://ads-api.x.com/11/accounts/{account.adsAccountId}/cards"
        headers = {
            'accept': '*/*',
            'accept-language': 'en-GB,en;q=0.9,vi-VN;q=0.8,vi;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4',
            'content-type': 'application/json',
            'priority': 'u=1, i',
            'referer': f'https://ads.x.com/accounts/{account.adsAccountId}/media',
            'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'x-csrf-token': account.ct0,
            'Cookie': account.cookie,
            'Authorization': bearer_token,
            'x-origin-environment': 'production'
        }
        name_ads = ''.join(random.choices(string.ascii_uppercase, k=5))
        json_data = {
            "name": name_ads,
            "components": [
                {
                    "media_key": random.choice(account.medias),
                    "type": "MEDIA"
                },
                {
                    "destination": {
                        "type": "WEBSITE",
                        "url": link_network
                    },
                    "title": title,
                    "type": "DETAILS"
                }
            ]
        }
        
        response = requests.post(url_register_media_ads, headers=headers, json=json_data, proxies=account.proxy)
        
        try:
            response.raise_for_status()
            response_json = response.json()
            card_uri = response_json.get("data", {}).get("card_uri")
            
            url_post_ads = f"https://ads-api.x.com/11/accounts/{account.adsAccountId}/tweet"
            
            params = {
                "as_user_id": account.adsTargetUserId,
                "card_uri": card_uri,
                "nullcast": 'false',
                "trim_user": 'false',
                "text": ''.join(random.choices(string.ascii_letters, k=18)),
                "name": name_ads,
            }
            
            response = requests.post(url_post_ads, headers=headers, params=params)
            
            response.raise_for_status()
            response_json = response.json()
            tweet_id = response_json.get("data", {}).get("id_str")
            print("✅ Đăng bài thành công:", tweet_id)
            url_post_ads = f"https://x.com/{account.user_name}/status/{tweet_id}"
            write_result_to_file(url_post_ads)
            
            time.sleep(time_sleep_per_post)
            
        except Exception as e:
            print("❌ Error fetching card_uri:", e)
            print("Response content:", response.text)
            return response.status_code
    return 200
    
def process_account(account: Account_X):
    try:
        status = get_account_info(account)
        if status != 200:
            raise Exception(f"Failed to get account info for {account.user_name}, status code: {status}")
        status = get_list_media(account)
        if status != 200 and status != 201:
            raise Exception(f"Failed to get media list for {account.user_name}, status code: {status}")
        status = post_X(account)
        if status != 200 and status != 201:
            raise Exception(f"Failed to post for {account.user_name}, status code: {status}")
    except Exception as e:
        with file_write_lock:
            print(f"Error for {account.user_name}: {e}")
            with open("output\\error_log.txt", "a", encoding="utf-8") as f:
                f.write(f"{account.user_name}\n")
    
# xử lí main
# Đọc dữ liệu từ file
accounts = []
with open(user_file_path, 'r', encoding='utf-8') as user_file, open(cookie_file_path, 'r', encoding='utf-8') as cookie_file:
    user_lines = user_file.readlines()
    cookie_lines = cookie_file.readlines()

    if len(user_lines) != len(cookie_lines):
        print("Số lượng username và cookie không khớp nhau.")
        exit(1)

    for user_line, cookie_line in zip(user_lines, cookie_lines):
        parts = user_line.strip().split("|")
        user_name = parts[0]
        proxy = None

        if len(parts) > 1:
            proxy_parts = parts[1].split(":")
            if len(proxy_parts) == 4:
                ip, port, user, pwd = proxy_parts
                proxy_url = f"http://{user}:{pwd}@{ip}:{port}"
                proxy = {
                    "http": proxy_url,
                    "https": proxy_url
                }

        cookie = cookie_line.strip()
        account = Account_X(user_name=user_name, cookie=cookie, proxy=proxy)
        accounts.append(account)
        
# Dùng ThreadPoolExecutor để xử lý đa luồng
with concurrent.futures.ThreadPoolExecutor(max_workers=number_of_threads) as executor:
    executor.map(process_account, accounts)
