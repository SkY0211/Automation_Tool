document.addEventListener("DOMContentLoaded", () => {

  /* ===============================
     GLOBAL UI STATE
  =============================== */
  let pairCount = 0;
  let mtNumbers = {};
  let pairs = []; // {pairId, mo, mt, caller, receiver, moConnected, mtConnected, saved}

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
      alert("Please enter an even number of devices");
      return;
    }

    pairCount = count / 2;
    renderPairs(pairCount);
    showStep(2);
  });

  /* ===============================
     RENDER PAIRS (WITH DROPDOWNS)
  =============================== */

  function renderPairs(count) {
    const container = document.getElementById("pair-container");
    container.innerHTML = "";

    pairs = [];
    mtNumbers = {};

    for (let i = 1; i <= count; i++) {
      pairs.push({
        pairId: i,
        mo: "",
        mt: "",
        caller: "",      // 🔥 ADDED
        receiver: "",    // 🔥 ADDED
        moConnected: false,
        mtConnected: false,
        saved: false
      });

      container.innerHTML += `
        <div class="connection-row" data-pair="${i}">
          <span class="pair-label">MO–MT Pair ${i}</span>

          <select class="mo-select">
            <option value="">Select MO (Caller)</option>
          </select>

          <select class="mt-select">
            <option value="">Select MT (Receiver)</option>
          </select>

          <span id="mo-status-${i}" class="status">MO (Caller) Not Connected</span>
          <span id="mt-status-${i}" class="status">MT (Receiver) Not Connected</span>

          <input type="text"
                 class="mt-input"
                 placeholder="Enter MT${i} Phone Number"/>

          <button class="primary small-btn">Save</button>
        </div>
      `;
    }

    startBtn.disabled = true;
  }

  /* ===============================
     SAVE PAIR CONFIG (ENFORCE DIRECTION)
  =============================== */

  document.body.addEventListener("click", (e) => {
    if (!e.target.classList.contains("small-btn")) return;

    const row = e.target.closest(".connection-row");
    const pairId = Number(row.dataset.pair);
    const mo = row.querySelector(".mo-select").value;
    const mt = row.querySelector(".mt-select").value;
    const mtInput = row.querySelector(".mt-input").value;

    if (!mo || !mt) {
      alert("Please select MO and MT devices");
      return;
    }

    // 🔥 CRITICAL VALIDATION
    if (mo === mt) {
      alert("MO and MT must be different devices");
      return;
    }

    if (!mtInput.match(/^[0-9]{8,15}$/)) {
      alert("Enter valid MT phone number");
      return;
    }

    const pair = pairs[pairId - 1];

    pair.mo = mo;
    pair.mt = mt;

    // 🔥 LOCK DIRECTION (THIS FIXES YOUR ISSUE)
    pair.caller = mo;      // MO ALWAYS CALLS
    pair.receiver = mt;    // MT ALWAYS RECEIVES

    pair.saved = true;
    mtNumbers[pairId] = mtInput;

    alert(`Pair ${pairId} saved`);

    if (pairs.every(p => p.saved)) {
      showStep(3);
    }
  });

  /* ===============================
     STATUS POLLING (MANUAL SELECTION)
  =============================== */

  setInterval(async () => {
    try {
      const res = await fetch("/api/cat-a/status");
      const data = await res.json();

      const devices = data.devices || [];

      // Populate dropdowns ONCE
      document.querySelectorAll(".mo-select, .mt-select").forEach(sel => {
        if (sel.options.length > 1) return;
        devices.forEach(d => {
          sel.innerHTML += `<option value="${d}">${d}</option>`;
        });
      });

      pairs.forEach(pair => {
        const moEl = document.getElementById(`mo-status-${pair.pairId}`);
        const mtEl = document.getElementById(`mt-status-${pair.pairId}`);

        pair.moConnected = pair.caller && devices.includes(pair.caller);
        pair.mtConnected = pair.receiver && devices.includes(pair.receiver);

        moEl.textContent = pair.moConnected
          ? `MO (Caller) Connected`
          : `MO (Caller) Not Connected`;
        moEl.classList.toggle("connected", pair.moConnected);

        mtEl.textContent = pair.mtConnected
          ? `MT (Receiver) Connected`
          : `MT (Receiver) Not Connected`;
        mtEl.classList.toggle("connected", pair.mtConnected);
      });

      startBtn.disabled = !pairs.every(
        p => p.saved && p.moConnected && p.mtConnected
      );

    } catch (e) {
      console.error("Status polling failed", e);
    }
  }, 2000);

  /* ===============================
     START TEST (UNCHANGED)
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

    await fetch("/api/cat-a/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    alert("CAT-A Test Started");
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
    pairs = [];
    mtNumbers = {};
    showStep(1);
  });

});
