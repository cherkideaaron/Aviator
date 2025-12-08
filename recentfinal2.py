import sys
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from playwright.async_api import async_playwright

# FORCE WINDOWS TO USE THE CORRECT EVENT LOOP
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI()

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
SELECTOR = "[class*='multiplier']" 
OUTPUT_FILE = "results.txt"

@app.get("/")
async def root():
    return {"message": "Scraper V3. Go to /scrape to start. The tab will load forever (this is normal). Watch your terminal."}

@app.get("/scrape")
async def scrape_aviator():
    print("------------------------------------------------")
    print("STARTING CONTINUOUS SCRAPER... (Press Ctrl+C in terminal to stop)")
    print("------------------------------------------------")

    playwright = await async_playwright().start()
    browser = None
    
    try:
        # ---------------------------------------------------------
        # 1. CONNECT TO CHROME (Do this once)
        # ---------------------------------------------------------
        try:
            browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        except Exception:
            raise HTTPException(status_code=500, detail="Could not find Chrome! Run: chrome.exe --remote-debugging-port=9222")

        context = browser.contexts[0]
        page = None
        
        # Find the correct tab
        for p in context.pages:
            if "2xsport" in p.url or "aviator" in p.url:
                page = p
                print(f"2. Found Game Tab: {page.url}")
                break
        
        if not page:
            if context.pages:
                page = context.pages[0]
                print(f"2. Warning: Using active tab: {page.url}")
            else:
                raise HTTPException(status_code=404, detail="No open tabs found.")

        # ---------------------------------------------------------
        # 2. LOCATE THE FRAME (Do this once)
        # ---------------------------------------------------------
        print("3. Searching for game frame...")
        target_frame = None
        multiplier_element = None

        await asyncio.sleep(1)
        for frame in page.frames:
            try:
                if await frame.locator(SELECTOR).count() > 0:
                    target_frame = frame
                    multiplier_element = frame.locator(SELECTOR).first
                    print(f"    -> FOUND game frame: {frame.url}")
                    break
            except:
                continue
        
        if not target_frame:
            # Fallback search
            for f in page.frames:
                 if "spribe" in f.url or "aviator" in f.url:
                     target_frame = f
                     multiplier_element = f.locator(SELECTOR).first
                     print(f"    -> Inferred game frame: {f.url}")
                     break
            
            if not target_frame:
                raise HTTPException(status_code=404, detail="Could not find game frame.")

        # ---------------------------------------------------------
        # 3. INFINITE MONITORING LOOP
        # ---------------------------------------------------------
        print("4. Locked on. Starting infinite loop...")
        
        # This loop runs forever. It handles finding the round -> reading -> saving -> waiting -> repeating.
        while True:
            # --- PHASE A: WAIT FOR ROUND TO START ---
            # We check if the element exists. If not, we wait.
            print("    [Status] Waiting for round to start...", end="\r")
            
            while True:
                try:
                    if await multiplier_element.count() > 0:
                        # Element appeared! Break this inner loop and start reading
                        break
                except:
                    pass
                # Check every 0.2s as requested
                await asyncio.sleep(0.2)

            # --- PHASE B: MONITOR THE ROUND ---
            last_value = ""
            current_value = ""
            print("\n    [Status] Round Started! Reading values...")

            while True:
                try:
                    # If element disappears suddenly during reading, break to restart
                    if await multiplier_element.count() == 0:
                        break

                    current_value = await multiplier_element.inner_text()
                    
                    # Live print
                    print(f"    Reading: {current_value}      ", end="\r")

                    # CHECK FOR STABILITY (Round End)
                    if current_value == last_value and current_value.strip() != "":
                        # Double check
                        await asyncio.sleep(0.5)
                        try:
                            check_again = await multiplier_element.inner_text()
                        except:
                            check_again = "GONE" # Force a mismatch if it disappeared

                        if check_again == current_value:
                            print(f"\n    -> STABLE: {current_value}")
                            
                            # --- SAVE DATA ---
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            with open(OUTPUT_FILE, "a") as f:
                                f.write(f"[{timestamp}] {current_value}\n")
                            
                            # --- PHASE C: COOLDOWN (YOUR LOGIC) ---
                            print("    [Status] Waiting 7 seconds before searching...")
                            await asyncio.sleep(7.0) # Wait 2 seconds
                            
                            # Now we break out of the "Reading" loop and go back to "Phase A" (Waiting for new round)
                            break 
                    
                    last_value = current_value
                    await asyncio.sleep(0.1) # Fast reads during the round

                except Exception as e:
                    # If something glitches, just break and try to find the element again
                    break
            
            # End of "Phase B" loop, goes back to "Phase A" (Waiting for element)

    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
    finally:
        await playwright.stop()

if __name__ == "__main__":
    import uvicorn
    # TIMEOUT SETTING: We set timeout_keep_alive to a high number so the connection doesn't drop
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=9999)