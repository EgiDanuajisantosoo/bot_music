// ========================
//  Utility Functions
// ========================
const formatTime = (ms) => {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
};

// Toast notification
const showToast = (message, type = 'success') => {
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.className = `toast ${type}`;
    // Trigger reflow then show
    void toast.offsetWidth;
    toast.classList.add('show');
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => toast.classList.remove('show'), 2500);
};

// ========================
//  Lyrics Integration
// ========================
let currentLyricsTrack = null;
let parsedLyrics = [];

function parseLRC(lrcString) {
    const lines = lrcString.split('\n');
    const parsed = [];
    const timeRegex = /\[(\d{2}):(\d{2})\.(\d{2,3})\]/;
    
    for (const line of lines) {
        const match = timeRegex.exec(line);
        if (match) {
            const minutes = parseInt(match[1], 10);
            const seconds = parseInt(match[2], 10);
            const milliseconds = match[3].length === 2 ? parseInt(match[3], 10) * 10 : parseInt(match[3], 10);
            const timeInSeconds = minutes * 60 + seconds + milliseconds / 1000;
            const text = line.replace(timeRegex, '').trim();
            if (text) {
                parsed.push({ time: timeInSeconds, text });
            }
        }
    }
    return parsed;
}

async function fetchLyrics(title, author, durationMs) {
    if (currentLyricsTrack === `${title}-${author}`) return;
    
    currentLyricsTrack = `${title}-${author}`;
    parsedLyrics = [];
    
    const container = document.getElementById('lyrics-content');
    container.innerHTML = '<div class="empty-state">Loading lyrics... <i class="fa-solid fa-spinner fa-spin"></i></div>';
    
    try {
        const durationSec = Math.round(durationMs / 1000);
        
        // Bersihkan judul dari embel-embel YouTube seperti (Official Video), (Lyric), dsb.
        let cleanTitle = title.replace(/\s*[\(\[].*?(official|music|lyric|video|audio|visualizer).*?[\)\]]\s*/gi, '').trim();
        // Hapus nama artis dari judul jika ada format "Artis - Judul"
        const authorLower = author.toLowerCase();
        if (cleanTitle.toLowerCase().includes(authorLower + ' - ')) {
            const splitIdx = cleanTitle.toLowerCase().indexOf(authorLower + ' - ');
            cleanTitle = cleanTitle.substring(splitIdx + authorLower.length + 3).trim();
        }
        // Bersihkan nama artis (hapus bagian setelah tanda "-")
        let cleanAuthor = author;
        if (cleanAuthor.includes('-')) {
            cleanAuthor = cleanAuthor.split('-')[0].trim();
        }

        let data = null;

        // 1. Coba exact match dengan durasi
        let res = await fetch(`https://lrclib.net/api/get?track_name=${encodeURIComponent(cleanTitle)}&artist_name=${encodeURIComponent(cleanAuthor)}&duration=${durationSec}`);
        if (res.ok) data = await res.json();
        
        // 2. Coba exact match tanpa durasi
        if (!data) {
            res = await fetch(`https://lrclib.net/api/get?track_name=${encodeURIComponent(cleanTitle)}&artist_name=${encodeURIComponent(cleanAuthor)}`);
            if (res.ok) data = await res.json();
        }

        let isFallbackMatch = false;

        // 3. Jika masih gagal, gunakan fitur Search dari lrclib
        if (!data) {
            // Kita coba search dengan query gabungan judul dan artis
            res = await fetch(`https://lrclib.net/api/search?q=${encodeURIComponent(cleanTitle + ' ' + cleanAuthor)}`);
            if (res.ok) {
                const searchResults = await res.json();
                if (searchResults && searchResults.length > 0) {
                    // Pilih hasil pertama yang memiliki lirik (utamakan lirik sinkron)
                    data = searchResults.find(t => t.syncedLyrics) || searchResults.find(t => t.plainLyrics) || searchResults[0];
                }
            }
        }
        
        // 4. Opsi Terakhir: Cari HANYA dengan judul lagu, tapi filter berdasarkan durasi (toleransi 3 detik)
        if (!data) {
            res = await fetch(`https://lrclib.net/api/search?q=${encodeURIComponent(cleanTitle)}`);
            if (res.ok) {
                const searchResults = await res.json();
                if (searchResults && searchResults.length > 0) {
                    // Cari yang durasinya mirip (toleransi 3 detik)
                    const durationTolerance = 3;
                    const matchedByDuration = searchResults.filter(t => t.duration && Math.abs(t.duration - durationSec) <= durationTolerance);
                    
                    // Jika ada yang durasinya pas, gunakan itu. Jika tidak, gunakan hasil pencarian awal.
                    const listToSearch = matchedByDuration.length > 0 ? matchedByDuration : searchResults;

                    data = listToSearch.find(t => t.syncedLyrics) || listToSearch.find(t => t.plainLyrics) || listToSearch[0];
                    isFallbackMatch = true; // Tandai bahwa ini hasil tebakan yang mungkin kurang akurat
                }
            }
        }

        if (!data || (!data.syncedLyrics && !data.plainLyrics)) {
            throw new Error('Lyrics not found');
        }
        
        if (data.syncedLyrics) {
            parsedLyrics = parseLRC(data.syncedLyrics);
        } else if (data.plainLyrics) {
            parsedLyrics = [{ time: 0, text: data.plainLyrics.replace(/\n/g, '<br>') }];
        }
        
        // Render
        let html = '';
        if (isFallbackMatch) {
            html += `<div style="color: #fbbf24; font-size: 0.9rem; margin-bottom: 2rem; font-weight: 600; line-height: 1.4;"><i class="fa-solid fa-triangle-exclamation"></i> Peringatan: Lirik ini mungkin kurang akurat (karena pencarian hanya menggunakan tebakan judul).</div>`;
        }

        if (parsedLyrics.length === 1 && parsedLyrics[0].text.includes('<br>')) {
            html += `<div class="lyric-line active">${parsedLyrics[0].text}</div>`;
            parsedLyrics = []; // disable sync since it's plain
        } else if (parsedLyrics.length > 0) {
            html += parsedLyrics.map((line, idx) => 
                `<div class="lyric-line" id="lyric-${idx}">${line.text}</div>`
            ).join('');
        } else {
            throw new Error('Parsed lyrics empty');
        }
        
        container.innerHTML = html;
        
    } catch (err) {
        console.error(err);
        container.innerHTML = '<div class="empty-state">No lyrics found</div>';
    }
}

