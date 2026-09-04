let currentQueue = [];
let currentIndex = -1;
let activePlayer = null;

// --- Auth Management Functions ---

async function handleLogin() {
    const usernameInput = document.getElementById('auth-username');
    const passwordInput = document.getElementById('auth-password');
    const errorEl = document.getElementById('auth-error');

    errorEl.classList.add('d-none');

    const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            username: usernameInput.value,
            password: passwordInput.value
        })
    });

    const data = await res.json();
    if (res.ok) {
        updateUserUI(data.username);
        const modalEl = document.getElementById('authModal');
        const modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();
        usernameInput.value = '';
        passwordInput.value = '';
    } else {
        errorEl.innerText = data.error || 'Login failed';
        errorEl.classList.remove('d-none');
    }
}

async function handleRegister() {
    const usernameInput = document.getElementById('auth-username');
    const passwordInput = document.getElementById('auth-password');
    const errorEl = document.getElementById('auth-error');

    errorEl.classList.add('d-none');

    const res = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            username: usernameInput.value,
            password: passwordInput.value
        })
    });

    const data = await res.json();
    if (res.ok) {
        // Automatically log in after registration
        handleLogin();
    } else {
        errorEl.innerText = data.error || 'Registration failed';
        errorEl.classList.remove('d-none');
    }
}

async function handleLogout() {
    await fetch('/api/logout', { method: 'POST' });
    updateUserUI(null);
}

function updateUserUI(username) {
    const userDisplay = document.getElementById('user-display');
    const authBtn = document.getElementById('auth-btn');

    if (username) {
        userDisplay.innerText = `Logged in as: ${username}`;
        authBtn.innerText = 'Logout';
        authBtn.onclick = handleLogout;
        authBtn.removeAttribute('data-bs-toggle');
        authBtn.removeAttribute('data-bs-target');
    } else {
        userDisplay.innerText = '';
        authBtn.innerText = 'Login';
        authBtn.onclick = null;
        authBtn.setAttribute('data-bs-toggle', 'modal');
        authBtn.setAttribute('data-bs-target', '#authModal');
    }
}


// --- Playlist & Feed Loading ---

async function loadFeed(path, type="avfiles") {
    const res = await fetch(`/api/feed/${encodeURIComponent(path)}`);
    const data = await res.json();
    currentQueue = data.items;

    const infoId = type + "_info";
    const playlistId = type + "_playlist";
    const tabTarget = type + "cast-tab";    

    const infoElement = document.getElementById(infoId);
    if (infoElement) {
        infoElement.innerHTML = `<h4>${data.title}</h4><p>${data.description}</p>`;
    }

    const rssLink = document.getElementById(type + '_rss-link');
    if (rssLink && data.link) {
        rssLink.href = data.link.replace('http', 'podcast');
    }

    const list = document.getElementById(playlistId);
    if (list) {
        list.innerHTML = '';
        data.items.forEach((item, index) => {
            const li = document.createElement('li');
            li.className = "list-group-item list-group-item-action";
            li.innerText = item.title;
            li.onclick = () => playItem(index, type);
            list.appendChild(li);
        });
    }

    const tabTrigger = document.getElementById(tabTarget);
    if (tabTrigger) {
        const tab = new bootstrap.Tab(tabTrigger);
        tab.show();   
    }
}

async function playItem(index, type='avfiles') {
    if (index >= currentQueue.length) return;
    currentIndex = index;
    const item = currentQueue[index];
    const id = type + "_item_extra";

    const extraContainer = document.getElementById(id);
    if (extraContainer) {
        extraContainer.innerHTML = `
        <div class="container-fluid">
            <a class="navbar-brand" href="#"><img src="/static/logo.light.png" height="30"></a>
        </div>
        <hr />
        <p><strong>Title:</strong> ${item.title}</p>
        <p><strong>Published:</strong> ${item.pubDate || ''}</p>
        <hr />
        <div>
            <strong>Description:</strong><br />
            <p>${item.description || ''}</p>
            ${item.transcript || ''}
        </div>
        `;

        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-outline-secondary mt-2';
        editBtn.innerText = '✏️ Edit Episode';
        editBtn.onclick = () => openEditModal({
           file_path: item.file_path || '',
           title: item.title || '',
           description: item.description || ''
        });
        extraContainer.appendChild(editBtn);
    }

    // Show Media Overlay Player
    const overlay = document.getElementById('media-overlay');
    const content = document.getElementById('media-content');
    overlay.classList.remove('d-none');
    
    const isVideo = item.media_type && item.media_type.includes('video');
    content.innerHTML = isVideo 
        ? `<video id="main-player" controls style="width: 100%;"></video>`
        : `<audio id="main-player" controls style="width: 100%;"></audio>`;

    document.getElementById('now-playing-title').innerText = item.title;

    // Attach tracking player class to main element
    activePlayer = new DircastPlayer('main-player');
    
    // Auto-advance queue on track completion
    activePlayer.player.onended = () => {
        activePlayer.saveProgress(0);
        if (currentIndex < currentQueue.length - 1) {
            playItem(currentIndex + 1, type);
        }
    };

    // Load file with state, views, and saved notes
    await activePlayer.loadMedia(item.file_path || item.media_url, item.media_url);
}

