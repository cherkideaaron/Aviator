(function () {
    console.log("%c 🛰 VAULT ACTIVE: Routing data to Local Python Server", "color: #3498db; font-weight: bold;");

    let lastValue = "";
    // The URL of your local Python server
    const API_URL = "http://127.0.0.1:5000/save";

    /**
     * Finds the balance by filtering for numerical strings only,
     * avoiding elements like clocks (09:25) or UI labels.
     */
    const getBalance = () => {
        const frames = [window, ...Array.from(window.frames)];
        for (let frame of frames) {
            try {
                // Select all spans that match the common UI classes for the balance
                const elements = frame.document.querySelectorAll("span[class*='_size-14_'], span[class*='_container_1p5jb_']");
                
                for (let el of elements) {
                    const text = el.innerText.trim();
                    
                    // Validation: Only return if the text is strictly numbers and dots (e.g., 2.91)
                    // This prevents the script from accidentally grabbing the time (09:25)
                    if (/^[0-9.]+$/.test(text) && text !== "") {
                        return text;
                    }
                }
            } catch (e) {
                // Handle cross-origin frame errors silently
            }
        }
        return "0.00";
    };

    /**
     * Sends the collected data to your Python Flask/FastAPI backend
     */
    const sendToServer = async (value) => {
        const balance = getBalance();
        try {
            await fetch(API_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ 
                    multiplier: value,
                    balance: balance
                })
            });
            console.log(`✅ Data Exported: ${value} | Current Balance: ${balance}`);
        } catch (error) {
            console.error("❌ Transmission failed. Is the Python server running at " + API_URL + "?", error);
        }
    };

    /**
     * Tracks the multiplier element. When it disappears, it triggers the data send.
     */
    const findAndTrack = () => {
        const frames = [window, ...Array.from(window.frames)];
        let element = null;

        for (let frame of frames) {
            try {
                element = frame.document.querySelector("span[class*='_multiplier_']");
                if (element) break;
            } catch (e) { }
        }

        if (element) {
            // Keep updating the last seen multiplier while the round is active
            lastValue = element.innerText.trim();
        } else if (lastValue !== "") {
            // The multiplier element is gone (round ended), send the final value
            sendToServer(lastValue);
            lastValue = ""; // Reset for the next round
        }
    };

    // Scans the DOM every 50ms for updates
    setInterval(findAndTrack, 50);
})();