function updateLyricsScroll(positionMs) {
    if (parsedLyrics.length === 0) return;
    
    const positionSec = positionMs / 1000;
    let activeIdx = -1;
    
    for (let i = 0; i < parsedLyrics.length; i++) {
        if (positionSec >= parsedLyrics[i].time) {
            activeIdx = i;
        } else {
            break;
        }
    }
    
    if (activeIdx !== -1) {
        const lines = document.querySelectorAll('.lyric-line');
        lines.forEach(l => l.classList.remove('active'));
        
        const activeLine = document.getElementById(`lyric-${activeIdx}`);
        if (activeLine) {
            activeLine.classList.add('active');
            
            // Center the active line
            const container = document.getElementById('lyrics-content');
            const scrollPos = activeLine.offsetTop - (container.clientHeight / 2) + (activeLine.clientHeight / 2);
            container.scrollTo({ top: scrollPos, behavior: 'smooth' });
        }
    }
}

// ========================
//  Player Status
// ========================
const updateStatus = async () => {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        
        const statusDot = document.querySelector('.dot');
        const statusText = document.getElementById('status-text');
        
        if (data.status === 'disconnected') {
            statusDot.classList.remove('active');
            statusText.innerText = 'Disconnected from Voice';
            resetPlayer();
            return;
        }

        if (data.status === 'idle') {
            statusDot.classList.add('active');
            statusText.innerText = 'Connected - Idle';
            resetPlayer();
            return;
        }

        // Update player
        statusDot.classList.add('active');
        statusText.innerText = 'Playing';

        document.getElementById('track-title').innerText = data.track.title;
        document.getElementById('track-author').innerText = data.track.author;
        
        if (data.track.artwork) {
            document.getElementById('track-artwork').src = data.track.artwork;
        } else {
            document.getElementById('track-artwork').src = 'https://via.placeholder.com/200?text=No+Artwork';
        }

        document.getElementById('time-current').innerText = formatTime(data.track.position);
        document.getElementById('time-total').innerText = formatTime(data.track.length);
        
        const progressPercent = (data.track.position / data.track.length) * 100;
        document.getElementById('progress-fill').style.width = `${progressPercent}%`;

        fetchLyrics(data.track.title, data.track.author, data.track.length);
        updateLyricsScroll(data.track.position);

    } catch (error) {
        console.error('Error fetching status:', error);
    }
};