function playAll() { if (currentQueue.length > 0) playItem(0); }

function toggleMinimize() { 
    document.getElementById('media-overlay').classList.toggle('minimized'); 
}

function closePlayer() {
    if (activePlayer) {
        activePlayer.saveProgress();
    }
    const content = document.getElementById('media-content');
    content.innerHTML = '';
    document.getElementById('media-overlay').classList.add('d-none');
}

// --- Note Taking Functions ---

async function submitNote() {
    const noteInput = document.getElementById('note-input');
    const content = noteInput.value.trim();

    if (!content || !activePlayer) return;

    await activePlayer.addNote(content);
    noteInput.value = '';
}

function renderNotes(notes) {
    const list = document.getElementById('notes-list');
    if (!list) return;

    list.innerHTML = '';

    if (notes.length === 0) {
        list.innerHTML = '<small class="text-muted d-block p-1">No notes yet for this episode.</small>';
        return;
    }

    notes.forEach(note => {
        const div = document.createElement('div');
        div.className = 'd-flex justify-content-between align-items-center mb-1 bg-secondary bg-opacity-25 rounded p-1';
        
        const timestampStr = formatTime(note.timestamp);
        div.innerHTML = `
            <small class="text-truncate me-2">${note.content}</small>
            <button class="btn btn-xs btn-outline-info py-0 px-1" style="font-size: 0.75rem;" onclick="seekToTimestamp(${note.timestamp})">
                ${timestampStr}
            </button>
        `;
        list.appendChild(div);
    });
}

function seekToTimestamp(seconds) {
    if (activePlayer && activePlayer.player) {
        activePlayer.player.currentTime = seconds;
        activePlayer.player.play();
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}


// --- Core Tracking Player Engine ---
class DircastPlayer {
  constructor(mediaElementId) {
    this.player = document.getElementById(mediaElementId);
    this.currentFilePath = null;
    this.viewRecorded = false;
    this.isSaving = false; // Prevents overlapping request spam
    this.setupListeners();
  }

  setupListeners() {
    this.player.addEventListener('pause', () => this.saveProgress());

    window.addEventListener('beforeunload', () => this.sendBeaconProgress());

    this.player.addEventListener('timeupdate', () => {
      if (!this.viewRecorded && this.player.currentTime > 10 && this.currentFilePath) {
        this.recordView();
      }
    });
  }

  async loadMedia(filePath, streamUrl) {
    if (this.currentFilePath) {
      await this.saveProgress();
    }

    this.currentFilePath = filePath;
    this.viewRecorded = false;
    this.player.src = streamUrl;

    // Fetch progress, views, and notes state
    const res = await fetch(`/api/media/state?file_path=${encodeURIComponent(filePath)}`);
    if (res.ok) {
        const state = await res.json();

        // Update View Count UI
        const viewEl = document.getElementById('view-count');
        if (viewEl) viewEl.innerText = state.views || 0;

        // Render Notes list
        renderNotes(state.notes || []);

        // Restore position on load
        this.player.addEventListener('loadedmetadata', () => {
          if (state.resume_position > 0 && state.resume_position < this.player.duration - 5) {
            this.player.currentTime = state.resume_position;
          }
          this.player.play();
        }, { once: true });
    } else {
        this.player.play();
    }
  }

  async saveProgress(overridePos = null) {
    if (!this.currentFilePath || this.isSaving) return;
    this.isSaving = true;

    const pos = overridePos !== null ? overridePos : this.player.currentTime;

    try {
      await fetch('/api/media/save-position', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: this.currentFilePath, position: pos })
      });
    } finally {
      this.isSaving = false;
    }
  }

  sendBeaconProgress() {
    if (!this.currentFilePath) return;
    const blob = new Blob([JSON.stringify({ 
      file_path: this.currentFilePath, 
      position: this.player.currentTime 
    })], { type: 'application/json' });
    
    navigator.sendBeacon('/api/media/save-position', blob);
  }

  async recordView() {
    this.viewRecorded = true;
    const res = await fetch('/api/media/view', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: this.currentFilePath })
    });
    if (res.ok) {
        const viewEl = document.getElementById('view-count');
        if (viewEl) {
            const currentViews = parseInt(viewEl.innerText) || 0;
            viewEl.innerText = currentViews + 1;
        }
    }
  }

  async addNote(content) {
    if (!this.currentFilePath) return;
    const timestamp = this.player.currentTime;
    
    const res = await fetch('/api/media/notes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        file_path: this.currentFilePath,
        timestamp: timestamp,
        content: content
      })
    });

    if (res.ok) {
        // Re-fetch notes to refresh UI list
        const stateRes = await fetch(`/api/media/state?file_path=${encodeURIComponent(this.currentFilePath)}`);
        const state = await stateRes.json();
        renderNotes(state.notes || []);
    }
  }
}