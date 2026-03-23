document.addEventListener("DOMContentLoaded", () => {

  let pairCount = 0;
  let mtNumbers = {};
  let pairs = [];
  let testRunning = false;
  let testPaused = false;
  let previousOosState = false;  // Track previous OOS state to detect changes

  const disconnectModal = document.getElementById("disconnect-modal");
  const closeDisconnectModal = document.getElementById("close-disconnect-modal");
  const disconnectMessage = document.getElementById("disconnect-message");

  // ✅ NEW: OOS modal references
  const oosModal = document.getElementById("oos-modal");
  const closeOosModal = document.getElementById("close-oos-modal");
  const oosMessage = document.getElementById("oos-message");
  const oosDevicesList = document.getElementById("oos-devices-list");

  // ✅ Device connection modal references
  const deviceConnectionModal = document.getElementById("device-connection-modal");
  const deviceConnectionTitle = document.getElementById("device-connection-title");
  const deviceInstruction = document.getElementById("device-instruction");
  const connectionStep1 = document.getElementById("connection-step-1");
  const connectionStep2 = document.getElementById("connection-step-2");
  const proceedBtn = document.getElementById("proceed-connection-btn");
  const confirmDeviceBtn = document.getElementById("confirm-device-btn");

  // Hide both modals and clear alerts on startup
  if (disconnectModal) {
    disconnectModal.classList.add("hidden");
    disconnectModal.style.display = "none";
    
    fetch("/api/cat-a/clear-disconnect", { method: "POST" })
      .then(() => console.log("✅ Startup: Alerts cleared"))
      .catch(() => {});
  }

  // ✅ NEW: Hide OOS modal on startup
  if (oosModal) {
    oosModal.classList.add("hidden");
    oosModal.style.display = "none";

    fetch("/api/cat-a/clear-oos", { method: "POST" }).catch(() => {});
  }

  // ✅ Hide device connection modal on startup
  if (deviceConnectionModal) {
    deviceConnectionModal.classList.add("hidden");
    deviceConnectionModal.style.display = "none";
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
    
    // ✅ Reset device connection state
    alreadyConnectedSerials = [];
    currentConnectingPair = null;
    currentConnectingType = null;
    mtNumbers = {};
    pairs = [];
    
    fetch("/api/cat-a/clear-disconnect", { method: "POST" }).catch(() => {});
    fetch("/api/cat-a/clear-oos", { method: "POST" }).catch(() => {});
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

    const catInfoPanel = document.getElementById("cat-info-panel");
    const catLayout = document.querySelector(".cat-layout");
    
    if (step === 1) {
      step1.classList.remove("hidden");
      if (catInfoPanel) catInfoPanel.style.visibility = "visible";
      if (catLayout) catLayout.classList.remove("no-sidebar");
    }
    if (step === 2) {
      step2.classList.remove("hidden");
      if (catInfoPanel) catInfoPanel.style.visibility = "hidden";
      if (catLayout) catLayout.classList.add("no-sidebar");
    }
    if (step === 3) {
      step3.classList.remove("hidden");
      if (catInfoPanel) catInfoPanel.style.visibility = "hidden";
      if (catLayout) catLayout.classList.add("no-sidebar");
    }
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
    
    // ✅ CRITICAL: Reset device connection tracking on retest/reset
    alreadyConnectedSerials = [];
    currentConnectingPair = null;
    currentConnectingType = null;

    for (let i = 1; i <= count; i++) {
      pairs.push({
        pairId: i,
        mo: null,
        mt: null,
        moSerial: null,
        mtSerial: null,
        moSimPref: null,
        mtSimPref: null,
        moConnected: false,
        mtConnected: false,
        saved: false
      });

      container.innerHTML += `
        <div class="connection-row">
          <span class="pair-label">MO–MT Pair ${i}:</span>
          <button class="primary small-btn connect-mo-btn" data-pair="${i}">Connect MO${i}</button>
          <span id="mo-status-${i}" class="status">Not Connected</span>
          <button class="primary small-btn connect-mt-btn" data-pair="${i}" disabled>Connect MT${i}</button>
          <span id="mt-status-${i}" class="status">Not Connected</span>
          <input type="text" class="mt-input" data-pair="${i}" placeholder="Enter MT${i} Phone Number" disabled/>
          <button class="primary small-btn save-btn" data-pair="${i}" disabled>Save</button>
        </div>
      `;
    }
  }

  let currentConnectingPair = null;
  let currentConnectingType = null; // 'mo' or 'mt'
  let alreadyConnectedSerials = [];

  // Handle Connect MO button clicks
  document.body.addEventListener("click", async (e) => {
    if (e.target.classList.contains("connect-mo-btn")) {
      const pairId = Number(e.target.dataset.pair);
      currentConnectingPair = pairId;
      currentConnectingType = 'mo';
      
      // Show connection modal
      deviceConnectionTitle.textContent = `Connect MO${pairId}`;
      deviceInstruction.textContent = `Connect the MO${pairId} device and click 'Proceed' button`;
      connectionStep1.classList.remove("hidden");
      connectionStep2.classList.add("hidden");
      deviceConnectionModal.classList.remove("hidden");
      deviceConnectionModal.style.display = "flex";
    }
    
    // Handle Connect MT button clicks
    if (e.target.classList.contains("connect-mt-btn")) {
      const pairId = Number(e.target.dataset.pair);
      currentConnectingPair = pairId;
      currentConnectingType = 'mt';
      
      // Show connection modal
      deviceConnectionTitle.textContent = `Connect MT${pairId}`;
      deviceInstruction.textContent = `Connect the MT${pairId} device and click 'Proceed' button`;
      connectionStep1.classList.remove("hidden");
      connectionStep2.classList.add("hidden");
      deviceConnectionModal.classList.remove("hidden");
      deviceConnectionModal.style.display = "flex";
    }
    
    // Handle Save button clicks
    if (e.target.classList.contains("save-btn")) {
      const pairId = Number(e.target.dataset.pair);
      const input = document.querySelector(`input[data-pair="${pairId}"]`);

      if (!input.value.match(/^[0-9]{8,15}$/)) {
        alert(`Enter valid MT number for Pair ${pairId}`);
        return;
      }

      mtNumbers[pairId] = input.value;
      pairs[pairId - 1].saved = true;
      
      // Disable save button and input
      e.target.disabled = true;
      input.disabled = true;

      alert(`MT number saved for Pair ${pairId}`);

      if (pairs.every(p => p.saved)) {
        showStep(3);
      }
    }
  });

  // Handle Proceed button click
  proceedBtn.addEventListener("click", async () => {
    proceedBtn.disabled = true;
    proceedBtn.textContent = "Detecting...";
    
    try {
      // Call API to detect new device
      const response = await fetch("/api/cat-a/detect-device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          already_connected: alreadyConnectedSerials 
        })
      });
      
      const data = await response.json();
      
      if (data.status === "error" || data.device === "NotFound") {
        alert("No device found. Connect the device properly and try again.");
        proceedBtn.disabled = false;
        proceedBtn.textContent = "Proceed";
        return;
      }
      
      // Show device info
      document.getElementById("device-udid").textContent = data.device.serial;
      document.getElementById("device-name").textContent = data.device.name;
      document.getElementById("device-version").textContent = data.device.android_version;
      
      // Clear SIM preference selection
      document.querySelectorAll('input[name="sim-pref"]').forEach(radio => {
        radio.checked = false;
      });
      
      // Show step 2
      connectionStep1.classList.add("hidden");
      connectionStep2.classList.remove("hidden");
      
      proceedBtn.disabled = false;
      proceedBtn.textContent = "Proceed";
      
    } catch (error) {
      console.error("Device detection error:", error);
      alert("Error detecting device. Please try again.");
      proceedBtn.disabled = false;
      proceedBtn.textContent = "Proceed";
    }
  });

  // Handle Confirm button click
  confirmDeviceBtn.addEventListener("click", () => {
    const selectedSim = document.querySelector('input[name="sim-pref"]:checked');
    
    if (!selectedSim) {
      alert("Please select a SIM preference");
      return;
    }
    
    const serial = document.getElementById("device-udid").textContent;
    const name = document.getElementById("device-name").textContent;
    const simPref = parseInt(selectedSim.value);
    
    // Save device info to pair
    const pair = pairs[currentConnectingPair - 1];
    
    if (currentConnectingType === 'mo') {
      pair.moSerial = serial;
      pair.mo = name;
      pair.moSimPref = simPref;
      pair.moConnected = true;
      
      // Update UI
      const moStatus = document.getElementById(`mo-status-${currentConnectingPair}`);
      moStatus.textContent = `${name} (SIM${simPref + 1})`;
      moStatus.classList.add("connected");  // Adds CSS class
      moStatus.style.color = "white";
      
      // Enable Connect MT button
      const mtBtn = document.querySelector(`.connect-mt-btn[data-pair="${currentConnectingPair}"]`);
      mtBtn.disabled = false;
      
      // Disable Connect MO button
      const moBtn = document.querySelector(`.connect-mo-btn[data-pair="${currentConnectingPair}"]`);
      moBtn.disabled = true;
      
    } else { // mt
      pair.mtSerial = serial;
      pair.mt = name;
      pair.mtSimPref = simPref;
      pair.mtConnected = true;
      
      // Update UI
      const mtStatus = document.getElementById(`mt-status-${currentConnectingPair}`);
      mtStatus.textContent = `${name} (SIM${simPref + 1})`;
      mtStatus.classList.add("connected");  // Adds CSS class
      mtStatus.style.color = "white";
      
      // Enable phone number input and save button
      const input = document.querySelector(`input[data-pair="${currentConnectingPair}"]`);
      input.disabled = false;
      
      const saveBtn = document.querySelector(`.save-btn[data-pair="${currentConnectingPair}"]`);
      saveBtn.disabled = false;
      
      // Disable Connect MT button
      const mtBtn = document.querySelector(`.connect-mt-btn[data-pair="${currentConnectingPair}"]`);
      mtBtn.disabled = true;
    }
    
    // Add to already connected list
    alreadyConnectedSerials.push(serial);
    
    // Close modal
    deviceConnectionModal.classList.add("hidden");
    deviceConnectionModal.style.display = "none";
  });

  // Status polling - ONLY for step 3 (during test execution)
  setInterval(async () => {
    // Only poll when on step 3 (test execution screen)
    const step3 = document.getElementById("cat-step-3");
    if (!step3 || step3.classList.contains("hidden")) {
      return;
    }
    
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
      
      // Use backend test_running instead of frontend testRunning
      if (!data.test_running) return;
      
      // Check if device disconnected during test
      if (data.device_disconnected === true && data.test_running === true) {
        const device = data.disconnected_device || "Unknown";
        
        console.log("⚠️ Device disconnect detected - test PAUSED:", device);
        
        // Update popup message
        disconnectMessage.textContent = `A device has been disconnected during the test. The test has been PAUSED. Please reconnect the device and click Resume to continue.`;
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

  // ✅ OOS monitoring - now fully automated, no popup needed
  setInterval(async () => {
    const homeScreen = document.getElementById("home-screen");
    if (homeScreen && !homeScreen.classList.contains("hidden")) return;

    if (!step3 || step3.classList.contains("hidden")) return;

    try {
      const res = await fetch("/api/cat-a/status");
      const data = await res.json();

      const backendRunning = data.test_running === true;

      // ✅ YOUR ORIGINAL CODE + POPUP WHEN STATE CHANGES
      if (data.oos_detected === true && backendRunning) {
        console.log("📵 OOS detected - auto-waiting for devices to come back online");
        
        // Show popup ONLY when OOS state changes from false → true
        if (previousOosState === false) {
          console.log("🔔 OOS state changed: false → true, showing alert");
          previousOosState = true;  // Update state
          
          // Update modal message
          const oosDevicesList = document.getElementById("oos-devices-list");
          if (oosDevicesList) {
            oosDevicesList.textContent = "A device has entered an Out of Service zone";
          }
          
          // Show modal
          if (oosModal) {
            oosModal.style.display = "flex";
            oosModal.classList.remove("hidden");
          }
          
          // Play sound
          try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.2);
          } catch (e) {
            console.log("Sound failed:", e);
          }
          
          // Auto-dismiss after 4 seconds
          setTimeout(() => {
            if (oosModal) {
              oosModal.style.display = "none";
              oosModal.classList.add("hidden");
            }
            console.log("✅ OOS alert auto-dismissed");
          }, 4000);
        }
      } else {
        // Reset state when OOS is false
        if (previousOosState === true) {
          previousOosState = false;
          console.log("✅ OOS cleared - state reset");
        }
      }
    } catch (e) {
      console.error("OOS monitoring failed", e);
    }
  }, 2000);

  // ✅ NEW: OOS modal close handler
  if (closeOosModal) {
    closeOosModal.addEventListener("click", async () => {
      oosModal.classList.add("hidden");
      oosModal.style.display = "none";

      // Clear OOS alert on backend so it doesn't re-trigger immediately
      await fetch("/api/cat-a/clear-oos", { method: "POST" }).catch(() => {});

      console.log("✅ OOS modal closed - user acknowledged");
    });
  }

  startBtn.addEventListener("click", async () => {
    if (!iterations.value || !callDuration.value || !callDelay.value) {
      alert("Please fill all execution parameters");
      return;
    }

    // ✅ Validate call duration is >= 0.1 (minimum 6 seconds)
    const durationValue = Number(callDuration.value);
    if (durationValue < 0.1) {
      alert("Call Duration must be at least 0.1 minutes (6 seconds)");
      return;
    }

    // ✅ Validate iterations is >= 1
    const iterValue = Number(iterations.value);
    if (iterValue < 1) {
      alert("Number of Iterations must be at least 1");
      return;
    }

    // ✅ Validate call delay is >= 0
    const delayValue = Number(callDelay.value);
    if (delayValue < 0) {
      alert("Call Delay cannot be negative");
      return;
    }

    const payload = {
      test_type: testType.value,
      device_count: Number(deviceCount.value),
      mt_number: mtNumbers[1] || "",
      iterations: iterValue,
      call_duration: durationValue,
      call_delay: delayValue,
      pairs: pairs.map(p => ({
        pair_id: p.pairId,
        mo_serial: p.moSerial,
        mt_serial: p.mtSerial,
        mt_number: mtNumbers[p.pairId] || ""
      }))
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
      
      // ✅ Show folder button when test starts
      if (folderBtn) {
        folderBtn.style.display = "block";
      }
      
      // ✅ Navigate to step 3 (Test Execution Screen)
      showStep(3);
      
      startBtn.classList.add("hidden");
      resetBtn.classList.add("hidden");
      retestBtn.classList.add("hidden");
      
      controlButtons.classList.remove("hidden");
      controlButtons.style.display = "flex";
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
        controlButtons.style.display = "none";
        
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
    
    // ✅ Reset device connection state
    alreadyConnectedSerials = [];
    currentConnectingPair = null;
    currentConnectingType = null;
    
    // ✅ Hide folder button on retest
    if (folderBtn) {
      folderBtn.style.display = "none";
    }
    
    startBtn.classList.remove("hidden");
    resetBtn.classList.remove("hidden");
    retestBtn.classList.remove("hidden");
    controlButtons.classList.add("hidden");
    controlButtons.style.display = "none";
    
    showStep(1);
  });

  // Progress monitoring with test completion detection
  let lastProgressRunning = false;

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
      
      const progressRunning = progressData.running === true;
      
      // ✅ DETECT COMPLETION: Progress changed from running to not running
      if (lastProgressRunning === true && progressRunning === false) {
        console.log("✅ Test completed - progress running changed from true to false");
        
        testRunning = false;
        testPaused = false;
        
        // Show Start/Reset/Retest buttons
        startBtn.classList.remove("hidden");
        resetBtn.classList.remove("hidden");
        retestBtn.classList.remove("hidden");
        
        // Hide control buttons
        controlButtons.classList.add("hidden");
        controlButtons.style.display = "none";
        
        // ✅ Show completion alert IMMEDIATELY
        setTimeout(() => {
          if (!statusData.device_disconnected) {
            if (progressData.percent >= 100) {
              alert("Test completed successfully!");
            } else if (statusData.state === "FAILED") {
              alert("Test failed: " + (statusData.message || "Unknown error"));
            }
          }
        }, 100);  // Small delay to ensure UI updates first
      }
      
      lastProgressRunning = progressRunning;

    } catch (e) {
      console.error("Progress polling error:", e);
    }
  }, 1000);

  // Live logs (no auto-scroll)
  setInterval(async () => {
    const logBox = document.getElementById("log-box");
    if (!logBox) return;

    try {
      const res = await fetch("/api/cat-a/logs");
      const logs = await res.json();

      logBox.innerText = logs.join("\n");
      // No auto-scroll - user controls scroll position manually
    } catch (e) {}
  }, 1000);

  // Auto-clear disconnect alerts on home screen
  setInterval(() => {
    const homeScreen = document.getElementById("home-screen");
    if (homeScreen && !homeScreen.classList.contains("hidden")) {
      fetch("/api/cat-a/clear-disconnect", { method: "POST" }).catch(() => {});
      fetch("/api/cat-a/clear-oos", { method: "POST" }).catch(() => {});
    }
  }, 5000);

  // Folder icon button - placeholder for opening output folder
  const folderBtn = document.getElementById("open-output-folder");
  if (folderBtn) {
    // ✅ Hide button initially (show only after test starts)
    folderBtn.style.display = "none";
    
    folderBtn.addEventListener("click", async () => {
      try {
        const response = await fetch("/api/cat-a/open-folder", {
          method: "POST"
        });
        const data = await response.json();
        
        if (data.status === "success") {
          console.log("Opened folder:", data.path);
        } else {
          alert(data.message || "Could not open folder");
        }
      } catch (error) {
        console.error("Error opening folder:", error);
        alert("Failed to open output folder");
      }
    });
  }

});