// ========================
//  Queue — Drag & Drop
// ========================

// State for drag & drop
let dragSrcIndex = null;
let dragGhostEl = null;

// Pause auto-refresh during drag to prevent DOM flicker
let isDragging = false;

const updateQueue = async () => {
    // Don't update queue DOM while user is dragging
    if (isDragging) return;

    try {
        const res = await fetch('/api/queue');
        const data = await res.json();
        const queueList = document.getElementById('queue-list');
        
        if (!data.queue || data.queue.length === 0) {
            queueList.innerHTML = '<div class="empty-state">Queue is empty</div>';
            return;
        }

        queueList.innerHTML = data.queue.map((track, idx) => `
            <li class="queue-item" draggable="true" data-index="${idx}">
                <div class="queue-item-left">
                    <div class="drag-handle" title="Drag to reorder">
                        <i class="fa-solid fa-grip-vertical"></i>
                    </div>
                    <div class="queue-index">${idx + 1}</div>
                    <div class="queue-item-info">
                        <h4>${track.title}</h4>
                        <p>${track.author} • ${formatTime(track.length)}</p>
                    </div>
                </div>
                <button class="btn-remove" onclick="removeFromQueue(${track.index})" title="Remove">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </li>
        `).join('');

        // Attach drag events to each item
        attachDragListeners();

    } catch (error) {
        console.error('Error fetching queue:', error);
    }
};

// Attach drag event listeners to all queue items
function attachDragListeners() {
    const queueList = document.getElementById('queue-list');
    const items = queueList.querySelectorAll('.queue-item');

    items.forEach(item => {
        item.addEventListener('dragstart', handleDragStart);
        item.addEventListener('dragend', handleDragEnd);
        item.addEventListener('dragover', handleDragOver);
        item.addEventListener('dragenter', handleDragEnter);
        item.addEventListener('dragleave', handleDragLeave);
        item.addEventListener('drop', handleDrop);
    });
}

function handleDragStart(e) {
    isDragging = true;
    dragSrcIndex = parseInt(this.dataset.index);
    this.classList.add('dragging');
    document.getElementById('queue-list').classList.add('drag-active');

    // Create a custom drag ghost
    dragGhostEl = document.createElement('div');
    dragGhostEl.className = 'drag-ghost';
    const title = this.querySelector('.queue-item-info h4')?.textContent || 'Track';
    dragGhostEl.textContent = `♪ ${title}`;
    document.body.appendChild(dragGhostEl);
    e.dataTransfer.setDragImage(dragGhostEl, 0, 0);

    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', dragSrcIndex.toString());
}

