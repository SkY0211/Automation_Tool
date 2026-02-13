document.addEventListener("DOMContentLoaded", () => {

  /* ===============================
     GLOBAL UI STATE
  =============================== */
  let pairCount = 0;
  let mtNumbers = {};        // {1: "xxxx", 2: "yyyy"}
  let pairs = [];            // [{pairId, mo, mt, moConnected, mtConnected, saved}]
  let testRunning = false;
  let testPaused = false;

  /* ===============================
     HELPERS
  =============================== */

  function getRole(index) {
    const pair = Math.floor(index / 2) + 1;
    const type = index % 2 === 0 ? "MO" : "MT";
    return `${type}${pair}`;
  }

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
  const startBtn = document.getElementById("start-btn");
  const resetBtn = document.getElementById("reset-btn");
  const retestBtn = document.getElementById("retest-btn");

  // NEW: Control buttons
  const controlButtons = document.getElementById("control-buttons");
  const pauseBtn = document.getElementById("pause-btn");
  const resumeBtn = document.getElementById("resume-btn");
  const stopBtn = document.getElementById("stop-btn");

  // NEW: Disconnect modal
  const disconnectModal = document.getElementById("disconnect-modal");
  const closeDisconnectModal = document.getElementById("close-disconnect-modal");
  const disconnectMessage = document.getElementById("disconnect-message");

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
      alert("Please enter an even number of devices");
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
    pairs = [];

    for (let i = 1; i <= count; i++) {
      pairs.push({
        pairId: i,
        mo: null,
        mt: null,
        moConnected: false,
        mtConnected: false,
        saved: false
      });

      container.innerHTML += `
        <div class="connection-row">
          <span class="pair-label">MO–MT Pair ${i}:</span>

          <span id="mo-status-${i}" class="status">MO Not Connected</span>
          <span id="mt-status-${i}" class="status">MT Not Connected</span>

          <input type="text"
                 class="mt-input"
                 data-pair="${i}"
                 placeholder="Enter MT${i} Phone Number"/>

          <button class="primary small-btn" data-pair="${i}">
            Save
          </button>
        </div>
      `;
    }
  }

  /* ===============================
     SAVE MT NUMBER PER PAIR
  =============================== */

  document.body.addEventListener("click", (e) => {
    if (!e.target.classList.contains("small-btn")) return;

    const pairId = Number(e.target.dataset.pair);
    const input = document.querySelector(`input[data-pair="${pairId}"]`);

    if (!input.value.match(/^[0-9]{8,15}$/)) {
      alert(`Enter valid MT number for Pair ${pairId}`);
      return;
    }

    mtNumbers[pairId] = input.value;
    pairs[pairId - 1].saved = true;

    alert(`MT number saved for Pair ${pairId}`);

    if (pairs.every(p => p.saved)) {
      showStep(3);
    }
  });

  /* ===============================
   STATUS POLLING (PAIR-AWARE, FRONTEND ONLY)
   🔧 FIXED: Now properly handles disconnections
=============================== */

setInterval(async () => {
  try {
    const res = await fetch("/api/cat-a/status");
    const data = await res.json();

    // 🔧 FIX: If no pairs data, hide all status indicators
    if (!data.pairs || data.pairs.length === 0) {
      // Clear all status displays when no devices connected
      for (let pairId = 1; pairId <= pairCount; pairId++) {
        const moEl = document.getElementById(`mo-status-${pairId}`);
        const mtEl = document.getElementById(`mt-status-${pairId}`);
        
        if (moEl) {
          moEl.textContent = `MO${pairId} Not Connected`;
          moEl.classList.remove("connected");
        }
        if (mtEl) {
          mtEl.textContent = `MT${pairId} Not Connected`;
          mtEl.classList.remove("connected");
        }
        
        // Update internal pairs state
        if (pairs[pairId - 1]) {
          pairs[pairId - 1].moConnected = false;
          pairs[pairId - 1].mtConnected = false;
        }
      }
      return;
    }

    // 🔧 FIX: Update each pair's status
    data.pairs.forEach((pair, index) => {
      const pairId = index + 1;

      const moEl = document.getElementById(`mo-status-${pairId}`);
      const mtEl = document.getElementById(`mt-status-${pairId}`);

      if (!moEl || !mtEl) return;

      // 🔧 FIX: Use proper boolean checks
      const moConnected = pair.mo_connected === true;
      const mtConnected = pair.mt_connected === true;

      // Update MO status
      moEl.textContent = moConnected
        ? `MO${pairId} Connected`
        : `MO${pairId} Not Connected`;
      moEl.classList.toggle("connected", moConnected);

      // Update MT status
      mtEl.textContent = mtConnected
        ? `MT${pairId} Connected`
        : `MT${pairId} Not Connected`;
      mtEl.classList.toggle("connected", mtConnected);
      
      // 🔧 FIX: Update internal pairs state
      if (pairs[pairId - 1]) {
        pairs[pairId - 1].moConnected = moConnected;
        pairs[pairId - 1].mtConnected = mtConnected;
      }
    });

    // 🔧 FIX: Clear status for pairs that no longer exist
    for (let pairId = data.pairs.length + 1; pairId <= pairCount; pairId++) {
      const moEl = document.getElementById(`mo-status-${pairId}`);
      const mtEl = document.getElementById(`mt-status-${pairId}`);
      
      if (moEl) {
        moEl.textContent = `MO${pairId} Not Connected`;
        moEl.classList.remove("connected");
      }
      if (mtEl) {
        mtEl.textContent = `MT${pairId} Not Connected`;
        mtEl.classList.remove("connected");
      }
      
      if (pairs[pairId - 1]) {
        pairs[pairId - 1].moConnected = false;
        pairs[pairId - 1].mtConnected = false;
      }
    }

  } catch (e) {
    console.error("Status polling failed", e);
    // 🔧 FIX: On error, mark all as disconnected
    for (let pairId = 1; pairId <= pairCount; pairId++) {
      const moEl = document.getElementById(`mo-status-${pairId}`);
      const mtEl = document.getElementById(`mt-status-${pairId}`);
      
      if (moEl) {
        moEl.textContent = `MO${pairId} Not Connected`;
        moEl.classList.remove("connected");
      }
      if (mtEl) {
        mtEl.textContent = `MT${pairId} Not Connected`;
        mtEl.classList.remove("connected");
      }
      
      if (pairs[pairId - 1]) {
        pairs[pairId - 1].moConnected = false;
        pairs[pairId - 1].mtConnected = false;
      }
    }
  }
}, 2000);

// 🔧 FIX: Update Start button enable logic
setInterval(() => {
  if (startBtn && pairs.length > 0 && !testRunning) {
    startBtn.disabled = !pairs.every(
      p => p.saved && p.moConnected && p.mtConnected
    );
  }
}, 500);

  /* ===============================
     NEW: DEVICE DISCONNECTION MONITORING
  =============================== */
  
  setInterval(async () => {
    if (!testRunning) return;
    
    try {
      const res = await fetch("/api/cat-a/status");
      const data = await res.json();
      
      // Check if device disconnected during test
      if (data.device_disconnected === true) {
        const device = data.disconnected_device || "Unknown";
        
        // Show disconnect modal
        disconnectMessage.textContent = `${device} device has been disconnected during the test.`;
        disconnectModal.classList.remove("hidden");
        
        // Hide control buttons
        controlButtons.classList.add("hidden");
        
        // Reset test state
        testRunning = false;
        testPaused = false;
        
        // Clear the disconnect alert on backend
        await fetch("/api/cat-a/clear-disconnect", { method: "POST" });
      }
    } catch (e) {
      console.error("Disconnect monitoring failed", e);
    }
  }, 2000);

  /* ===============================
     NEW: CLOSE DISCONNECT MODAL
  =============================== */
  
  closeDisconnectModal.addEventListener("click", () => {
    disconnectModal.classList.add("hidden");
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
      mt_number: mtNumbers[1] || "",
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
      
      // Update UI state
      testRunning = true;
      testPaused = false;
      
      // Hide Start/Reset/Retest buttons
      startBtn.classList.add("hidden");
      resetBtn.classList.add("hidden");
      retestBtn.classList.add("hidden");
      
      // Show control buttons
      controlButtons.classList.remove("hidden");
      
      // Initially show pause, hide resume
      pauseBtn.classList.remove("hidden");
      resumeBtn.classList.add("hidden");
      
      alert("CAT-A Test Started");

    } catch (err) {
      console.error(err);
      alert("Failed to start CAT-A backend");
    }
  });

  /* ===============================
     NEW: PAUSE BUTTON
  =============================== */
  
  pauseBtn.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/cat-a/pause", { method: "POST" });
      const data = await res.json();
      
      if (data.status === "success") {
        testPaused = true;
        pauseBtn.classList.add("hidden");
        resumeBtn.classList.remove("hidden");
        alert("Test paused");
      } else {
        alert(data.message || "Failed to pause test");
      }
    } catch (err) {
      console.error(err);
      alert("Failed to pause test");
    }
  });

  /* ===============================
     NEW: RESUME BUTTON
  =============================== */
  
  resumeBtn.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/cat-a/resume", { method: "POST" });
      const data = await res.json();
      
      if (data.status === "success") {
        testPaused = false;
        resumeBtn.classList.add("hidden");
        pauseBtn.classList.remove("hidden");
        alert("Test resumed");
      } else {
        alert(data.message || "Failed to resume test");
      }
    } catch (err) {
      console.error(err);
      alert("Failed to resume test");
    }
  });

  /* ===============================
     NEW: STOP BUTTON
  =============================== */
  
  stopBtn.addEventListener("click", async () => {
    if (!confirm("Are you sure you want to stop the test?")) {
      return;
    }
    
    try {
      const res = await fetch("/api/cat-a/stop", { method: "POST" });
      const data = await res.json();
      
      if (data.status === "success") {
        // Reset UI state
        testRunning = false;
        testPaused = false;
        
        // Show Start/Reset/Retest buttons
        startBtn.classList.remove("hidden");
        resetBtn.classList.remove("hidden");
        retestBtn.classList.remove("hidden");
        
        // Hide control buttons
        controlButtons.classList.add("hidden");
        
        alert("Test stopped");
      } else {
        alert(data.message || "Failed to stop test");
      }
    } catch (err) {
      console.error(err);
      alert("Failed to stop test");
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
    pairs = [];
    testRunning = false;
    testPaused = false;
    
    // Show Start/Reset/Retest buttons
    startBtn.classList.remove("hidden");
    resetBtn.classList.remove("hidden");
    retestBtn.classList.remove("hidden");
    
    // Hide control buttons
    controlButtons.classList.add("hidden");
    
    showStep(1);
  });

  /* ===============================
     PROGRESS BAR + AUTO UI RESET ON COMPLETION
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
      
      // Check if test completed or failed
      const statusRes = await fetch("/api/cat-a/status");
      const statusData = await statusRes.json();
      
      if (testRunning && (statusData.state === "COMPLETED" || statusData.state === "FAILED" || statusData.state === "STOPPED")) {
        // Reset UI state
        testRunning = false;
        testPaused = false;
        
        // Show Start/Reset/Retest buttons
        startBtn.classList.remove("hidden");
        resetBtn.classList.remove("hidden");
        retestBtn.classList.remove("hidden");
        
        // Hide control buttons
        controlButtons.classList.add("hidden");
        
        if (statusData.state === "COMPLETED") {
          alert("Test completed successfully!");
        } else if (statusData.state === "FAILED") {
          alert("Test failed: " + (statusData.message || "Unknown error"));
        }
      }

    } catch (e) {}
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
    } catch (e) {}
  }, 1500);

});