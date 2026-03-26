document.addEventListener("DOMContentLoaded", () => {

  // ═══════════════════════════════════════════════════════════════════════
  // CAT-A  ── original code, zero changes
  // ═══════════════════════════════════════════════════════════════════════

  let pairCount = 0;
  let mtNumbers = {};
  let pairs = [];
  let testRunning = false;
  let testPaused = false;
  let previousOosState = false;

  const disconnectModal     = document.getElementById("disconnect-modal");
  const closeDisconnectModal = document.getElementById("close-disconnect-modal");
  const disconnectMessage   = document.getElementById("disconnect-message");

  const oosModal      = document.getElementById("oos-modal");
  const closeOosModal = document.getElementById("close-oos-modal");
  const oosMessage    = document.getElementById("oos-message");
  const oosDevicesList = document.getElementById("oos-devices-list");

  const deviceConnectionModal  = document.getElementById("device-connection-modal");
  const deviceConnectionTitle  = document.getElementById("device-connection-title");
  const deviceInstruction      = document.getElementById("device-instruction");
  const connectionStep1        = document.getElementById("connection-step-1");
  const connectionStep2        = document.getElementById("connection-step-2");
  const proceedBtn             = document.getElementById("proceed-connection-btn");
  const confirmDeviceBtn       = document.getElementById("confirm-device-btn");

  if (disconnectModal) {
    disconnectModal.classList.add("hidden");
    disconnectModal.style.display = "none";
    fetch("/api/cat-a/clear-disconnect", { method: "POST" })
      .then(() => console.log("✅ Startup: Alerts cleared"))
      .catch(() => {});
  }

  if (oosModal) {
    oosModal.classList.add("hidden");
    oosModal.style.display = "none";
    fetch("/api/cat-a/clear-oos", { method: "POST" }).catch(() => {});
  }

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
    alreadyConnectedSerials = [];
    currentConnectingPair   = null;
    currentConnectingType   = null;
    mtNumbers = {};
    pairs     = [];
    fetch("/api/cat-a/clear-disconnect", { method: "POST" }).catch(() => {});
    fetch("/api/cat-a/clear-oos",        { method: "POST" }).catch(() => {});
  }

  document.body.addEventListener("click", (event) => {
    if (event.target.closest("#cat-a"))    showCatAScreen();
    if (event.target.closest("#back-home")) showHomeScreen();
  });

  const step1 = document.getElementById("cat-step-1");
  const step2 = document.getElementById("cat-step-2");
  const step3 = document.getElementById("cat-step-3");

  const testType   = document.getElementById("test-type");
  const deviceCount = document.getElementById("device-count");

  const iterations  = document.getElementById("iterations");
  const callDuration = document.getElementById("call-duration");
  const callDelay   = document.getElementById("call-delay");

  const nextBtn   = document.getElementById("next-to-step-2");
  const startBtn  = document.getElementById("start-btn");
  const resetBtn  = document.getElementById("reset-btn");
  const retestBtn = document.getElementById("retest-btn");

  const controlButtons = document.getElementById("control-buttons");
  const pauseBtn  = document.getElementById("pause-btn");
  const resumeBtn = document.getElementById("resume-btn");
  const stopBtn   = document.getElementById("stop-btn");

  function showStep(step) {
    step1.classList.add("hidden");
    step2.classList.add("hidden");
    step3.classList.add("hidden");

    const catInfoPanel = document.getElementById("cat-info-panel");
    const catLayout    = document.getElementById("cat-a-layout");

    if (step === 1) {
      step1.classList.remove("hidden");
      if (catInfoPanel) catInfoPanel.style.visibility = "visible";
      if (catLayout)    catLayout.classList.remove("no-sidebar");
    }
    if (step === 2) {
      step2.classList.remove("hidden");
      if (catInfoPanel) catInfoPanel.style.visibility = "hidden";
      if (catLayout)    catLayout.classList.add("no-sidebar");
    }
    if (step === 3) {
      step3.classList.remove("hidden");
      if (catInfoPanel) catInfoPanel.style.visibility = "hidden";
      if (catLayout)    catLayout.classList.add("no-sidebar");
    }
  }

  nextBtn.addEventListener("click", () => {
    const count = Number(deviceCount.value);
    if (!testType.value || !count) { alert("Please select test type and device count"); return; }
    if (count % 2 !== 0)           { alert("Please enter an even number of devices");   return; }
    pairCount = count / 2;
    renderPairs(pairCount);
    showStep(2);
  });

  function renderPairs(count) {
    const container = document.getElementById("pair-container");
    container.innerHTML = "";
    mtNumbers = {};
    pairs     = [];
    alreadyConnectedSerials = [];
    currentConnectingPair   = null;
    currentConnectingType   = null;

    for (let i = 1; i <= count; i++) {
      pairs.push({
        pairId: i, mo: null, mt: null, moSerial: null, mtSerial: null,
        moSimPref: null, mtSimPref: null,
        moConnected: false, mtConnected: false, saved: false
      });

      container.innerHTML += `
        <div class="connection-row">
          <span class="pair-label">MO–MT Pair ${i}:</span>
          <button class="primary small-btn connect-mo-btn" data-pair="${i}">Connect MO${i}</button>
          <span id="mo-status-${i}" class="status">Not Connected</span>
          <button class="primary small-btn connect-mt-btn" data-pair="${i}" disabled>Connect MT${i}</button>
          <span id="mt-status-${i}" class="status">Not Connected</span>
          <input type="text" class="mt-input" data-pair="${i}"
                 placeholder="Enter MT${i} Phone Number" disabled/>
          <button class="primary small-btn save-btn" data-pair="${i}" disabled>Save</button>
        </div>
      `;
    }
  }

  let currentConnectingPair   = null;
  let currentConnectingType   = null;
  let alreadyConnectedSerials = [];

  document.body.addEventListener("click", async (e) => {
    if (e.target.classList.contains("connect-mo-btn")) {
      const pairId = Number(e.target.dataset.pair);
      currentConnectingPair = pairId;
      currentConnectingType = "mo";
      deviceConnectionTitle.textContent  = `Connect MO${pairId}`;
      deviceInstruction.textContent      = `Connect the MO${pairId} device and click 'Proceed' button`;
      connectionStep1.classList.remove("hidden");
      connectionStep2.classList.add("hidden");
      deviceConnectionModal.classList.remove("hidden");
      deviceConnectionModal.style.display = "flex";
    }

    if (e.target.classList.contains("connect-mt-btn")) {
      const pairId = Number(e.target.dataset.pair);
      currentConnectingPair = pairId;
      currentConnectingType = "mt";
      deviceConnectionTitle.textContent  = `Connect MT${pairId}`;
      deviceInstruction.textContent      = `Connect the MT${pairId} device and click 'Proceed' button`;
      connectionStep1.classList.remove("hidden");
      connectionStep2.classList.add("hidden");
      deviceConnectionModal.classList.remove("hidden");
      deviceConnectionModal.style.display = "flex";
    }

    if (e.target.classList.contains("save-btn")) {
      const pairId = Number(e.target.dataset.pair);
      const input  = document.querySelector(`input[data-pair="${pairId}"]`);
      if (!input.value.match(/^[0-9]{8,15}$/)) { alert(`Enter valid MT number for Pair ${pairId}`); return; }
      mtNumbers[pairId]          = input.value;
      pairs[pairId - 1].saved    = true;
      e.target.disabled          = true;
      input.disabled             = true;
      alert(`MT number saved for Pair ${pairId}`);
      if (pairs.every(p => p.saved)) { showStep(3); }
    }
  });

  proceedBtn.addEventListener("click", async () => {
    proceedBtn.disabled    = true;
    proceedBtn.textContent = "Detecting...";
    try {
      const response = await fetch("/api/cat-a/detect-device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ already_connected: alreadyConnectedSerials })
      });
      const data = await response.json();
      if (data.status === "error" || data.device === "NotFound") {
        alert("No device found. Connect the device properly and try again.");
        proceedBtn.disabled    = false;
        proceedBtn.textContent = "Proceed";
        return;
      }
      document.getElementById("device-udid").textContent    = data.device.serial;
      document.getElementById("device-name").textContent    = data.device.name;
      document.getElementById("device-version").textContent = data.device.android_version;
      document.querySelectorAll('input[name="sim-pref"]').forEach(r => r.checked = false);
      connectionStep1.classList.add("hidden");
      connectionStep2.classList.remove("hidden");
      proceedBtn.disabled    = false;
      proceedBtn.textContent = "Proceed";
    } catch (error) {
      console.error("Device detection error:", error);
      alert("Error detecting device. Please try again.");
      proceedBtn.disabled    = false;
      proceedBtn.textContent = "Proceed";
    }
  });

  confirmDeviceBtn.addEventListener("click", () => {
    const selectedSim = document.querySelector('input[name="sim-pref"]:checked');
    if (!selectedSim) { alert("Please select a SIM preference"); return; }
    const serial  = document.getElementById("device-udid").textContent;
    const name    = document.getElementById("device-name").textContent;
    const simPref = parseInt(selectedSim.value);
    const pair    = pairs[currentConnectingPair - 1];

    if (currentConnectingType === "mo") {
      pair.moSerial = serial; pair.mo = name; pair.moSimPref = simPref; pair.moConnected = true;
      const moStatus        = document.getElementById(`mo-status-${currentConnectingPair}`);
      moStatus.textContent  = `${name} (SIM${simPref + 1})`;
      moStatus.classList.add("connected");
      moStatus.style.color  = "white";
      document.querySelector(`.connect-mt-btn[data-pair="${currentConnectingPair}"]`).disabled = false;
      document.querySelector(`.connect-mo-btn[data-pair="${currentConnectingPair}"]`).disabled = true;
    } else {
      pair.mtSerial = serial; pair.mt = name; pair.mtSimPref = simPref; pair.mtConnected = true;
      const mtStatus        = document.getElementById(`mt-status-${currentConnectingPair}`);
      mtStatus.textContent  = `${name} (SIM${simPref + 1})`;
      mtStatus.classList.add("connected");
      mtStatus.style.color  = "white";
      document.querySelector(`input[data-pair="${currentConnectingPair}"]`).disabled  = false;
      document.querySelector(`.save-btn[data-pair="${currentConnectingPair}"]`).disabled = false;
      document.querySelector(`.connect-mt-btn[data-pair="${currentConnectingPair}"]`).disabled = true;
    }
    alreadyConnectedSerials.push(serial);
    deviceConnectionModal.classList.add("hidden");
    deviceConnectionModal.style.display = "none";
  });

  setInterval(async () => {
    const s3 = document.getElementById("cat-step-3");
    if (!s3 || s3.classList.contains("hidden")) return;
    try {
      const res  = await fetch("/api/cat-a/status");
      const data = await res.json();
      if (!data.pairs || data.pairs.length === 0) return;
      data.pairs.forEach((pair, index) => {
        const pairId = index + 1;
        const moEl   = document.getElementById(`mo-status-${pairId}`);
        const mtEl   = document.getElementById(`mt-status-${pairId}`);
        if (!moEl || !mtEl) return;
        moEl.textContent = pair.mo_connected ? `MO${pairId} Connected` : `MO${pairId} Not Connected`;
        moEl.classList.toggle("connected", pair.mo_connected === true);
        mtEl.textContent = pair.mt_connected ? `MT${pairId} Connected` : `MT${pairId} Not Connected`;
        mtEl.classList.toggle("connected", pair.mt_connected === true);
        if (pairs[pairId - 1]) {
          pairs[pairId - 1].moConnected = pair.mo_connected === true;
          pairs[pairId - 1].mtConnected = pair.mt_connected === true;
        }
      });
    } catch (e) { console.error("Status polling failed", e); }
  }, 2000);

  setInterval(() => {
    if (startBtn && pairs.length > 0 && !testRunning)
      startBtn.disabled = !pairs.every(p => p.saved && p.moConnected && p.mtConnected);
  }, 500);

  setInterval(async () => {
    const homeScreen = document.getElementById("home-screen");
    if (homeScreen && !homeScreen.classList.contains("hidden")) return;
    const s3 = document.getElementById("cat-step-3");
    if (!s3 || s3.classList.contains("hidden")) return;
    try {
      const res  = await fetch("/api/cat-a/status");
      const data = await res.json();
      if (!data.test_running) return;
      if (data.device_disconnected === true && data.test_running === true) {
        disconnectMessage.textContent =
          "A device has been disconnected during the test. The test has been PAUSED. " +
          "Please reconnect the device and click Resume to continue.";
        disconnectModal.classList.remove("hidden");
        disconnectModal.style.display = "flex";
        testPaused = true;
        pauseBtn.classList.add("hidden");
        resumeBtn.classList.remove("hidden");
        await fetch("/api/cat-a/clear-disconnect", { method: "POST" });
      }
    } catch (e) { console.error("Disconnect monitoring failed", e); }
  }, 2000);

  if (closeDisconnectModal) {
    closeDisconnectModal.addEventListener("click", async () => {
      disconnectModal.classList.add("hidden");
      disconnectModal.style.display = "none";
      await fetch("/api/cat-a/clear-disconnect", { method: "POST" }).catch(() => {});
    });
  }

  setInterval(async () => {
    const homeScreen = document.getElementById("home-screen");
    if (homeScreen && !homeScreen.classList.contains("hidden")) return;
    const s3 = document.getElementById("cat-step-3");
    if (!s3 || s3.classList.contains("hidden")) return;
    try {
      const res  = await fetch("/api/cat-a/status");
      const data = await res.json();
      if (data.oos_detected === true && data.test_running === true) {
        if (previousOosState === false) {
          previousOosState = true;
          const list = document.getElementById("oos-devices-list");
          if (list) list.textContent = "A device has entered an Out of Service zone";
          if (oosModal) { oosModal.style.display = "flex"; oosModal.classList.remove("hidden"); }
          try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc  = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            osc.frequency.value = 800; osc.type = "sine";
            gain.gain.setValueAtTime(0.3, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.2);
            osc.start(ctx.currentTime); osc.stop(ctx.currentTime + 0.2);
          } catch (e) {}
          setTimeout(() => {
            if (oosModal) { oosModal.style.display = "none"; oosModal.classList.add("hidden"); }
          }, 4000);
        }
      } else {
        if (previousOosState === true) previousOosState = false;
      }
    } catch (e) { console.error("OOS monitoring failed", e); }
  }, 2000);

  if (closeOosModal) {
    closeOosModal.addEventListener("click", async () => {
      oosModal.classList.add("hidden");
      oosModal.style.display = "none";
      await fetch("/api/cat-a/clear-oos", { method: "POST" }).catch(() => {});
    });
  }

  startBtn.addEventListener("click", async () => {
    if (!iterations.value || !callDuration.value || !callDelay.value) {
      alert("Please fill all execution parameters"); return;
    }
    const durationValue = Number(callDuration.value);
    if (durationValue < 0.1) { alert("Call Duration must be at least 0.1 minutes (6 seconds)"); return; }
    const iterValue = Number(iterations.value);
    if (iterValue < 1)       { alert("Number of Iterations must be at least 1");                return; }
    const delayValue = Number(callDelay.value);
    if (delayValue < 0)      { alert("Call Delay cannot be negative");                          return; }

    const payload = {
      test_type:    testType.value,
      device_count: Number(deviceCount.value),
      mt_number:    mtNumbers[1] || "",
      iterations:   iterValue,
      call_duration: durationValue,
      call_delay:   delayValue,
      pairs: pairs.map(p => ({
        pair_id:   p.pairId,
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
      testRunning = true; testPaused = false;
      const logBox = document.getElementById("log-box");
      if (logBox) logBox.innerText = "Test started...\n";
      if (folderBtn) folderBtn.style.display = "block";
      showStep(3);
      startBtn.classList.add("hidden"); resetBtn.classList.add("hidden"); retestBtn.classList.add("hidden");
      controlButtons.classList.remove("hidden"); controlButtons.style.display = "flex";
      pauseBtn.classList.remove("hidden"); resumeBtn.classList.add("hidden");
    } catch (err) { console.error(err); alert("Failed to start test"); }
  });

  pauseBtn.addEventListener("click", async () => {
    try {
      const res  = await fetch("/api/cat-a/pause", { method: "POST" });
      const data = await res.json();
      if (data.status === "success") {
        testPaused = true; pauseBtn.classList.add("hidden"); resumeBtn.classList.remove("hidden");
      } else { alert(data.message || "Failed to pause test"); }
    } catch (err) { console.error(err); alert("Failed to pause test"); }
  });

  resumeBtn.addEventListener("click", async () => {
    try {
      const res  = await fetch("/api/cat-a/resume", { method: "POST" });
      const data = await res.json();
      if (data.status === "success") {
        testPaused = false; resumeBtn.classList.add("hidden"); pauseBtn.classList.remove("hidden");
      } else { alert(data.message || "Failed to resume test"); }
    } catch (err) { console.error(err); alert("Failed to resume test"); }
  });

  stopBtn.addEventListener("click", async () => {
    if (!confirm("Are you sure you want to stop the test?")) return;
    try {
      const res  = await fetch("/api/cat-a/stop", { method: "POST" });
      const data = await res.json();
      if (data.status === "success") {
        testRunning = false; testPaused = false;
        startBtn.classList.remove("hidden"); resetBtn.classList.remove("hidden"); retestBtn.classList.remove("hidden");
        controlButtons.classList.add("hidden"); controlButtons.style.display = "none";
      } else { alert(data.message || "Failed to stop test"); }
    } catch (err) { console.error(err); alert("Failed to stop test"); }
  });

  resetBtn.addEventListener("click", () => {
    iterations.value = ""; callDuration.value = ""; callDelay.value = "";
  });

  retestBtn.addEventListener("click", () => {
    mtNumbers = {}; pairs = []; testRunning = false; testPaused = false;
    alreadyConnectedSerials = []; currentConnectingPair = null; currentConnectingType = null;
    if (folderBtn) folderBtn.style.display = "none";
    startBtn.classList.remove("hidden"); resetBtn.classList.remove("hidden"); retestBtn.classList.remove("hidden");
    controlButtons.classList.add("hidden"); controlButtons.style.display = "none";
    showStep(1);
  });

  let lastProgressRunning = false;

  setInterval(async () => {
    try {
      const progressRes  = await fetch("/api/cat-a/progress");
      const progressData = await progressRes.json();
      const progressBar  = document.getElementById("progress-bar");
      const progressText = document.getElementById("progress-text");
      if (progressBar && progressText) {
        progressBar.value      = progressData.percent || 0;
        progressText.innerText = `Progress: ${progressData.percent || 0}%`;
      }
      const statusRes  = await fetch("/api/cat-a/status");
      const statusData = await statusRes.json();
      const progressRunning = progressData.running === true;
      if (lastProgressRunning === true && progressRunning === false) {
        testRunning = false; testPaused = false;
        startBtn.classList.remove("hidden"); resetBtn.classList.remove("hidden"); retestBtn.classList.remove("hidden");
        controlButtons.classList.add("hidden"); controlButtons.style.display = "none";
        setTimeout(() => {
          if (!statusData.device_disconnected) {
            if (progressData.percent >= 100) alert("Test completed successfully!");
            else if (statusData.state === "FAILED") alert("Test failed: " + (statusData.message || "Unknown error"));
          }
        }, 100);
      }
      lastProgressRunning = progressRunning;
    } catch (e) { console.error("Progress polling error:", e); }
  }, 1000);

  setInterval(async () => {
    const logBox = document.getElementById("log-box");
    if (!logBox) return;
    try {
      const res  = await fetch("/api/cat-a/logs");
      const logs = await res.json();
      logBox.innerText = logs.join("\n");
    } catch (e) {}
  }, 1000);

  setInterval(() => {
    const homeScreen = document.getElementById("home-screen");
    if (homeScreen && !homeScreen.classList.contains("hidden")) {
      fetch("/api/cat-a/clear-disconnect", { method: "POST" }).catch(() => {});
      fetch("/api/cat-a/clear-oos",        { method: "POST" }).catch(() => {});
    }
  }, 5000);

  const folderBtn = document.getElementById("open-output-folder");
  if (folderBtn) {
    folderBtn.style.display = "none";
    folderBtn.addEventListener("click", async () => {
      try {
        const response = await fetch("/api/cat-a/open-folder", { method: "POST" });
        const data     = await response.json();
        if (data.status === "success") console.log("Opened folder:", data.path);
        else alert(data.message || "Could not open folder");
      } catch (error) { console.error("Error opening folder:", error); alert("Failed to open output folder"); }
    });
  }

  // ═══════════════════════════════════════════════════════════════════════
  // CAT-F  ── fully self-contained IIFE, no CAT-A variables shared
  // ═══════════════════════════════════════════════════════════════════════

  (function initCatF() {

    // ── Country list ───────────────────────────────────────────────────
    const COUNTRIES = [
      { c: "Afghanistan",           code: "+93"  },
      { c: "Albania",               code: "+355" },
      { c: "Algeria",               code: "+213" },
      { c: "Argentina",             code: "+54"  },
      { c: "Australia",             code: "+61"  },
      { c: "Austria",               code: "+43"  },
      { c: "Bangladesh",            code: "+880" },
      { c: "Belgium",               code: "+32"  },
      { c: "Brazil",                code: "+55"  },
      { c: "Canada",                code: "+1"   },
      { c: "Chile",                 code: "+56"  },
      { c: "China",                 code: "+86"  },
      { c: "Colombia",              code: "+57"  },
      { c: "Czech Republic",        code: "+420" },
      { c: "Denmark",               code: "+45"  },
      { c: "Egypt",                 code: "+20"  },
      { c: "Ethiopia",              code: "+251" },
      { c: "Finland",               code: "+358" },
      { c: "France",                code: "+33"  },
      { c: "Germany",               code: "+49"  },
      { c: "Ghana",                 code: "+233" },
      { c: "Greece",                code: "+30"  },
      { c: "Hungary",               code: "+36"  },
      { c: "India",                 code: "+91"  },
      { c: "Indonesia",             code: "+62"  },
      { c: "Iran",                  code: "+98"  },
      { c: "Iraq",                  code: "+964" },
      { c: "Ireland",               code: "+353" },
      { c: "Israel",                code: "+972" },
      { c: "Italy",                 code: "+39"  },
      { c: "Japan",                 code: "+81"  },
      { c: "Jordan",                code: "+962" },
      { c: "Kazakhstan",            code: "+7"   },
      { c: "Kenya",                 code: "+254" },
      { c: "Kuwait",                code: "+965" },
      { c: "Lebanon",               code: "+961" },
      { c: "Malaysia",              code: "+60"  },
      { c: "Mexico",                code: "+52"  },
      { c: "Morocco",               code: "+212" },
      { c: "Netherlands",           code: "+31"  },
      { c: "New Zealand",           code: "+64"  },
      { c: "Nigeria",               code: "+234" },
      { c: "Norway",                code: "+47"  },
      { c: "Pakistan",              code: "+92"  },
      { c: "Philippines",           code: "+63"  },
      { c: "Poland",                code: "+48"  },
      { c: "Portugal",              code: "+351" },
      { c: "Qatar",                 code: "+974" },
      { c: "Romania",               code: "+40"  },
      { c: "Russia",                code: "+7"   },
      { c: "Saudi Arabia",          code: "+966" },
      { c: "Singapore",             code: "+65"  },
      { c: "South Africa",          code: "+27"  },
      { c: "South Korea",           code: "+82"  },
      { c: "Spain",                 code: "+34"  },
      { c: "Sri Lanka",             code: "+94"  },
      { c: "Sweden",                code: "+46"  },
      { c: "Switzerland",           code: "+41"  },
      { c: "Taiwan",                code: "+886" },
      { c: "Tanzania",              code: "+255" },
      { c: "Thailand",              code: "+66"  },
      { c: "Tunisia",               code: "+216" },
      { c: "Turkey",                code: "+90"  },
      { c: "UAE",                   code: "+971" },
      { c: "Uganda",                code: "+256" },
      { c: "Ukraine",               code: "+380" },
      { c: "United Kingdom",        code: "+44"  },
      { c: "United States",         code: "+1"   },
      { c: "Venezuela",             code: "+58"  },
      { c: "Vietnam",               code: "+84"  },
    ];

    // ── DOM refs ───────────────────────────────────────────────────────
    const catFCard    = document.getElementById("cat-f");
    const catFScreen  = document.getElementById("cat-f-screen");
    const homeScr     = document.getElementById("home-screen");
    const backBtnCatF = document.getElementById("back-home-catf");

    const catfStep1     = document.getElementById("catf-step-1");
    const catfStep2     = document.getElementById("catf-step-2");
    const catfInfoPanel = document.getElementById("catf-info-panel");
    const catfLayout    = document.getElementById("cat-f-layout");

    const countrySearch = document.getElementById("catf-country-search");
    const countrySelect = document.getElementById("catf-country-code");
    const catfTestType  = document.getElementById("catf-test-type");
    const catfMoPort    = document.getElementById("catf-mo-port");
    const catfMoPhone   = document.getElementById("catf-mo-phone");
    const catfMoSw      = document.getElementById("catf-mo-sw");
    const catfMoImei    = document.getElementById("catf-mo-imei");
    const catfMtPort    = document.getElementById("catf-mt-port");
    const catfMtPhone   = document.getElementById("catf-mt-phone");
    const catfMtSw      = document.getElementById("catf-mt-sw");
    const catfMtImei    = document.getElementById("catf-mt-imei");
    const catfNextBtn   = document.getElementById("catf-next-btn");

    const catfIterations = document.getElementById("catf-iterations");
    const catfDuration   = document.getElementById("catf-call-duration");
    const catfDelay      = document.getElementById("catf-call-delay");
    const catfDevSummary = document.getElementById("catf-device-summary");
    const catfProgressBar = document.getElementById("catf-progress-bar");
    const catfProgressTxt = document.getElementById("catf-progress-text");
    const catfStatusBadge = document.getElementById("catf-status-badge");
    const catfPreRunActs  = document.getElementById("catf-pre-run-actions");
    const catfControlBtns = document.getElementById("catf-control-buttons");
    const catfBackBtn     = document.getElementById("catf-back-btn");
    const catfResetBtn    = document.getElementById("catf-reset-btn");
    const catfStartBtn    = document.getElementById("catf-start-btn");
    const catfPauseBtn    = document.getElementById("catf-pause-btn");
    const catfResumeBtn   = document.getElementById("catf-resume-btn");
    const catfStopBtn     = document.getElementById("catf-stop-btn");
    const catfLogBox      = document.getElementById("catf-log-box");
    const catfFolderBtn   = document.getElementById("catf-open-folder");

    const catfDisconModal      = document.getElementById("catf-disconnect-modal");
    const catfDisconMsg        = document.getElementById("catf-disconnect-message");
    const catfCloseDisconModal = document.getElementById("catf-close-disconnect-modal");

    // ── State ──────────────────────────────────────────────────────────
    let catfRunning     = false;
    let catfPaused      = false;
    let catfLastRunning = false;
    let catfPollTimer   = null;
    let catfLogTimer    = null;

    // ── Populate country dropdown ──────────────────────────────────────
    function populateCountries(filter) {
      countrySelect.innerHTML = "";
      const list = filter
        ? COUNTRIES.filter(x =>
            x.c.toLowerCase().includes(filter.toLowerCase()) ||
            x.code.includes(filter))
        : COUNTRIES;

      list.forEach(x => {
        const opt       = document.createElement("option");
        opt.value       = x.code;
        opt.textContent = `${x.c}  (${x.code})`;
        if (x.c === "India") opt.selected = true;
        countrySelect.appendChild(opt);
      });
    }

    populateCountries("");
    countrySearch.addEventListener("input", () => populateCountries(countrySearch.value.trim()));

    // ── Screen navigation ──────────────────────────────────────────────
    function openCatF() {
      homeScr.classList.add("hidden");
      catFScreen.classList.remove("hidden");
      showCatFStep(1);
    }

    function closeCatF() {
      stopCatFPolling();
      catFScreen.classList.add("hidden");
      homeScr.classList.remove("hidden");
      resetCatFUI();
    }

    function showCatFStep(n) {
      catfStep1.classList.add("hidden");
      catfStep2.classList.add("hidden");
      if (n === 1) {
        catfStep1.classList.remove("hidden");
        if (catfInfoPanel) catfInfoPanel.style.visibility = "visible";
        if (catfLayout)    catfLayout.classList.remove("no-sidebar");
      }
      if (n === 2) {
        catfStep2.classList.remove("hidden");
        if (catfInfoPanel) catfInfoPanel.style.visibility = "hidden";
        if (catfLayout)    catfLayout.classList.add("no-sidebar");
      }
    }

    catFCard.addEventListener("click",    openCatF);
    backBtnCatF.addEventListener("click", closeCatF);

    // ── Validation ─────────────────────────────────────────────────────
    function isValidPort(v)  { return /^COM\d+$/i.test(v.trim()); }
    function isValidPhone(v) { return /^\+?[0-9]{7,15}$/.test(v.trim()); }

    // ── Step 1 → Step 2 ────────────────────────────────────────────────
    catfNextBtn.addEventListener("click", () => {
      const moPort  = catfMoPort.value.trim();
      const mtPort  = catfMtPort.value.trim();
      const moPhone = catfMoPhone.value.trim();
      const mtPhone = catfMtPhone.value.trim();

      if (!moPort  || !isValidPort(moPort))   { alert("Enter a valid MO COM port (e.g. COM11)");  catfMoPort.focus();  return; }
      if (!mtPort  || !isValidPort(mtPort))   { alert("Enter a valid MT COM port (e.g. COM32)");  catfMtPort.focus();  return; }
      if (!moPhone || !isValidPhone(moPhone)) { alert("Enter a valid MO phone number");            catfMoPhone.focus(); return; }
      if (!mtPhone || !isValidPhone(mtPhone)) { alert("Enter a valid MT phone number");            catfMtPhone.focus(); return; }
      if (moPort.toUpperCase() === mtPort.toUpperCase()) { alert("MO and MT ports cannot be the same"); return; }

      // Build summary strip
      const code = countrySelect.value || "+91";
      catfDevSummary.innerHTML = `
        <div class="catf-badge">📱 MO: <strong>${moPort}</strong> &nbsp;·&nbsp; ${moPhone}</div>
        <div class="catf-badge">📱 MT: <strong>${mtPort}</strong> &nbsp;·&nbsp; ${mtPhone}</div>
        <div class="catf-badge">🌐 ${code} &nbsp;·&nbsp; ${catfTestType.value}</div>
      `;
      showCatFStep(2);
    });

    // ── Step 2 back ────────────────────────────────────────────────────
    catfBackBtn.addEventListener("click", () => showCatFStep(1));

    // ── Reset params ───────────────────────────────────────────────────
    catfResetBtn.addEventListener("click", () => {
      catfIterations.value = "10";
      catfDuration.value   = "30";
      catfDelay.value      = "5";
    });

    // ── Start test ─────────────────────────────────────────────────────
    catfStartBtn.addEventListener("click", async () => {
      const itr = parseInt(catfIterations.value);
      const dur = parseInt(catfDuration.value);
      const dly = parseInt(catfDelay.value);

      if (!itr || itr < 1)        { alert("Iterations must be at least 1");          return; }
      if (!dur || dur < 5)        { alert("Call Duration must be at least 5 seconds"); return; }
      if (isNaN(dly) || dly < 0) { alert("Call Delay cannot be negative");            return; }

      const payload = {
        mo_port:       catfMoPort.value.trim(),
        mt_port:       catfMtPort.value.trim(),
        mo_phone:      catfMoPhone.value.trim(),
        mt_phone:      catfMtPhone.value.trim(),
        mo_sw:         catfMoSw.value.trim()   || "N/A",
        mt_sw:         catfMtSw.value.trim()   || "N/A",
        mo_imei:       catfMoImei.value.trim() || "N/A",
        mt_imei:       catfMtImei.value.trim() || "N/A",
        test_type:     catfTestType.value,
        iterations:    itr,
        call_duration: dur,
        call_delay:    dly,
        country_code:  countrySelect.value || "+91",
      };

      try {
        const res  = await fetch("/api/cat-f/start", {
          method:  "POST",
          headers: { "Content-Type": "application/json" },
          body:    JSON.stringify(payload),
        });
        const data = await res.json();

        if (data.status !== "started") {
          alert("Failed to start: " + (data.message || "unknown error"));
          return;
        }

        catfRunning     = true;
        catfPaused      = false;
        catfLastRunning = false;

        catfLogBox.innerText      = "Test started…\n";
        catfProgressBar.value     = 0;
        catfProgressTxt.innerText = "Progress: 0%";
        catfFolderBtn.style.display = "block";

        setBadge("running", "▶ Running");
        catfPreRunActs.classList.add("hidden");
        catfControlBtns.classList.remove("hidden");
        catfControlBtns.style.display = "flex";
        catfPauseBtn.classList.remove("hidden");
        catfResumeBtn.classList.add("hidden");

        startCatFPolling();

      } catch (err) {
        console.error("CAT-F start error:", err);
        alert("Failed to start CAT-F test. Check console for details.");
      }
    });

    // ── Pause ──────────────────────────────────────────────────────────
    catfPauseBtn.addEventListener("click", async () => {
      try {
        const res  = await fetch("/api/cat-f/pause", { method: "POST" });
        const data = await res.json();
        if (data.status === "success") {
          catfPaused = true;
          catfPauseBtn.classList.add("hidden");
          catfResumeBtn.classList.remove("hidden");
          setBadge("paused", "⏸ Paused");
        } else { alert(data.message || "Failed to pause"); }
      } catch (e) { alert("Failed to pause test"); }
    });

    // ── Resume ─────────────────────────────────────────────────────────
    catfResumeBtn.addEventListener("click", async () => {
      try {
        const res  = await fetch("/api/cat-f/resume", { method: "POST" });
        const data = await res.json();
        if (data.status === "success") {
          catfPaused = false;
          catfResumeBtn.classList.add("hidden");
          catfPauseBtn.classList.remove("hidden");
          setBadge("running", "▶ Running");
        } else { alert(data.message || "Failed to resume"); }
      } catch (e) { alert("Failed to resume test"); }
    });

    // ── Stop ───────────────────────────────────────────────────────────
    catfStopBtn.addEventListener("click", async () => {
      if (!confirm("Are you sure you want to stop the CAT-F test?")) return;
      try {
        const res  = await fetch("/api/cat-f/stop", { method: "POST" });
        const data = await res.json();
        if (data.status === "success") {
          onTestEnded("stopped");
        } else { alert(data.message || "Failed to stop"); }
      } catch (e) { alert("Failed to stop test"); }
    });

    // ── Folder button ──────────────────────────────────────────────────
    catfFolderBtn.addEventListener("click", async () => {
      try {
        const res  = await fetch("/api/cat-f/open-folder", { method: "POST" });
        const data = await res.json();
        if (data.status !== "success") alert(data.message || "Could not open folder");
      } catch (e) { alert("Failed to open output folder"); }
    });

    // ── Disconnect modal close ─────────────────────────────────────────
    if (catfCloseDisconModal) {
      catfCloseDisconModal.addEventListener("click", () => {
        catfDisconModal.classList.add("hidden");
        catfDisconModal.style.display = "none";
      });
    }

    // ── Status polling ─────────────────────────────────────────────────
    function startCatFPolling() {
      stopCatFPolling();

      catfPollTimer = setInterval(async () => {
        if (catFScreen.classList.contains("hidden")) return;
        try {
          const res  = await fetch("/api/cat-f/status");
          const data = await res.json();

          // Progress
          const pct = data.progress || 0;
          catfProgressBar.value     = pct;
          catfProgressTxt.innerText =
            `Progress: ${pct}%  (${data.current_iteration || 0} / ${data.total_iterations || 0} iterations)`;

          // Detect completion
          const nowRunning = data.test_running === true;
          if (catfLastRunning && !nowRunning) {
            if      (data.state === "DONE")    onTestEnded("done");
            else if (data.state === "STOPPED") onTestEnded("stopped");
            else if (data.state === "ERROR")   onTestEnded("error", data.message);
          }
          catfLastRunning = nowRunning;

          // Running badge update
          if (nowRunning && !catfPaused) {
            setBadge("running",
              `▶ Running — iter ${data.current_iteration || 0}/${data.total_iterations || 0}`);
          }

          // Device disconnection during test
          if (data.device_disconnected && nowRunning) {
            catfDisconMsg.textContent =
              "A device disconnected. Test paused. Reconnect and click Resume.";
            catfDisconModal.classList.remove("hidden");
            catfDisconModal.style.display = "flex";
            catfPaused = true;
            catfPauseBtn.classList.add("hidden");
            catfResumeBtn.classList.remove("hidden");
            setBadge("paused", "⏸ Paused — device disconnected");
          }

        } catch (e) { /* network hiccup — ignore */ }
      }, 1000);

      catfLogTimer = setInterval(async () => {
        if (catFScreen.classList.contains("hidden")) return;
        try {
          const res  = await fetch("/api/cat-f/logs");
          const logs = await res.json();
          // Auto-scroll only when user is already at bottom
          const atBottom =
            catfLogBox.scrollHeight - catfLogBox.scrollTop <= catfLogBox.clientHeight + 30;
          catfLogBox.innerText = logs.join("\n");
          if (atBottom) catfLogBox.scrollTop = catfLogBox.scrollHeight;
        } catch (e) {}
      }, 1000);
    }

    function stopCatFPolling() {
      if (catfPollTimer) { clearInterval(catfPollTimer); catfPollTimer = null; }
      if (catfLogTimer)  { clearInterval(catfLogTimer);  catfLogTimer  = null; }
    }

    // ── Post-test UI ───────────────────────────────────────────────────
    function onTestEnded(reason, errMsg) {
      catfRunning = false;
      catfPaused  = false;
      stopCatFPolling();

      catfControlBtns.classList.add("hidden");
      catfControlBtns.style.display = "none";
      catfPreRunActs.classList.remove("hidden");

      if (reason === "done") {
        catfProgressBar.value     = 100;
        catfProgressTxt.innerText = "Progress: 100%";
        setBadge("done", "✅ Test completed");
        setTimeout(() => alert("CAT-F test completed successfully!\nReport saved to the output folder."), 100);
      } else if (reason === "stopped") {
        setBadge("stopped", "⏹ Stopped by user");
      } else if (reason === "error") {
        setBadge("error", "❌ Error: " + (errMsg || "unknown"));
        setTimeout(() => alert("CAT-F test error:\n" + (errMsg || "unknown")), 100);
      }
    }

    function resetCatFUI() {
      catfRunning     = false;
      catfPaused      = false;
      catfLastRunning = false;
      catfProgressBar.value     = 0;
      catfProgressTxt.innerText = "Progress: 0%";
      catfLogBox.innerText      = "";
      catfFolderBtn.style.display = "none";
      catfControlBtns.classList.add("hidden");
      catfControlBtns.style.display = "none";
      catfPreRunActs.classList.remove("hidden");
      catfStatusBadge.className = "status-badge hidden";
    }

    function setBadge(type, text) {
      catfStatusBadge.className   = `status-badge badge-${type}`;
      catfStatusBadge.textContent = text;
    }

  })(); // end initCatF

});