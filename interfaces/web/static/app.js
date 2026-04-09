const form        = document.getElementById('inputForm');
const input       = document.getElementById('taskInput');
const sendBtn     = document.getElementById('sendBtn');
const chatHistory = document.getElementById('chatHistory');
const hero        = document.getElementById('hero');
const statusHint  = document.getElementById('statusHint');
const modeToggle  = document.getElementById('modeToggle');
const modeLabel   = document.getElementById('modeLabel');
const micBtn      = document.getElementById('micBtn');
const voiceToggle = document.getElementById('voiceToggle');
const voiceLabel  = document.getElementById('voiceLabel');
const wakeToggle  = document.getElementById('wakeToggle');
const wakeLabel   = document.getElementById('wakeLabel');

/* ── Mode toggle ─────────────────────────────────────────── */

let currentMode = 'cloud';

function applyMode(mode) {
  currentMode = mode;
  if (mode === 'local') {
    modeLabel.textContent = 'Local';
    modeToggle.querySelector('.mode-icon').textContent = '🖥️';
    modeToggle.className = 'mode-toggle local';
  } else {
    modeLabel.textContent = 'Cloud';
    modeToggle.querySelector('.mode-icon').textContent = '☁️';
    modeToggle.className = 'mode-toggle cloud';
  }
}

/* ── Voice mode toggle ───────────────────────────────────── */

let voiceModeOn = false;

function applyVoiceMode(enabled) {
  voiceModeOn = enabled;
  voiceToggle.classList.toggle('active', enabled);
  voiceLabel.textContent = enabled ? 'Voice ON' : 'Voice';
}

// Sync mode, voiceMode, and wakeWordActive on load
fetch('/api/status')
  .then(r => r.json())
  .then(d => {
    applyMode(d.mode);
    applyVoiceMode(d.voiceMode ?? false);
    applyWakeWord(d.wakeWordActive ?? false);
  })
  .catch(() => {});

modeToggle.addEventListener('click', async () => {
  const next = currentMode === 'cloud' ? 'local' : 'cloud';
  modeToggle.disabled = true;
  try {
    const res = await fetch('/api/mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: next }),
    });
    const data = await res.json();
    applyMode(data.mode);
    // Show a system message in chat indicating the switch
    const note = document.createElement('div');
    note.style.cssText = 'text-align:center;font-size:11px;color:var(--muted);padding:6px 0;';
    note.textContent = `─── switched to ${data.mode} mode · context cleared ───`;
    chatHistory.appendChild(note);
    scrollToBottom();
  } finally {
    modeToggle.disabled = false;
  }
});

voiceToggle.addEventListener('click', async () => {
  voiceToggle.disabled = true;
  try {
    const res = await fetch('/api/voice-mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: !voiceModeOn }),
    });
    const data = await res.json();
    applyVoiceMode(data.voiceMode);
  } finally {
    voiceToggle.disabled = false;
  }
});

/* ── Wake word toggle ────────────────────────────────────── */

let wakeWordOn = false;

function applyWakeWord(enabled) {
  wakeWordOn = enabled;
  wakeToggle.classList.toggle('active', enabled);
  wakeLabel.textContent = enabled ? 'Listening' : 'Wake';
}

wakeToggle.addEventListener('click', async () => {
  wakeToggle.disabled = true;
  const next = !wakeWordOn;
  // Optimistic UI update so it feels instant
  applyWakeWord(next);
  try {
    const res = await fetch('/api/wake-word', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: next }),
    });
    const data = await res.json();
    applyWakeWord(data.wakeWordActive);
  } catch {
    applyWakeWord(!next);  // revert on error
  } finally {
    wakeToggle.disabled = false;
  }
});

let firstMessage = true;
let currentLoomBubble = null;
let currentLoomText = '';

/* ── Helpers ─────────────────────────────────────────────── */

function hideHero() {
  hero.classList.add('hidden');
}

function appendUserMsg(text) {
  const el = document.createElement('div');
  el.className = 'msg msg-user';
  el.textContent = text;
  chatHistory.appendChild(el);
  scrollToBottom();
}

function createLoomBubble() {
  const el = document.createElement('div');
  el.className = 'msg msg-loom';
  el.innerHTML = '<span class="msg-label">L.O.O.M.</span><span class="msg-body"></span>';

  // typing indicator (3 dots) shown until first text arrives
  const indicator = document.createElement('div');
  indicator.className = 'typing-indicator';
  for (let i = 0; i < 3; i++) {
    const d = document.createElement('div');
    d.className = 'typing-dot';
    indicator.appendChild(d);
  }
  el.appendChild(indicator);

  chatHistory.appendChild(el);
  scrollToBottom();
  return el;
}

