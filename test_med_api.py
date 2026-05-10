import requests
import time
import json
from urllib.parse import urlparse


ENDPOINT = "http://100.51.212.220:8000/generate"
API_KEY  = "REMOVED"

text = """السلام عليكم.
أعاني من ألم في الصدر من الجهة اليسار ومنتصف الصدر، عمري 39 عاما، وأنا مدخن وعصبي، أجريت تخطيطا وجهدا للقلب، وصورة إيكو أيضا، ولم يظهر معي شيء، راجعت دكتور الهضمية، وبعد تحليل البراز ظهر معي جرثومة في المعدة، فهل من الممكن أن تسبب ألما في الصدر جهة القلب، وتعبا سريعا بعد جهد خفيف؟"""
print("Sending request to model...")
resp = requests.post(
    ENDPOINT,
    headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
    json={"text": text},
    timeout=300
)

if resp.status_code == 200:
    data = resp.json()
    poll_url = data.get("poll_url")
    
    if poll_url:
        parsed_url = urlparse(ENDPOINT)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        full_poll_url = f"{base_url}{poll_url}"
        
        print(f"Job queued. Polling for results...")
        while True:
            poll_resp = requests.get(full_poll_url, headers={"X-API-Key": API_KEY})
            if poll_resp.status_code == 200:
                poll_data = poll_resp.json()
                status = poll_data.get("status")
                
                if status == "completed":
                    print("\n\n--- Analysis Result ---")
                    result = poll_data.get("result")
                    if isinstance(result, (dict, list)):
                        print(json.dumps(result, indent=2, ensure_ascii=False))
                    else:
                        print(result)
                    break
                elif status == "failed":
                    print("\n\nJob failed.")
                    print(json.dumps(poll_data, indent=2))
                    break
                else:
                    # Still processing
                    print(".", end="", flush=True)
            else:
                print(f"\nError polling (HTTP {poll_resp.status_code}):")
                print(poll_resp.text)
                break
            time.sleep(1)
    else:
        print("Success, but no poll_url found in response:")
        print(json.dumps(data, indent=2))
else:
    print(f"Error: HTTP {resp.status_code}")
    print(resp.text)