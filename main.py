import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from playwright.async_api import async_playwright

app = FastAPI()

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
TARGET_URL = "https://2xsport.com/prematch?slotId=141904" 
SELECTOR = "[class*='multiplier']"
OUTPUT_FILE = "results.txt"

@app.get("/")
async def root():
    return {"message": "Scraper API is running. Go to /scrape?connect_existing=true to start."}

@app.get("/scrape")
async def scrape_last_multiplier(connect_existing: bool = False):
    """
    Launches a browser. 
    If connect_existing=True, it attaches to your open Chrome window (port 9222).
    Otherwise, it opens a new visible window.
    """
    playwright = await async_playwright().start()
    browser = None
    
    try:
        if connect_existing:
            # ---------------------------------------------------------
            # OPTION A: CONNECT TO YOUR RUNNING CHROME
            # Requires Chrome started with: chrome.exe --remote-debugging-port=9222
            # ---------------------------------------------------------
            try:
                print("Attempting to connect to existing Chrome on port 9222...")
                browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
                
                # Get the active context. If you have tabs open, this grabs them.
                context = browser.contexts[0]
                
                if context.pages:
                    # Use the most recently active tab
                    page = context.pages[0] 
                    print(f"Attached to active tab: {page.url}")
                else:
                    page = await context.new_page()
                    await page.goto(TARGET_URL)

            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Could not connect to Chrome. Did you start it with '--remote-debugging-port=9222'? Error: {e}"
                )
        else:
            # ---------------------------------------------------------
            # OPTION B: LAUNCH NEW VISIBLE BROWSER
            # We set headless=False so you can see what is happening
            # ---------------------------------------------------------
            print("Launching new browser...")
            browser = await playwright.chromium.launch(headless=False)
            page = await browser.new_page()
            
            print(f"Navigating to {TARGET_URL}...")
            await page.goto(TARGET_URL)

        # ---------------------------------------------------------
        # COMMON LOGIC
        # ---------------------------------------------------------
        
        # Wait longer (30s) because betting sites can be heavy
        try:
            print("Waiting for multiplier element...")
            await page.wait_for_selector(SELECTOR, timeout=30000)
        except Exception:
            raise HTTPException(status_code=404, detail="Multiplier element not found. If you are not logged in, please log in quickly!")

        print("Element found. Monitoring for changes...")

        last_value = ""
        current_value = ""
        stable_start_time = None
        stability_duration = 2.0  
        max_duration = 120.0 # Increased duration
        
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < max_duration:
            try:
                # Grab the text. We use .first to get the first match.
                element = page.locator(SELECTOR).first
                current_value = await element.inner_text()
            except:
                await asyncio.sleep(0.1)
                continue

            if current_value == last_value and current_value.strip() != "":
                if stable_start_time is None:
                    stable_start_time = datetime.now()
                else:
                    elapsed_stable = (datetime.now() - stable_start_time).total_seconds()
                    if elapsed_stable >= stability_duration:
                        break # Found final value
            else:
                print(f"Value changing: {current_value}")
                last_value = current_value
                stable_start_time = None

            await asyncio.sleep(0.1)

        # ---------------------------------------------------------
        # SAVE RESULTS
        # ---------------------------------------------------------
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        final_data = f"[{timestamp}] Final Value: {last_value}\n"

        with open(OUTPUT_FILE, "a") as f:
            f.write(final_data)

        print(f"Successfully saved: {final_data.strip()}")

        return {
            "status": "success", 
            "timestamp": timestamp, 
            "value": last_value
        }

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Only close the browser if we launched a NEW one. 
        # If we connected to yours, we don't want to kill your window.
        if browser and not connect_existing:
            await browser.close()
        
        # Stop the playwright driver
        await playwright.stop()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)