function handleDragEnd(e) {
    isDragging = false;
    this.classList.remove('dragging');
    document.getElementById('queue-list').classList.remove('drag-active');

    // Clean up all drag-over indicators
    document.querySelectorAll('.queue-item').forEach(item => {
        item.classList.remove('drag-over-top', 'drag-over-bottom');
    });

    // Remove ghost
    if (dragGhostEl) {
        dragGhostEl.remove();
        dragGhostEl = null;
    }

    dragSrcIndex = null;
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';

    const targetIndex = parseInt(this.dataset.index);
    if (targetIndex === dragSrcIndex) return;

    // Determine if we're above or below the midpoint
    const rect = this.getBoundingClientRect();
    const midY = rect.top + rect.height / 2;

    // Remove previous indicators on this element
    this.classList.remove('drag-over-top', 'drag-over-bottom');

    if (e.clientY < midY) {
        this.classList.add('drag-over-top');
    } else {
        this.classList.add('drag-over-bottom');
    }
}

function handleDragEnter(e) {
    e.preventDefault();
}

function handleDragLeave(e) {
    this.classList.remove('drag-over-top', 'drag-over-bottom');
}

async function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();

    const targetIndex = parseInt(this.dataset.index);
    
    // Clean up visuals
    this.classList.remove('drag-over-top', 'drag-over-bottom');

    if (dragSrcIndex === null || dragSrcIndex === targetIndex) return;

    // Determine drop position based on cursor position relative to element midpoint
    const rect = this.getBoundingClientRect();
    const midY = rect.top + rect.height / 2;
    let dropIndex = e.clientY < midY ? targetIndex : targetIndex;

    // If dragging from above to below, the drop index is the target.
    // If dragging from below to above, the drop index is the target.
    // The API moves `from` → `to`, so we send exactly what was computed.

    try {
        const res = await fetch('/api/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ from: dragSrcIndex, to: dropIndex })
        });

        const result = await res.json();
        if (result.success) {
            showToast('Antrean diperbarui ✓', 'success');
        } else {
            showToast(result.error || 'Gagal memindahkan', 'error');
        }
    } catch (err) {
        showToast('Koneksi error', 'error');
        console.error('Move error:', err);
    }

    // Force refresh queue
    isDragging = false;
    updateQueue();
}

