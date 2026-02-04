document.addEventListener("DOMContentLoaded", () => {

    /* ===============================
       GLOBAL UI STATE
    =============================== */
    let pairCount = 0;
    let mtNumbers = {}; // {1: "xxxx", 2: "yyyy"}

    /* ===============================
       HOME ↔ CAT-A NAVIGATION
    =============================== */

    function showCatAScreen() {
        document.getElementById("home-screen").classList.add("hidden");
        document.getElementById("cat-a-screen").classList.remove("hidden");
        showStep(1);
    }

    function showHomeScreen() {
        document.getElementById("cat-a-screen").classList.add("hidden");
        document.getElementById("home-screen").classList.remove("hidden");
    }

    document.body.addEventListener("click", (event) => {
        if (event.target.closest("#cat-a")) showCatAScreen();
        if (event.target.closest("#back-home")) showHomeScreen();
    });

    /* ===============================
       STEP REFERENCES
    =============================== */

    const step1 = document.getElementById("cat-step-1");
    const step2 = document.getElementById("cat-step-2");
    const step3 = document.getElementById("cat-step-3");

    const testType = document.getElementById("test-type");
    const deviceCount = document.getElementById("device-count");

    const iterations = document.getElementById("iterations");
    const callDuration = document.getElementById("call-duration");
    const callDelay = document.getElementById("call-delay");

    const nextBtn = document.getElementById("next-to-step-2");
    const startBtn = document.querySelector(".success");
    const resetBtn = document.querySelector(".secondary");
    const retestBtn = document.querySelector(".info");

    /* ===============================
       STEP SWITCHING
    =============================== */

    function showStep(step) {
        step1.classList.add("hidden");
        step2.classList.add("hidden");
        step3.classList.add("hidden");

        if (step === 1) step1.classList.remove("hidden");
        if (step === 2) step2.classList.remove("hidden");
        if (step === 3) step3.classList.remove("hidden");
    }

    /* ===============================
       STEP 1 → STEP 2
    =============================== */

    nextBtn.addEventListener("click", () => {
        const count = Number(deviceCount.value);

        if (!testType.value || !count) {
            alert("Please select test type and device count");
            return;
        }

        if (count % 2 !== 0) {
            alert("Please enter an even number of devices (MO–MT pairs)");
            return;
        }

        pairCount = count / 2;
        renderPairs(pairCount);
        showStep(2);
    });

    /* ===============================
       RENDER MO–MT PAIRS
    =============================== */

    function renderPairs(count) {
        const container = document.getElementById("pair-container");
        container.innerHTML = "";
        mtNumbers = {};

        for (let i = 1; i <= count; i++) {
            const row = document.createElement("div");
            row.className = "connection-row";

            row.innerHTML = `
                <span class="pair-label">MO–MT Pair ${i}:</span>

                <span id="mo-status-${i}" class="status">MO${i} Not Connected</span>
                <span id="mt-status-${i}" class="status">MT${i} Not Connected</span>

                <select class="device-select">
                    <option>MO${i}</option>
                </select>

                <select class="device-select">
                    <option>MT${i}</option>
                </select>

                <input type="text"
                       class="mt-input"
                       data-pair="${i}"
                       placeholder="Enter MT${i} Phone Number"/>

                <button class="primary small-btn" data-pair="${i}">
                    Save
                </button>
            `;

            container.appendChild(row);
        }
    }

    /* ===============================
       SAVE MT NUMBER PER PAIR
    =============================== */

    document.body.addEventListener("click", (e) => {
        if (e.target.matches(".small-btn")) {
            const pair = e.target.dataset.pair;
            const input = document.querySelector(`input[data-pair="${pair}"]`);

            if (!input.value.match(/^[0-9]{8,15}$/)) {
                alert(`Enter valid MT number for Pair ${pair}`);
                return;
            }

            mtNumbers[pair] = input.value;
            alert(`MT number saved for Pair ${pair}`);
        }
    });

    /* ===============================
       START TEST → BACKEND
       (NO automation logic changed)
    =============================== */

    startBtn.addEventListener("click", async () => {

        if (!iterations.value || !callDuration.value || !callDelay.value) {
            alert("Please fill all execution parameters");
            return;
        }

        const payload = {
            test_type: testType.value,
            device_count: Number(deviceCount.value),
            mt_number: mtNumbers[1] || "", // backend unchanged
            iterations: Number(iterations.value),
            call_duration: Number(callDuration.value),
            call_delay: Number(callDelay.value)
        };

        try {
            const res = await fetch("/api/cat-a/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            await res.json();
            alert("CAT-A Test Started");

        } catch (err) {
            console.error(err);
            alert("Failed to start CAT-A backend");
        }
    });

    /* ===============================
       RESET / RETEST
    =============================== */

    resetBtn.addEventListener("click", () => {
        iterations.value = "";
        callDuration.value = "";
        callDelay.value = "";
    });

    retestBtn.addEventListener("click", () => {
        mtNumbers = {};
        showStep(1);
    });

    /* ===============================
       STATUS POLLING (MULTI-PAIR UI)
    =============================== */

    setInterval(async () => {
        try {
            const res = await fetch("/api/cat-a/status");
            const data = await res.json();

            for (let i = 1; i <= pairCount; i++) {
                const moEl = document.getElementById(`mo-status-${i}`);
                const mtEl = document.getElementById(`mt-status-${i}`);

                if (!moEl || !mtEl) continue;

                moEl.textContent = data.mo_connected
                    ? `MO${i} Connected`
                    : `MO${i} Not Connected`;

                mtEl.textContent = data.mt_connected
                    ? `MT${i} Connected`
                    : `MT${i} Not Connected`;

                moEl.classList.toggle("connected", data.mo_connected);
                mtEl.classList.toggle("connected", data.mt_connected);
            }

            startBtn.disabled = !(data.mo_connected && data.mt_connected);

        } catch (e) {
            console.error("Status polling failed", e);
        }
    }, 2000);

    /* ===============================
       PROGRESS BAR
    =============================== */

    setInterval(async () => {
        try {
            const res = await fetch("/api/cat-a/progress");
            const data = await res.json();

            const progressBar = document.getElementById("progress-bar");
            const progressText = document.getElementById("progress-text");

            if (!progressBar || !progressText) return;

            progressBar.value = data.percent || 0;
            progressText.innerText = `Progress: ${data.percent || 0}%`;

        } catch (e) {
            // silent
        }
    }, 1000);

    /* ===============================
       LIVE LOG STREAM
    =============================== */

    setInterval(async () => {
        const logBox = document.getElementById("log-box");
        if (!logBox) return;

        try {
            const res = await fetch("/api/cat-a/logs");
            const logs = await res.json();

            logBox.innerText = logs.join("\n");
            logBox.scrollTop = logBox.scrollHeight;
        } catch (e) {
            // silent
        }
    }, 1500);

});
