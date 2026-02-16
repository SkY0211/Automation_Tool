document.addEventListener("DOMContentLoaded", () => {

  let pairCount = 0;
  let mtNumbers = {};
  let pairs = [];
  let testRunning = false;
  let testPaused = false;

  const disconnectModal = document.getElementById("disconnect-modal");
  const closeDisconnectModal = document.getElementById("close-disconnect-modal");
  const disconnectMessage = document.getElementById("disconnect-message");

  // Hide modal and clear alerts on startup
  if (disconnectModal) {
    disconnectModal.classList.add("hidden");
    disconnectModal.style.display = "none";
    
    fetch("/api/cat-a/clear-disconnect", { method: "POST" })
      .then(() => console.log("✅ Startup: Alerts cleared"))
      .catch(() => {});
  }

  function getRole(index) {
    const pair = Math.floor(index / 2) + 1;
    const type = index % 2 === 0 ? "MO" : "MT";
    return `${type}${pair}`;
  }

  function showCatAScreen() {
    document.getElementById("home-screen").classList.add("hidden");
    document.getElementById("cat-a-screen").classList.remove("hidden");
    showStep(1);
  }

  function showHomeScreen() {
    document.getElementById("cat-a-screen").classList.add("hidden");
    document.getElementById("home-screen").classList.remove("hidden");
    
    fetch("/api/cat-a/clear-disconnect", { method: "POST" }).catch(() => {});
  }

  document.body.addEventListener("click", (event) => {
    if (event.target.closest("#cat-a")) showCatAScreen();
    if (event.target.closest("#back-home")) showHomeScreen();
  });

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

  const controlButtons = document.getElementById("control-buttons");
  const pauseBtn = document.getElementById("pause-btn");
  const resumeBtn = document.getElementById("resume-btn");
  const stopBtn = document.getElementById("stop-btn");

  function showStep(step) {
    step1.classList.add("hidden");
    step2.classList.add("hidden");
    step3.classList.add("hidden");

    if (step === 1) step1.classList.remove("hidden");
    if (step === 2) step2.classList.remove("hidden");
    if (step === 3) step3.classList.remove("hidden");
  }

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
          <input type="text" class="mt-input" data-pair="${i}" placeholder="Enter MT${i} Phone Number"/>
          <button class="primary small-btn" data-pair="${i}">Save</button>
        </div>
      `;
    }
  }

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
  
  // Status polling
  setInterval(async () => {
    try {
      const res = await fetch("/api/cat-a/status");
      const data = await res.json();

      if (!data.pairs || data.pairs.length === 0) {
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
        return;
      }

      data.pairs.forEach((pair, index) => {
        const pairId = index + 1;
        const moEl = document.getElementById(`mo-status-${pairId}`);
        const mtEl = document.getElementById(`mt-status-${pairId}`);

        if (!moEl || !mtEl) return;

        const moConnected = pair.mo_connected === true;
        const mtConnected = pair.mt_connected === true;

        moEl.textContent = moConnected ? `MO${pairId} Connected` : `MO${pairId} Not Connected`;
        moEl.classList.toggle("connected", moConnected);

        mtEl.textContent = mtConnected ? `MT${pairId} Connected` : `MT${pairId} Not Connected`;
        mtEl.classList.toggle("connected", mtConnected);
        
        if (pairs[pairId - 1]) {
          pairs[pairId - 1].moConnected = moConnected;
          pairs[pairId - 1].mtConnected = mtConnected;
        }
      });

    } catch (e) {
      console.error("Status polling failed", e);
    }
  }, 2000);

  setInterval(() => {
    if (startBtn && pairs.length > 0 && !testRunning) {
      startBtn.disabled = !pairs.every(p => p.saved && p.moConnected && p.mtConnected);
    }
  }, 500);

  // Device disconnection monitoring
  setInterval(async () => {
    if (!testRunning) return;
    
    const homeScreen = document.getElementById("home-screen");
    if (homeScreen && !homeScreen.classList.contains("hidden")) {
      return;
    }
    
    if (!step3 || step3.classList.contains("hidden")) {
      return;
    }
    
    try {
      const res = await fetch("/api/cat-a/status");
      const data = await res.json();
      
      // Check if device disconnected during test
      if (data.device_disconnected === true && data.test_running === true) {
        const device = data.disconnected_device || "Unknown";
        
        console.log("⚠️ Device disconnect detected - test PAUSED:", device);
        
        // Update popup message
        disconnectMessage.textContent = `${device} device has been disconnected during the test. The test has been PAUSED. Please reconnect the device and click Resume to continue.`;
        disconnectModal.classList.remove("hidden");
        disconnectModal.style.display = "flex";
        
        // Set UI to paused state (keep control buttons visible!)
        testPaused = true;
        pauseBtn.classList.add("hidden");
        resumeBtn.classList.remove("hidden");  // Show Resume button
        
        // Clear the disconnect alert on backend
        await fetch("/api/cat-a/clear-disconnect", { method: "POST" });
      }
    } catch (e) {
      console.error("Disconnect monitoring failed", e);
    }
  }, 2000);

  if (closeDisconnectModal) {
    closeDisconnectModal.addEventListener("click", async () => {
      disconnectModal.classList.add("hidden");
      disconnectModal.style.display = "none";
      
      await fetch("/api/cat-a/clear-disconnect", { method: "POST" }).catch(() => {});
    });
  }

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
      await fetch("/api/cat-a/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      
      testRunning = true;
      testPaused = false;
      
      console.log("✅ Test started");
      
      // Clear logs panel when starting new test
      const logBox = document.getElementById("log-box");
      if (logBox) {
        logBox.innerText = "Test started...\n";
        console.log("✅ Logs cleared for new test");
      }
      
      startBtn.classList.add("hidden");
      resetBtn.classList.add("hidden");
      retestBtn.classList.add("hidden");
      
      controlButtons.classList.remove("hidden");
      pauseBtn.classList.remove("hidden");
      resumeBtn.classList.add("hidden");

    } catch (err) {
      console.error(err);
      alert("Failed to start test");
    }
  });

  pauseBtn.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/cat-a/pause", { method: "POST" });
      const data = await res.json();
      
      if (data.status === "success") {
        testPaused = true;
        pauseBtn.classList.add("hidden");
        resumeBtn.classList.remove("hidden");
        console.log("✅ Test paused");
      } else {
        alert(data.message || "Failed to pause test");
      }
    } catch (err) {
      console.error(err);
      alert("Failed to pause test");
    }
  });

  resumeBtn.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/cat-a/resume", { method: "POST" });
      const data = await res.json();
      
      if (data.status === "success") {
        testPaused = false;
        resumeBtn.classList.add("hidden");
        pauseBtn.classList.remove("hidden");
        console.log("✅ Test resumed");
      } else {
        alert(data.message || "Failed to resume test");
      }
    } catch (err) {
      console.error(err);
      alert("Failed to resume test");
    }
  });

  stopBtn.addEventListener("click", async () => {
    if (!confirm("Are you sure you want to stop the test?")) return;
    
    try {
      const res = await fetch("/api/cat-a/stop", { method: "POST" });
      const data = await res.json();
      
      if (data.status === "success") {
        testRunning = false;
        testPaused = false;
        
        startBtn.classList.remove("hidden");
        resetBtn.classList.remove("hidden");
        retestBtn.classList.remove("hidden");
        controlButtons.classList.add("hidden");
        
        console.log("Test stopped");
      } else {
        alert(data.message || "Failed to stop test");
      }
    } catch (err) {
      console.error(err);
      alert("Failed to stop test");
    }
  });

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
    
    startBtn.classList.remove("hidden");
    resetBtn.classList.remove("hidden");
    retestBtn.classList.remove("hidden");
    controlButtons.classList.add("hidden");
    
    showStep(1);
  });

  // Progress monitoring with test completion detection
  let lastBackendTestRunning = false;

  setInterval(async () => {
    try {
      const progressRes = await fetch("/api/cat-a/progress");
      const progressData = await progressRes.json();

      const progressBar = document.getElementById("progress-bar");
      const progressText = document.getElementById("progress-text");

      if (progressBar && progressText) {
        progressBar.value = progressData.percent || 0;
        progressText.innerText = `Progress: ${progressData.percent || 0}%`;
      }
      
      const statusRes = await fetch("/api/cat-a/status");
      const statusData = await statusRes.json();
      
      const backendTestRunning = statusData.test_running === true;
      
      // Detect when test stops running on backend OR reaches 100%
      if (testRunning && (!backendTestRunning || progressData.percent >= 100) && lastBackendTestRunning) {
        console.log("✅ Test ended - backend test_running became false or progress reached 100%");
        
        testRunning = false;
        testPaused = false;
        
        // Show Start/Reset/Retest buttons
        startBtn.classList.remove("hidden");
        resetBtn.classList.remove("hidden");
        retestBtn.classList.remove("hidden");
        
        // Hide control buttons
        controlButtons.classList.add("hidden");
        
        // Only show completion alert if NOT a disconnect
        if (!statusData.device_disconnected) {
          if (statusData.state === "COMPLETED" || progressData.percent >= 100) {
            alert("Test completed successfully!");
          } else if (statusData.state === "FAILED") {
            alert("Test failed: " + (statusData.message || "Unknown error"));
          }
        }
      }
      
      lastBackendTestRunning = backendTestRunning;

    } catch (e) {
      console.error("Progress polling error:", e);
    }
  }, 1000);

  // Live logs
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

  // Auto-clear disconnect alerts on home screen
  setInterval(() => {
    const homeScreen = document.getElementById("home-screen");
    if (homeScreen && !homeScreen.classList.contains("hidden")) {
      fetch("/api/cat-a/clear-disconnect", { method: "POST" }).catch(() => {});
    }
  }, 5000);

});