// ========================
//  Touch Drag Support
// ========================
// For mobile: implement touch-based drag & drop
(function initTouchDrag() {
    let touchStartY = 0;
    let touchCurrentItem = null;
    let touchClone = null;
    let touchStartIndex = null;
    let touchScrollOffset = 0;

    document.addEventListener('touchstart', (e) => {
        const handle = e.target.closest('.drag-handle');
        if (!handle) return;

        const item = handle.closest('.queue-item');
        if (!item) return;

        e.preventDefault();
        isDragging = true;
        touchStartIndex = parseInt(item.dataset.index);
        touchCurrentItem = item;
        touchStartY = e.touches[0].clientY;
        touchScrollOffset = document.getElementById('queue-list').scrollTop;

        item.classList.add('dragging');
        document.getElementById('queue-list').classList.add('drag-active');

        // Create floating clone
        touchClone = document.createElement('div');
        touchClone.className = 'drag-ghost';
        const title = item.querySelector('.queue-item-info h4')?.textContent || 'Track';
        touchClone.textContent = `♪ ${title}`;
        touchClone.style.position = 'fixed';
        touchClone.style.top = `${e.touches[0].clientY - 16}px`;
        touchClone.style.left = `${e.touches[0].clientX + 10}px`;
        touchClone.style.pointerEvents = 'none';
        touchClone.style.zIndex = '10000';
        document.body.appendChild(touchClone);
    }, { passive: false });

    document.addEventListener('touchmove', (e) => {
        if (!touchCurrentItem) return;
        e.preventDefault();

        const touch = e.touches[0];

        // Move floating clone
        if (touchClone) {
            touchClone.style.top = `${touch.clientY - 16}px`;
            touchClone.style.left = `${touch.clientX + 10}px`;
        }

        // Find item under touch
        const items = document.querySelectorAll('.queue-item:not(.dragging)');
        items.forEach(item => item.classList.remove('drag-over-top', 'drag-over-bottom'));

        const elementUnder = document.elementFromPoint(touch.clientX, touch.clientY);
        const itemUnder = elementUnder?.closest('.queue-item');
        if (itemUnder && !itemUnder.classList.contains('dragging')) {
            const rect = itemUnder.getBoundingClientRect();
            const midY = rect.top + rect.height / 2;
            if (touch.clientY < midY) {
                itemUnder.classList.add('drag-over-top');
            } else {
                itemUnder.classList.add('drag-over-bottom');
            }
        }
    }, { passive: false });

    document.addEventListener('touchend', async (e) => {
        if (!touchCurrentItem) return;

        // Find drop target
        const items = document.querySelectorAll('.queue-item');
        let dropIndex = touchStartIndex;

        items.forEach(item => {
            if (item.classList.contains('drag-over-top') || item.classList.contains('drag-over-bottom')) {
                dropIndex = parseInt(item.dataset.index);
            }
            item.classList.remove('drag-over-top', 'drag-over-bottom');
        });

        touchCurrentItem.classList.remove('dragging');
        document.getElementById('queue-list').classList.remove('drag-active');

        if (touchClone) {
            touchClone.remove();
            touchClone = null;
        }

        if (touchStartIndex !== null && touchStartIndex !== dropIndex) {
            try {
                const res = await fetch('/api/move', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ from: touchStartIndex, to: dropIndex })
                });
                const result = await res.json();
                if (result.success) {
                    showToast('Antrean diperbarui ✓', 'success');
                } else {
                    showToast(result.error || 'Gagal memindahkan', 'error');
                }
            } catch (err) {
                showToast('Koneksi error', 'error');
            }
        }

        touchCurrentItem = null;
        touchStartIndex = null;
        isDragging = false;
        updateQueue();
    });
})();

// ========================
//  Player Controls
// ========================
const resetPlayer = () => {
    document.getElementById('track-title').innerText = 'Nothing playing right now';
    document.getElementById('track-author').innerText = 'Play some music to get started!';
    document.getElementById('track-artwork').src = 'https://via.placeholder.com/200?text=Music';
    document.getElementById('time-current').innerText = '0:00';
    document.getElementById('time-total').innerText = '0:00';
    document.getElementById('progress-fill').style.width = '0%';
    
    // Reset lyrics
    currentLyricsTrack = null;
    parsedLyrics = [];
    document.getElementById('lyrics-content').innerHTML = '<div class="empty-state">No lyrics available</div>';
};

// Actions
document.getElementById('btn-skip').addEventListener('click', async () => {
    await fetch('/api/skip', { method: 'POST' });
    updateStatus();
    updateQueue();
});

document.getElementById('btn-clear').addEventListener('click', async () => {
    if(confirm('Are you sure you want to clear the entire queue?')) {
        await fetch('/api/clear', { method: 'POST' });
        updateQueue();
    }
});

document.getElementById('btn-play').addEventListener('click', async () => {
    const input = document.getElementById('search-input');
    const query = input.value.trim();
    if (!query) return;

    const btn = document.getElementById('btn-play');
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    btn.disabled = true;

    try {
        await fetch('/api/play', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        input.value = '';
        updateStatus();
        updateQueue();
    } catch (error) {
        alert('Failed to add song');
    } finally {
        btn.innerHTML = '<i class="fa-solid fa-play"></i> Add';
        btn.disabled = false;
    }
});

// Play Next — insert song at front of queue
document.getElementById('btn-playnext').addEventListener('click', async () => {
    const input = document.getElementById('search-input');
    const query = input.value.trim();
    if (!query) return;

    const btn = document.getElementById('btn-playnext');
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    btn.disabled = true;

    try {
        const res = await fetch('/api/playnext', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const result = await res.json();
        if (result.success) {
            showToast(result.message || 'Ditambahkan ke urutan berikutnya ✓', 'success');
        } else {
            showToast(result.error || 'Gagal menambahkan', 'error');
        }
        input.value = '';
        updateStatus();
        updateQueue();
    } catch (error) {
        showToast('Failed to add song', 'error');
    } finally {
        btn.innerHTML = '<i class="fa-solid fa-forward"></i> Next';
        btn.disabled = false;
    }
});

document.getElementById('search-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        document.getElementById('btn-play').click();
    }
});

