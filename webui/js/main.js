document.addEventListener("DOMContentLoaded", () => {

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
    const mtNumber = document.getElementById("mt-number");

    const iterations = document.getElementById("iterations");
    const callDuration = document.getElementById("call-duration");
    const callDelay = document.getElementById("call-delay");

    const nextBtn = document.getElementById("next-to-step-2");
    const saveBtn = document.getElementById("save-and-next");

    const startBtn  = document.querySelector(".success");
    const resetBtn  = document.querySelector(".secondary");
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
        if (!testType.value || !deviceCount.value) {
            alert("Please select test type and device count");
            return;
        }
        showStep(2);
    });

    /* ===============================
       STEP 2 → STEP 3
    =============================== */

    saveBtn.addEventListener("click", () => {
        if (!mtNumber.value.match(/^[0-9]{8,15}$/)) {
            alert("Enter a valid phone number");
            return;
        }
        showStep(3);
    });

    /* ===============================
       START TEST → BACKEND
    =============================== */

    startBtn.addEventListener("click", async () => {

        if (!iterations.value || !callDuration.value || !callDelay.value) {
            alert("Please fill all execution parameters");
            return;
        }

        const payload = {
            test_type: testType.value,
            device_count: Number(deviceCount.value),
            mt_number: mtNumber.value,
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

            const data = await res.json();
            alert("CAT-A Test Started");

        } catch (err) {
            console.error(err);
            alert("Failed to start CAT-A backend");
        }
    });

    /* ===============================
       RESET
    =============================== */

    resetBtn.addEventListener("click", () => {
        iterations.value = "";
        callDuration.value = "";
        callDelay.value = "";
    });

    /* ===============================
       RETEST (Back to Step 1)
    =============================== */

    retestBtn.addEventListener("click", () => {
        showStep(1);
    });

    /* ===============================
       STATUS POLLING
    =============================== */

    setInterval(async () => {
        try {
            const res = await fetch("/api/cat-a/status");
            const data = await res.json();

            console.log("CAT-A STATUS:", data.state);

            // Future UI hook:
            // document.getElementById("status-text").innerText = data.state;

        } catch (e) {
            console.warn("Status API not ready");
        }
    }, 2000);

    /* ===============================
       LOG STREAMING
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
            // silent fail (desktop-safe)
        }
    }, 1500);

});

    setInterval(async () => {
    try {
        const res = await fetch("/api/cat-a/status");
        const data = await res.json();

        const moEl = document.getElementById("mo-status");
        const mtEl = document.getElementById("mt-status");

        // MO STATUS
        if (data.mo_connected) {
            moEl.textContent = "MO1 Connected";
            moEl.classList.add("connected");
        } else {
            moEl.textContent = "MO1 Not Connected";
            moEl.classList.remove("connected");
        }

        // MT STATUS
        if (data.mt_connected) {
            mtEl.textContent = "MT1 Connected";
            mtEl.classList.add("connected");
        } else {
            mtEl.textContent = "MT1 Not Connected";
            mtEl.classList.remove("connected");
        }

    } catch (e) {
        console.error("Status polling failed", e);
    }
}, 2000);

    const startBtn = document.querySelector(".success");

setInterval(async () => {
    try {
        const res = await fetch("/api/cat-a/status");
        const data = await res.json();

        // Device status (unchanged)
        document.getElementById("mo-status").innerText =
            data.mo_connected ? "MO1 Connected" : "MO1 Not Connected";

        document.getElementById("mt-status").innerText =
            data.mt_connected ? "MT1 Connected" : "MT1 Not Connected";

        startBtn.disabled = !(data.mo_connected && data.mt_connected);

        // 👉 PROGRESS BAR UPDATE
        if (data.progress) {
            const percent = data.progress.percent || 0;
            document.getElementById("progress-fill").style.width = percent + "%";
            document.getElementById("progress-text").innerText =
                `Progress: ${percent}%`;
        }

    } catch (e) {
        console.error("Status polling failed", e);
    }
}, 2000);

// ========================Start Test Click Handler============================== //

startBtn.addEventListener("click", async () => {

    console.log("Start Test clicked"); // 👈 ADD

    if (!iterations.value || !callDuration.value || !callDelay.value) {
        alert("Please fill all execution parameters");
        return;
    }

    const payload = {
    test_type: testType.value,                 // short / long
    device_count: Number(deviceCount.value),   // device count
    mt_number: mtNumber.value,                 // MT number

    // execution params (STRICT mapping)
    iterations: Number(iterations.value),
    call_duration: Number(callDuration.value),
    call_delay: Number(callDelay.value)
    };

    // Debug log (do NOT remove)
    console.log("Payload being sent to backend:", payload);


    const res = await fetch("/api/cat-a/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    const data = await res.json();
    console.log("Backend response:", data); // 👈 ADD

    alert("Start request sent");
});


setInterval(async () => {
    try {
        const res = await fetch("/api/cat-a/progress");
        const data = await res.json();

        const progressBar = document.getElementById("progress-bar");
        const progressText = document.getElementById("progress-text");

        if (!progressBar || !progressText) return;

        progressBar.value = data.percent;
        progressText.innerText = `Progress: ${data.percent}%`;

    } catch (e) {
        console.warn("Progress API not ready");
    }
}, 1000);


setInterval(async () => {
    const logBox = document.getElementById("log-box");
    if (!logBox) return;

    try {
        const res = await fetch("/api/cat-a/logs");
        const logs = await res.json();

        logBox.innerText = logs.join("\n");
        logBox.scrollTop = logBox.scrollHeight;
    } catch (e) {}
}, 1500);

logBox.innerText = logs.join("\n\n");

