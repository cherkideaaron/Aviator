(function () {
    console.log("%c 🛰 VAULT ACTIVE: Routing data to Local Python Server", "color: #3498db; font-weight: bold;");

    let lastValue = "";
    // The URL of your local Python server
    const API_URL = "http://127.0.0.1:5000/save";

    const getBalance = () => {
        const frames = [window, ...Array.from(window.frames)];
        for (let frame of frames) {
            try {
                let el = frame.document.querySelector("span._size-14_1p5jb_34");
                if (el) return el.innerText.trim();
            } catch (e) { }
        }
        return "0.00";
    };

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
            console.log(`✅ Sent to server: ${value} | Balance: ${balance}`);
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