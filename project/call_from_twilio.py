# # Download the helper library from https://www.twilio.com/docs/python/install
# import os
# from twilio.rest import Client

# # Find your Account SID and Auth Token at twilio.com/console
# # and set the environment variables. See http://twil.io/secure
# account_sid = "AC2f76d049dba022f5cff127fe816971a5"
# auth_token = "e821a669a756801ad5e111a32779db5e"
# client = Client(account_sid, auth_token)

# call = client.calls.create(
#     twiml="<Response><Say>Ahoy, World!</Say></Response>",
#     to="+919021131499",
#     from_="+18888545624",
# )

# print(call.sid)


from twilio.rest import Client

account_sid = "AC2f76d049dba022f5cff127fe816971a5"
auth_token = "e821a669a756801ad5e111a32779db5e"

client = Client(account_sid, auth_token)

call = client.calls.create(
    twiml='<Response><Say>Hi, this is a test</Say></Response>',  # OR use 'url'
    # url='https://thekingofmemphis-rp.com/voice', 
    url='https://a726d43e3c70.ngrok-free.app/voice',
    to="+919021131499",
    from_="+18888545624",
)

# print("Call SID:", call.sid)