window.removeFromQueue = async (index) => {
    await fetch('/api/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ index })
    });
    updateQueue();
};

// Polling loops
setInterval(updateStatus, 1000);
setInterval(updateQueue, 2000);

// Initial fetch
updateStatus();
updateQueue();

// ========================
//  Playlists Integration
// ========================

// Navigation
const navDashboard = document.getElementById('nav-dashboard');
const navPlaylists = document.getElementById('nav-playlists');
const viewDashboard = document.getElementById('view-dashboard');
const viewPlaylists = document.getElementById('view-playlists');
const pageTitle = document.getElementById('page-title');

navDashboard.addEventListener('click', () => {
    navDashboard.classList.add('active');
    navPlaylists.classList.remove('active');
    viewDashboard.style.display = 'block';
    viewPlaylists.style.display = 'none';
    pageTitle.innerText = 'Now Playing';
});

navPlaylists.addEventListener('click', () => {
    navPlaylists.classList.add('active');
    navDashboard.classList.remove('active');
    viewDashboard.style.display = 'none';
    viewPlaylists.style.display = 'block';
    pageTitle.innerText = 'Playlists';
    loadPlaylists();
});

// Load all playlists
async function loadPlaylists() {
    document.getElementById('playlists-main').style.display = 'flex';
    document.getElementById('playlist-details').style.display = 'none';
    
    const grid = document.getElementById('playlists-grid');
    grid.innerHTML = '<div class="empty-state">Loading playlists... <i class="fa-solid fa-spinner fa-spin"></i></div>';
    
    try {
        const res = await fetch('/api/playlists');
        const data = await res.json();
        
        if (!data.playlists || data.playlists.length === 0) {
            grid.innerHTML = '<div class="empty-state">No playlists found. Create one!</div>';
            return;
        }
        
        grid.innerHTML = data.playlists.map(p => `
            <div class="playlist-card glass-panel" onclick="openPlaylist(${p.id}, '${p.name.replace(/'/g, "\\'")}')">
                <i class="fa-solid fa-list-music playlist-icon"></i>
                <h3>${p.name}</h3>
                <p>Created by: ${p.user_id === 'WebUser' ? 'Web' : p.user_id}</p>
            </div>
        `).join('');
    } catch (err) {
        grid.innerHTML = '<div class="empty-state">Failed to load playlists.</div>';
    }
}

