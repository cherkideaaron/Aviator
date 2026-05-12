(function () {
    console.log("%c 🛰 VAULT ACTIVE: Integrated Controller Ready", "color: #2ecc71; font-weight: bold;");

    let lastMultiplier = "";
    const API_BASE = "http://127.0.0.1:5000";
    const SAVE_URL = `${API_BASE}/save`;
    const CMD_URL = `${API_BASE}/get_command`;
    const BALANCE_UPDATE_URL = `${API_BASE}/balance-update`;

    // --- UTILITY FUNCTIONS ---

    const getAllElementsFromFrames = (selector) => {
        let results = [];
        const frames = [window, ...Array.from(window.frames)];
        for (let frame of frames) {
            try {
                let els = frame.document.querySelectorAll(selector);
                if (els.length > 0) results.push(...Array.from(els));
            } catch (e) { /* cross-origin safety */ }
        }
        return results;
    };

    const forceClick = (el) => {
        if (!el) return;
        
        // Calculate coordinates (center of the element)
        const rect = el.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;
        
        const eventOptions = {
            view: window,
            bubbles: true,
            cancelable: true,
            buttons: 1,
            clientX: x,
            clientY: y,
            screenX: x,
            screenY: y,
            isTrusted: true // We can set it, though browser will mark it false, some filters check the property existence
        };

        const events = ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'];
        events.forEach(evt => {
            const eventType = evt.startsWith('pointer') ? PointerEvent : MouseEvent;
            el.dispatchEvent(new eventType(evt, eventOptions));
        });
    };

    const setInputValue = (input, value) => {
        if (!input) return;
        
        // React-safe value setter
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
        nativeInputValueSetter.call(input, value);
        
        // Dispatch events to trigger framework listeners
        const events = ['input', 'change', 'blur'];
        events.forEach(evt => {
            input.dispatchEvent(new Event(evt, { bubbles: true }));
        });
    };

    const getBalance = () => {
        const el = getElementFromFrames("span._size-14_1p5jb_34");
        return el ? el.innerText.trim() : "0.00";
    };

    const clickBetButton = () => {
        // 1. Try targeting by the the user's observed classes
        const allSpans = getAllElementsFromFrames("span");
        const betSpans = allSpans.filter(s => s.innerText.trim().toUpperCase() === "BET");
        
        let clickCount = 0;
        
        if (betSpans.length > 0) {
            betSpans.forEach(span => {
                // Check if the button is actually "clickable" (not disabled via parent)
                let parent = span.parentElement;
                while (parent && parent.tagName !== "BODY") {
                    if (parent.disabled || parent.classList.contains("disabled") || parent.getAttribute("aria-disabled") === "true") {
                        console.warn("⚠️ Found BET span but parent seems disabled.");
                        return;
                    }
                    parent = parent.parentElement;
                }

                console.log(`🎯 Clicking BET span at (${span.getBoundingClientRect().left}, ${span.getBoundingClientRect().top})`);
                forceClick(span);
                
                // Also trigger on the immediate parent if it exists as it's often the actual button
                if (span.parentElement) forceClick(span.parentElement);
                clickCount++;
            });
            console.log(`🚀 Force-clicked ${clickCount} "BET" target(s).`);
        } else {
            console.warn("⚠️ No active 'BET' text found on screen.");
        }
    };

    // --- COMMUNICATION ---

    const sendToServer = async (multiplierValue) => {
        const currentBalance = getBalance();
        try {
            await fetch(SAVE_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    multiplier: multiplierValue, 
                    balance: currentBalance 
                })
            });
            console.log(`✅ Data Status | Multiplier: ${multiplierValue} | Balance: ${currentBalance}`);
        } catch (error) {
            console.error("❌ Link to Python broken.", error);
        }
    };

    const checkRemoteCommands = async () => {
        try {
            const response = await fetch(CMD_URL);
            const data = await response.json();

            // Handle Bet Amount (Force state update)
            if (data.new_bet_amount) {
                const inputs = getAllElementsFromFrames("input[name='bet']");
                inputs.forEach(input => {
                    setInputValue(input, data.new_bet_amount);
                });
                console.log(`💰 Bet state forced to: ${data.new_bet_amount}`);
            }

            if (data.action === "PLACE_BET") {
                // Delay to allow the UI to reflect the new bet amount state
                setTimeout(clickBetButton, 200);
            }
        } catch (e) { }
    };

    // --- MAIN LOOP ---

    let lastRecordedBalance = "";
    const monitorBalance = async () => {
        const currentBalance = getBalance();
        if (currentBalance !== lastRecordedBalance) {
            try {
                await fetch(BALANCE_UPDATE_URL, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ balance: currentBalance })
                });
                lastRecordedBalance = currentBalance;
                console.log(`💰 Balance update sent: ${currentBalance}`);
            } catch (e) { }
        }
    };

    const findAndTrack = () => {
        const multiplierEl = getElementFromFrames("span[class*='_multiplier_']");

        if (multiplierEl) {
            lastMultiplier = multiplierEl.innerText.trim();
        } else if (lastMultiplier !== "") {
            // Round finished
            sendToServer(lastMultiplier);
            lastMultiplier = ""; 
        }
    };

    // Core loops
    setInterval(findAndTrack, 50);        // Fast tracking for the multiplier
    setInterval(checkRemoteCommands, 500); // Check for Python commands every 0.5s
    setInterval(monitorBalance, 250);     // Check for balance changes every 250ms
})();