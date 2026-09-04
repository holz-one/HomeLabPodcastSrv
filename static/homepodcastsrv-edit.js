// Open the edit modal pre-filled with the current episode details
function openEditModal(episodeData) {
    document.getElementById('edit-file-path').value = episodeData.file_path || '';
    document.getElementById('edit-title').value = episodeData.title || '';
    document.getElementById('edit-description').value = episodeData.description || '';
    
    document.getElementById('editEpisodeModal').style.display = 'flex';
}

function closeEditModal() {
    document.getElementById('editEpisodeModal').style.display = 'none';
}

// Post updated metadata to Flask API
async function saveEpisodeData() {
    const payload = {
        file_path: document.getElementById('edit-file-path').value,
        title: document.getElementById('edit-title').value,
        description: document.getElementById('edit-description').value
    };

    try {
        const response = await fetch('/api/episode/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            alert('Episode saved!');
            closeEditModal();
            location.reload(); // Refresh page/feed to load updated content
        } else {
            alert('Error: ' + result.message);
        }
    } catch (err) {
        alert('Failed to save episode updates: ' + err);
    }
}

function openPlaylistEditModal(playlistName) {
    document.getElementById('edit-old-playlist-name').value = playlistName;
    document.getElementById('edit-new-playlist-name').value = playlistName;
    document.getElementById('editPlaylistModal').style.display = 'flex';
}

function closePlaylistEditModal() {
    document.getElementById('editPlaylistModal').style.display = 'none';
}

async function savePlaylistData() {
    const oldName = document.getElementById('edit-old-playlist-name').value;
    const newName = document.getElementById('edit-new-playlist-name').value.trim();

    if (!newName) {
        alert("Playlist name cannot be empty.");
        return;
    }

    try {
        const response = await fetch('/api/playlist/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_name: oldName, new_name: newName })
        });

        const result = await response.json();
        if (result.status === 'success') {
            alert('Playlist renamed!');
            closePlaylistEditModal();
            location.reload();
        } else {
            alert('Error: ' + result.message);
        }
    } catch (err) {
        alert('Failed to rename playlist: ' + err);
    }
}