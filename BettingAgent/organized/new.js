(function () {
    console.log("%c 🛰 VAULT ACTIVE: Routing data to Local Python Server", "color: #3498db; font-weight: bold;");

    let lastValue = "";
    let isSending = false; // 1. Added a guard flag
    const API_URL = "http://127.0.0.1:5000/save";

    const sendToServer = async (value) => {
        isSending = true; // 2. Lock the process
        try {
            await fetch(API_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ multiplier: value })
            });
            console.log(`✅ Sent to server: ${value}`);
        } catch (error) {
            console.error("❌ Failed to send:", error);
        } finally {
            isSending = false; // 4. Release the lock after completion
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
        } else if (lastValue !== "" && !isSending) { // 3. Check the flag
            const valueToKeep = lastValue;
            lastValue = ""; // Reset IMMEDIATELY before the async call
            sendToServer(valueToKeep);
        }
    };

    setInterval(findAndTrack, 50);
})();