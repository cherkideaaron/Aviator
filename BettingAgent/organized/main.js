(function () {
    console.log("%c 🛰 VAULT ACTIVE: Routing data to Local Python Server", "color: #3498db; font-weight: bold;");

    let lastValue = "";
    // The URL of your local Python server
    const API_URL = "http://127.0.0.1:5000/save";

    const sendToServer = async (value) => {
        try {
            await fetch(API_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ multiplier: value })
            });
            console.log(`✅ Sent to server: ${value}`);
        } catch (error) {
            console.error("❌ Failed to send to server. Is Python running?", error);
        }
    };

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
            lastValue = element.innerText.trim();
        } else if (lastValue !== "") {
            // As soon as the multiplier element disappears, send the last seen value
            sendToServer(lastValue);
            lastValue = ""; // Reset for the next round
        }
    };

    setInterval(findAndTrack, 50);
})();