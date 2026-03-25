(function () {
    console.log("%c 🛰 VAULT ACTIVE: Monitoring for Crash Points...", "color: #2ecc71; font-weight: bold;");

    let lastValue = "";
    const API_URL = "http://127.0.0.1:5000/save";

    const findElementDeep = (root) => {
        let el = root.querySelector("text.crash-game__counter");
        if (el) return el;

        const iframes = root.querySelectorAll("iframe");
        for (let i = 0; i < iframes.length; i++) {
            try {
                const iframeDoc = iframes[i].contentDocument || iframes[i].contentWindow.document;
                el = findElementDeep(iframeDoc);
                if (el) return el;
            } catch (e) { }
        }
        return null;
    };

    const sendToServer = async (value) => {
        try {
            const response = await fetch(API_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ multiplier: value })
            });
            if (response.ok) {
                console.log(`%c 🎯 CRASH SAVED: ${value}`, "color: #f1c40f; font-weight: bold;");
            }
        } catch (error) {
            console.error("❌ Network Error: Is the Python server running?");
        }
    };

    const track = () => {
        const element = findElementDeep(document);

        if (element) {
            const currentText = element.textContent.trim();

            // If the text contains a digit (e.g., "9.71x"), update our record
            if (/\d/.test(currentText)) {
                lastValue = currentText;
            }
            // If the text resets to "x" while we have a stored value, the round ended
            else if (currentText === "x" && lastValue !== "") {
                sendToServer(lastValue);
                lastValue = "";
            }
        } else {
            // If the element disappears entirely while we have a stored value, the round ended
            if (lastValue !== "") {
                sendToServer(lastValue);
                lastValue = "";
            }
        }
    };

    setInterval(track, 100);
})();