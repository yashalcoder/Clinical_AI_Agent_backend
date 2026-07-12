import httpx
from app.core.config import settings

# Google OAuth URLs
GOOGLE_AUTH_URL     = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL    = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def get_google_auth_url(state: str) -> str:
    """
    Google login page ka URL banao
    User yahan jaayega jab 'Login with Google' click kare
    
    state = CSRF attack rokne ke liye random string
    """
    params = {
        "client_id":     settings.GOOGLE_CLIENT_ID,
        "redirect_uri":  settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         "openid email profile",
        "state":         state,
        "access_type":   "offline",  # refresh token bhi milega
        "prompt":        "select_account",  # har baar account select kare
    }

    # URL banao with params
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query_string}"


async def exchange_code_for_token(code: str) -> dict:
    """
    Google se code milta hai callback pe
    Yeh code access_token se exchange karo
    
    code → Google server → access_token
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code":          code,
                "client_id":     settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri":  settings.GOOGLE_REDIRECT_URI,
                "grant_type":    "authorization_code",
            }
        )

    if response.status_code != 200:
        raise Exception(f"Token exchange failed: {response.text}")

    return response.json()


async def get_google_user_info(access_token: str) -> dict:
    """
    access_token se Google user ki info lo
    Returns: {email, name, picture, sub (google_id)}
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )

    if response.status_code != 200:
        raise Exception(f"Failed to get user info: {response.text}")

    data = response.json()

    # Sirf humari zaroorat ka data return karo
    return {
        "google_id":    data.get("sub"),       # Google ka unique user ID
        "email":        data.get("email"),
        "full_name":    data.get("name"),
        "picture":      data.get("picture"),   # profile photo URL
        "email_verified": data.get("email_verified", False)
    }