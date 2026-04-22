const formatTime = (ms) => {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
};

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

    } catch (error) {
        console.error('Error fetching status:', error);
    }
};

const updateQueue = async () => {
    try {
        const res = await fetch('/api/queue');
        const data = await res.json();
        const queueList = document.getElementById('queue-list');
        
        if (!data.queue || data.queue.length === 0) {
            queueList.innerHTML = '<div class="empty-state">Queue is empty</div>';
            return;
        }

        queueList.innerHTML = data.queue.map(track => `
            <li class="queue-item">
                <div class="queue-item-info">
                    <h4>${track.index + 1}. ${track.title}</h4>
                    <p>${track.author} • ${formatTime(track.length)}</p>
                </div>
                <button class="btn-remove" onclick="removeFromQueue(${track.index})" title="Remove">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </li>
        `).join('');

    } catch (error) {
        console.error('Error fetching queue:', error);
    }
};

const resetPlayer = () => {
    document.getElementById('track-title').innerText = 'Nothing playing right now';
    document.getElementById('track-author').innerText = 'Play some music to get started!';
    document.getElementById('track-artwork').src = 'https://via.placeholder.com/200?text=Music';
    document.getElementById('time-current').innerText = '0:00';
    document.getElementById('time-total').innerText = '0:00';
    document.getElementById('progress-fill').style.width = '0%';
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
