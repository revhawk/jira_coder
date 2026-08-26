"""
Test script to verify Jira and GitHub API connections.
Run this to ensure your .env configuration is correct.
"""

import requests
from requests.auth import HTTPBasicAuth
from config.settings import Settings

def test_jira_connection():
    """Test Jira API connection and authentication."""
    print("\n🔍 Testing Jira Connection...")
    print(f"   URL: {Settings.JIRA_BASE}")
    
    try:
        # Test endpoint: Get current user info
        url = f"{Settings.JIRA_BASE}/rest/api/3/myself"
        auth = HTTPBasicAuth(Settings.JIRA_EMAIL, Settings.JIRA_API_TOKEN)
        
        response = requests.get(url, auth=auth, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"   ✅ Connected successfully!")
            print(f"   👤 Logged in as: {user_data.get('displayName')} ({user_data.get('emailAddress')})")
            print(f"   🆔 Account ID: {user_data.get('accountId')}")
            return True
        else:
            print(f"   ❌ Connection failed!")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Connection error: {e}")
        return False


def test_github_connection():
    """Test GitHub API connection and authentication."""
    print("\n🔍 Testing GitHub Connection...")
    print(f"   Repository: {Settings.GITHUB_REPO}")
    
    try:
        # Test endpoint: Get authenticated user
        url = "https://api.github.com/user"
        headers = {
            "Authorization": f"Bearer {Settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"   ✅ Connected successfully!")
            print(f"   👤 Logged in as: {user_data.get('login')} ({user_data.get('name')})")
            print(f"   📧 Email: {user_data.get('email', 'Not public')}")
            
            # Test repository access
            repo_url = f"https://api.github.com/repos/{Settings.GITHUB_REPO}"
            repo_response = requests.get(repo_url, headers=headers, timeout=10)
            
            if repo_response.status_code == 200:
                repo_data = repo_response.json()
                print(f"   📦 Repository access: ✅")
                print(f"   🔓 Visibility: {repo_data.get('visibility', 'unknown')}")
                print(f"   ⭐ Stars: {repo_data.get('stargazers_count', 0)}")
            else:
                print(f"   ⚠️  Repository access: Limited or not found")
                print(f"   Status Code: {repo_response.status_code}")
            
            return True
        else:
            print(f"   ❌ Connection failed!")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Connection error: {e}")
        return False


def test_openai_connection():
    """Test OpenAI API connection."""
    print("\n🔍 Testing OpenAI Connection...")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=Settings.OPENAI_API_KEY)
        
        # Make a simple API call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'API test successful' and nothing else."}],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        print(f"   ✅ Connected successfully!")
        print(f"   🤖 Response: {result}")
        return True
        
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False


def test_groq_connection():
    """Test Groq API connection with Qwen model."""
    print("\n🔍 Testing Groq (Qwen) Connection...")
    try:
        from groq import Groq
        client = Groq(api_key=Settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[{"role": "user", "content": "Say 'API test successful' and nothing else."}],
            temperature=0.6,
            max_completion_tokens=64,
            top_p=0.95,
            reasoning_effort="default",
            stream=True,
            stop=None
        )
        result = ""
        for chunk in completion:
            result += chunk.choices[0].delta.content or ""
        print(f"   ✅ Connected successfully!")
        print(f"   🤖 Response: {result}")
        return True
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False

def test_anthropic_connection():
    """Test Anthropic API connection."""
    print("\n🔍 Testing Anthropic Connection...")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=Settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=32,
            messages=[{"role": "user", "content": "Say 'API test successful' and nothing else."}]
        )
        result = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content)
        print(f"   ✅ Connected successfully!")
        print(f"   🤖 Response: {result}")
        return True
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False

def test_gemini_connection():
    """Test Gemini API connection and list available models."""
    print("\n🔍 Testing Gemini Connection...")
    try:
        import google.generativeai as genai
        genai.configure(api_key=Settings.GEMINI_API_KEY)
        #print("   📋 Listing available Gemini models:")
        #models = genai.list_models()
        #for m in models:
        #    print(f"   - {getattr(m, 'name', m)}")
        # Try to use a common free model (update as needed)
        model_name = "models/gemini-2.5-pro" # Change this if another model is available
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say 'API test successful' and nothing else.")
        result = response.text if hasattr(response, 'text') else str(response)
        print(f"   ✅ Connected successfully!")
        print(f"   🤖 Response: {result}")
        return True
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False


def main():
    """Run all connection tests."""
    print("=" * 60)
    print("🧪 API Connection Tests")
    print("=" * 60)
    
    # Verify settings loaded
    try:
        Settings.check()
    except EnvironmentError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("Please check your .env file and try again.")
        return
    
    # Run tests
    results = {
        "Jira": test_jira_connection(),
        "GitHub": test_github_connection(),
        "OpenAI": test_openai_connection(),
        "Groq (Qwen)": test_groq_connection(),
        # "Anthropic": test_anthropic_connection(),  # Temporarily commented out due to lack of credits
        "Gemini": test_gemini_connection()
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    for service, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {service}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All connections successful! You're ready to go!")
    else:
        print("\n⚠️  Some connections failed. Please check the errors above.")
    
    print("=" * 60)

    #print("GROQ_API_KEY:", Settings.GROQ_API_KEY)
    #print("ANTHROPIC_API_KEY:", Settings.ANTHROPIC_API_KEY)
    #print("GEMINI_API_KEY:", Settings.GEMINI_API_KEY)


if __name__ == "__main__":
    main()