from twilio.rest import Client

from core.logger import get_logger
log = get_logger()

from dotenv import load_dotenv
load_dotenv()

import os
import time

account_sid = os.getenv('ACCOUNT_SID')
auth_token = os.getenv('AUTH_TOKEN')
site_url = os.getenv('SITE_URL')

full_url = f"{site_url}/voice/"

client = Client(account_sid, auth_token)

def call(to_number):
    log.info(f"Callback executed for {to_number} at {time.strftime('%X')}")
    print(f"{full_url = }")

    call = client.calls.create(
        url=full_url,
        to=to_number,
        from_="+18888545624",
    )