// Create Playlist
document.getElementById('btn-create-playlist').addEventListener('click', async () => {
    const name = prompt('Enter new playlist name:');
    if (!name) return;
    
    try {
        const res = await fetch('/api/playlists/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        const result = await res.json();
        if (result.success) {
            showToast('Playlist created!', 'success');
            loadPlaylists();
        } else {
            showToast(result.error || 'Failed to create playlist', 'error');
        }
    } catch (err) {
        showToast('Connection error', 'error');
    }
});

// Playlist Details State
let currentPlaylistId = null;

// Open Playlist Details
async function openPlaylist(id, name) {
    currentPlaylistId = id;
    document.getElementById('playlists-main').style.display = 'none';
    document.getElementById('playlist-details').style.display = 'flex';
    document.getElementById('playlist-details-title').innerText = name;
    
    await loadPlaylistTracks(id);
}

// Back to Playlists List
document.getElementById('btn-back-playlists').addEventListener('click', () => {
    document.getElementById('playlists-main').style.display = 'flex';
    document.getElementById('playlist-details').style.display = 'none';
    currentPlaylistId = null;
    loadPlaylists();
});

// Load Playlist Tracks
async function loadPlaylistTracks(id) {
    const list = document.getElementById('playlist-tracks-list');
    list.innerHTML = '<div class="empty-state">Loading tracks... <i class="fa-solid fa-spinner fa-spin"></i></div>';
    
    try {
        const res = await fetch(`/api/playlists/${id}`);
        const data = await res.json();
        
        if (!data.tracks || data.tracks.length === 0) {
            list.innerHTML = '<div class="empty-state">Playlist is empty. Add some songs!</div>';
            return;
        }
        
        list.innerHTML = data.tracks.map((t, idx) => `
            <li class="queue-item">
                <div class="queue-item-left">
                    <div class="queue-index">${idx + 1}</div>
                    <div class="queue-item-info">
                        <h4>${t.title}</h4>
                        <p>${t.query}</p>
                    </div>
                </div>
                <button class="btn-remove" onclick="removePlaylistTrack(${t.id})" title="Remove">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </li>
        `).join('');
    } catch (err) {
        list.innerHTML = '<div class="empty-state">Failed to load tracks.</div>';
    }
}

// Add Track to Playlist
document.getElementById('btn-playlist-add').addEventListener('click', async () => {
    if (!currentPlaylistId) return;
    
    const input = document.getElementById('playlist-search-input');
    const query = input.value.trim();
    if (!query) return;
    
    const btn = document.getElementById('btn-playlist-add');
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    btn.disabled = true;
    
    try {
        const res = await fetch('/api/playlists/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ playlist_id: currentPlaylistId, query: query, title: query })
        });
        const result = await res.json();
        
        if (result.success) {
            showToast('Added to playlist!', 'success');
            input.value = '';
            loadPlaylistTracks(currentPlaylistId);
        } else {
            showToast(result.error || 'Failed to add', 'error');
        }
    } catch (err) {
        showToast('Connection error', 'error');
    } finally {
        btn.innerHTML = '<i class="fa-solid fa-plus"></i> Add to Playlist';
        btn.disabled = false;
    }
});

// Play Playlist
document.getElementById('btn-play-playlist').addEventListener('click', async () => {
    if (!currentPlaylistId) return;
    
    const btn = document.getElementById('btn-play-playlist');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    btn.disabled = true;
    
    try {
        const res = await fetch('/api/playlists/play', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ playlist_id: currentPlaylistId })
        });
        const result = await res.json();
        
        if (result.success) {
            showToast(result.message, 'success');
            // Switch to dashboard view
            navDashboard.click();
        } else {
            showToast(result.error || 'Failed to play playlist', 'error');
        }
    } catch (err) {
        showToast('Connection error', 'error');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
});

// Remove Track from Playlist
window.removePlaylistTrack = async (trackId) => {
    if (!confirm('Remove this track from the playlist?')) return;
    
    try {
        const res = await fetch('/api/playlists/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ track_id: trackId })
        });
        const result = await res.json();
        if (result.success) {
            showToast('Track removed', 'success');
            loadPlaylistTracks(currentPlaylistId);
        } else {
            showToast('Failed to remove track', 'error');
        }
    } catch (err) {
        showToast('Connection error', 'error');
    }
};

// Delete Playlist
document.getElementById('btn-delete-playlist').addEventListener('click', async () => {
    if (!currentPlaylistId) return;
    if (!confirm('Are you sure you want to delete this playlist entirely? This action cannot be undone.')) return;
    
    try {
        const res = await fetch('/api/playlists/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ playlist_id: currentPlaylistId })
        });
        const result = await res.json();
        if (result.success) {
            showToast('Playlist deleted', 'success');
            document.getElementById('btn-back-playlists').click();
        } else {
            showToast('Failed to delete playlist', 'error');
        }
    } catch (err) {
        showToast('Connection error', 'error');
    }
});

