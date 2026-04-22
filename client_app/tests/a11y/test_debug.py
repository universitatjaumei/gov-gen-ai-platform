from nicegui.testing import User

async def test_debug_user(user: User):
    await user.open('/')
    try:
        url = await user.run_javascript('return window.location.href')
        print(f"DEBUG_JS_URL: {url}")
    except Exception as e:
        print(f"DEBUG_JS_ERROR: {e}")
        
    try:
        # Check for driver
        if hasattr(user, 'driver'):
            print(f"DEBUG_DRIVER: {user.driver}")
            print(f"DEBUG_DRIVER_URL: {user.driver.current_url}")
    except Exception as e:
        print(f"DEBUG_DRIVER_ERROR: {e}")
