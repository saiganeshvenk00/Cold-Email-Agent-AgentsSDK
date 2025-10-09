"""
Test script to verify the /incoming-reply webhook is accessible.
Run this to test both locally and on production.
"""
import requests
import json

# Test data
test_payload = {
    "from": "test@example.com",
    "subject": "Test Reply",
    "text": "This is a test reply to verify the webhook is working.",
    "message_id": "<test-123@example.com>",
    "headers": {
        "Message-ID": "<test-123@example.com>"
    }
}

def test_webhook(base_url):
    """Test the /incoming-reply webhook endpoint."""
    url = f"{base_url}/incoming-reply"
    print(f"\n🔍 Testing webhook at: {url}")
    print(f"📤 Sending test payload...")
    
    try:
        response = requests.post(
            url,
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"✅ Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ Response: {json.dumps(response.json(), indent=2)}")
            print("\n✅ WEBHOOK IS WORKING!")
            return True
        else:
            print(f"❌ Response: {response.text}")
            print("\n❌ WEBHOOK RETURNED ERROR")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error - Server not running or not accessible")
        return False
    except requests.exceptions.Timeout:
        print("❌ Timeout - Server took too long to respond")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 WEBHOOK ENDPOINT TEST")
    print("=" * 60)
    
    # Test local
    print("\n1️⃣  Testing LOCAL server...")
    local_success = test_webhook("http://localhost:8000")
    
    # Test production
    print("\n2️⃣  Testing PRODUCTION server...")
    prod_success = test_webhook("https://cold-email-agent-agentssdk.onrender.com")
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)
    print(f"Local:      {'✅ PASS' if local_success else '❌ FAIL'}")
    print(f"Production: {'✅ PASS' if prod_success else '❌ FAIL'}")
    print("=" * 60)
    
    if prod_success:
        print("\n🎉 Production webhook is accessible and working!")
        print("📝 Next steps:")
        print("   1. Configure SendGrid Inbound Parse:")
        print("      https://app.sendgrid.com/settings/parse")
        print("   2. Set destination URL to:")
        print("      https://cold-email-agent-agentssdk.onrender.com/incoming-reply")
        print("   3. Open the web UI and watch the Activity log!")
    else:
        print("\n⚠️  Production webhook is not accessible yet.")
        print("   Wait 2-3 minutes for Render to rebuild and deploy.")
        print("   Then run this test again.")
