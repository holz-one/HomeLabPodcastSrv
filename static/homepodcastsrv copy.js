let currentQueue = [];
let currentIndex = -1;

async function loadFeed(path, type="avfiles") {
    const res = await fetch(`/api/feed/${encodeURIComponent(path)}`);
    const data = await res.json();
    currentQueue = data.items;

    // 1. Declare variables OUTSIDE the if blocks so they are accessible later
    // let infoId;
    const infoId = type + "_info"    
    // let playlistId;
    const playlistId = type + "_playlist"
    // let tabTarget;
    const tabTarget = type + "cast-tab";    
    
    // 2. Use the variables
    const infoElement = document.getElementById(infoId);
    if (infoElement) {
        infoElement.innerHTML = `<h4>${data.title}</h4><p>${data.description}</p>`;
    }

    const rssLink = document.getElementById(type + '_rss-link');
    if (rssLink && data.link) {
            rssLink.href = data.link.replace('http', 'podcast');
    }

    // 3. Clear and build the Playlist
    const list = document.getElementById(playlistId);
    if (list) {
        list.innerHTML = '';
        data.items.forEach((item, index) => {
            const li = document.createElement('li');
            li.className = "list-group-item list-group-item-action"; // Bootstrap 5 styling
            li.innerText = item.title;
            li.onclick = () => playItem(index, type);
            list.appendChild(li);
        });
    }

    // 4. AUTOMATIC TAB SWITCH
    // Correct: Use the tab trigger button/link
    var tabTrigger = document.getElementById(tabTarget); // This should be the button/a, not the div
    var tab = new bootstrap.Tab(tabTrigger);
    tab.show();   
}


function playItem(index, type='avfiles') {
    if (index >= currentQueue.length) return;
    currentIndex = index;
    const item = currentQueue[index];
    const id = type + "_item_extra";
    // Example JavaScript rendering loop
    const editBtn = document.createElement('button');
    editBtn.className = 'btn-edit-episode';
    editBtn.innerText = '✏️ Edit Episode';
    editBtn.onclick = () => openEditModal({
       file_path: item.file_path || '',
       title: item.title || '',
       description: item.description || ''
    });

    document.getElementById(id).innerHTML = `
    <div class="container-fluid">
        <a class="navbar-brand" href="#"><img src="/static/logo.light.png" height="30"></a>

    </div>
    <hr />
    <p><strong>Title:</strong> ${item.title}</p>
    <p><strong>Published:</strong> ${item.pubDate}</p>
	<hr />
	<div>
		<strong>Description:</strong>
		<br />
	    <p>${item.description}</p>
        ${item.transcript}
	</div>

    `;

    // Append editBtn to your episode card/row container element
    document.getElementById(id).appendChild(editBtn);
    // Swap Player
    const overlay = document.getElementById('media-overlay');
    const content = document.getElementById('media-content');
    overlay.classList.remove('d-none');
    
    const isVideo = item.media_type && item.media_type.includes('video');
    content.innerHTML = isVideo 
        ? `<video id="main-player" controls src="${item.media_url}"></video>`
        : `<audio id="main-player" controls src="${item.media_url}"></audio>`;

    document.getElementById('now-playing-title').innerText = item.title;
    
    const player = document.getElementById('main-player');
    player.play();

    // "Play All" Logic: When this ends, play next
    player.onended = () => {
        if (currentIndex < currentQueue.length - 1) {
            playItem(currentIndex + 1);
        }
    };
}

function playAll() { if (currentQueue.length > 0) playItem(0); }

function toggleMinimize() { document.getElementById('media-overlay').classList.toggle('minimized'); }

function closePlayer() {
    const content = document.getElementById('media-content');
    content.innerHTML = '';
    document.getElementById('media-overlay').classList.add('d-none');
}


class DircastPlayer {
  constructor(mediaElementId) {
    this.player = document.getElementById(mediaElementId);
    this.currentFilePath = null;
    this.viewRecorded = false;
    this.setupListeners();
  }

  setupListeners() {
    // Save state on pause & ended
    this.player.addEventListener('pause', () => this.saveProgress());
    this.player.addEventListener('ended', () => this.saveProgress(0));

    // Send position beacon on tab close / reload
    window.addEventListener('beforeunload', () => this.sendBeaconProgress());

    // Record a view after 10 continuous seconds
    this.player.addEventListener('timeupdate', () => {
      if (!this.viewRecorded && this.player.currentTime > 10 && this.currentFilePath) {
        this.recordView();
      }
    });
  }

  async loadMedia(filePath, streamUrl) {
    // Save outgoing item position
    if (this.currentFilePath) {
      await this.saveProgress();
    }

    this.currentFilePath = filePath;
    this.viewRecorded = false;
    this.player.src = streamUrl;

    // Fetch resume state
    const res = await fetch(`/api/media/state?file_path=${encodeURIComponent(filePath)}`);
    const state = await res.json();

    // Restore timestamp once metadata loads
    this.player.addEventListener('loadedmetadata', () => {
      if (state.resume_position > 0 && state.resume_position < this.player.duration - 5) {
        this.player.currentTime = state.resume_position;
      }
      this.player.play();
    }, { once: true });
  }

  saveProgress(overridePos = null) {
    if (!this.currentFilePath) return;
    const pos = overridePos !== null ? overridePos : this.player.currentTime;

    return fetch('/api/media/save-position', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: this.currentFilePath, position: pos })
    });
  }

  sendBeaconProgress() {
    if (!this.currentFilePath) return;
    const blob = new Blob([JSON.stringify({ 
      file_path: this.currentFilePath, 
      position: this.player.currentTime 
    })], { type: 'application/json' });
    
    navigator.sendBeacon('/api/media/save-position', blob);
  }

  recordView() {
    this.viewRecorded = true;
    fetch('/api/media/view', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: this.currentFilePath })
    });
  }

  async addNote(content) {
    if (!this.currentFilePath) return;
    return fetch('/api/media/notes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        file_path: this.currentFilePath,
        timestamp: this.player.currentTime,
        content: content
      })
    });
  }
}

// Initialize instance
const dircastPlayer = new DircastPlayer('media-content');