function appendToLoomBubble(bubble, text) {
  // Remove typing indicator once real text arrives
  const indicator = bubble.querySelector('.typing-indicator');
  if (indicator) indicator.remove();

  const body = bubble.querySelector('.msg-body');
  currentLoomText += text;
  body.innerHTML = marked.parse(currentLoomText);
  scrollToBottom();
}

function setStatus(text) {
  statusHint.textContent = text;
}

function clearStatus() {
  statusHint.textContent = '';
}

function setLoading(on) {
  sendBtn.disabled = on;
  input.disabled = on;
  micBtn.disabled = on;
}

function scrollToBottom() {
  const main = document.querySelector('.main');
  main.scrollTop = main.scrollHeight;
}

/* ── Submit handler ──────────────────────────────────────── */

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = input.value.trim();
  if (!msg) return;

  // Hide hero on first message
  if (firstMessage) {
    hideHero();
    firstMessage = false;
  }

  input.value = '';
  appendUserMsg(msg);

  // Create LOOM bubble and lock UI
  currentLoomBubble = createLoomBubble();
  currentLoomText = '';
  setStatus('Connecting...');
  setLoading(true);

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg }),
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    // Read the SSE body as a stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Normalize line endings, then split
      const lines = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
      buffer = lines.pop(); // keep incomplete last line

      let currentEvent = null;
      let currentData = null;

      for (const line of lines) {
        if (line.startsWith('event:')) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          currentData = line.slice(5).trim();
        } else if (line === '') {
          // Dispatch whenever we hit a blank separator line (event field is optional)
          if (currentData !== null) {
            handleSSEEvent(currentEvent || 'message', currentData);
          }
          currentEvent = null;
          currentData = null;
        }
      }
    }

  } catch (err) {
    appendToLoomBubble(currentLoomBubble, `Error: ${err.message}`);
  } finally {
    clearStatus();
    setLoading(false);
    input.focus();
  }
});

function handleSSEEvent(event, data) {
  if (event === 'status') {
    setStatus(data);
  } else if (event === 'message') {
    try {
      const parsed = JSON.parse(data);
      appendToLoomBubble(currentLoomBubble, parsed.text || data);
    } catch {
      appendToLoomBubble(currentLoomBubble, data);
    }
  } else if (event === 'done') {
    // If the bubble still only has the typing indicator (no response text), show a fallback
    const indicator = currentLoomBubble && currentLoomBubble.querySelector('.typing-indicator');
    if (indicator) {
      indicator.remove();
      const body = currentLoomBubble.querySelector('.msg-body');
      body.textContent = 'Done.';
    }
    clearStatus();
  }
}

/* ── Mic button (hold-to-record) ─────────────────────────── */

let mediaRecorder = null;
let audioChunks   = [];
let micStream     = null;

async function startRecording() {
  if (mediaRecorder && mediaRecorder.state === 'recording') return;
  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    setStatus('Mic access denied');
    setTimeout(clearStatus, 2000);
    return;
  }

  audioChunks = [];
  const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
    ? 'audio/webm;codecs=opus' : 'audio/webm';
  mediaRecorder = new MediaRecorder(micStream, { mimeType });

  mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) audioChunks.push(e.data);
  };

  mediaRecorder.onstop = async () => {
    micStream.getTracks().forEach(t => t.stop());
    micStream = null;
    micBtn.classList.remove('recording');
    micBtn.disabled = true;
    setStatus('Transcribing...');

    const blob = new Blob(audioChunks, { type: mimeType });
    audioChunks = [];

    try {
      const res = await fetch('/api/voice', {
        method: 'POST',
        headers: { 'Content-Type': mimeType },
        body: blob,
      });
      const data = await res.json();
      if (data.text && data.text.trim()) {
        input.value = data.text.trim();
        clearStatus();
        form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      } else {
        setStatus('Nothing detected — try again');
        setTimeout(clearStatus, 2000);
      }
    } catch (err) {
      setStatus(`Voice error: ${err.message}`);
      setTimeout(clearStatus, 2000);
    } finally {
      micBtn.disabled = false;
    }
  };

  mediaRecorder.start();
  micBtn.classList.add('recording');
  setStatus('Listening... (release to send)');
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop();
}

// Desktop: hold mousedown, release anywhere on the document
micBtn.addEventListener('mousedown', (e) => { e.preventDefault(); startRecording(); });
document.addEventListener('mouseup', stopRecording);

// Mobile: touchstart/touchend
micBtn.addEventListener('touchstart', (e) => { e.preventDefault(); startRecording(); }, { passive: false });
document.addEventListener('touchend', stopRecording);

// Auto-focus input on load
input.focus();
