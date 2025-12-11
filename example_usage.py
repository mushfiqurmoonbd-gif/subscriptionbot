"""
Example usage of the Subscription Service Bot API
"""

import requests
from datetime import datetime, timedelta

# Base URL for the API
BASE_URL = "http://localhost:5000/api"

def example_subscribe():
    """Example: Subscribe a new user"""
    response = requests.post(f"{BASE_URL}/subscribe", json={
        "phone_number": "1234567890",
        "carrier": "boost",  # Use 'boost' for Boost Mobile
        "email": "user@example.com",
        "name": "John Doe"
    })
    print("Subscribe Response:", response.json())
    return response.json()

def example_get_carriers():
    """Example: Get list of available carriers"""
    response = requests.get(f"{BASE_URL}/carriers")
    print("Available Carriers:", response.json())
    return response.json()

def example_send_sms(subscriber_id, message):
    """Example: Send immediate SMS to subscriber"""
    response = requests.post(
        f"{BASE_URL}/subscribers/{subscriber_id}/send-sms",
        json={"message": message}
    )
    print("Send SMS Response:", response.json())
    return response.json()

def example_schedule_message(subscriber_id, message, hours_from_now=24):
    """Example: Schedule a message for later"""
    scheduled_time = (datetime.utcnow() + timedelta(hours=hours_from_now)).isoformat() + "Z"
    
    response = requests.post(
        f"{BASE_URL}/subscribers/{subscriber_id}/schedule-message",
        json={
            "message": message,
            "scheduled_time": scheduled_time
        }
    )
    print("Schedule Message Response:", response.json())
    return response.json()

def example_get_subscribers():
    """Example: Get all subscribers"""
    response = requests.get(f"{BASE_URL}/subscribers")
    print("Subscribers:", response.json())
    return response.json()

if __name__ == "__main__":
    print("=== Subscription Service Bot Examples ===\n")
    
    # 1. Get available carriers
    print("1. Getting available carriers...")
    carriers = example_get_carriers()
    print()
    
    # 2. Subscribe a new user
    print("2. Subscribing a new user...")
    subscriber_data = example_subscribe()
    subscriber_id = subscriber_data.get('subscriber', {}).get('id')
    print()
    
    if subscriber_id:
        # 3. Send immediate SMS
        print("3. Sending immediate SMS...")
        example_send_sms(subscriber_id, "Welcome to our service! This is a test message.")
        print()
        
        # 4. Schedule a message for 24 hours from now
        print("4. Scheduling a message...")
        example_schedule_message(
            subscriber_id,
            "This is your scheduled reminder message!",
            hours_from_now=24
        )
        print()
    
    # 5. Get all subscribers
    print("5. Getting all subscribers...")
    example_get_subscribers()

