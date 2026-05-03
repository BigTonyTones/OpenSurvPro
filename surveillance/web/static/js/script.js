async function fetchData() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        updateUI(data);
    } catch (error) {
        console.error('Error fetching status:', error);
        document.getElementById('system-status').innerText = 'System Offline';
        document.querySelector('.status-dot').style.background = '#f44336';
        document.querySelector('.status-dot').style.boxShadow = '0 0 10px #f44336';
    }
}

function updateUI(data) {
    // Update Screens
    if (data.screenmanagers && data.screenmanagers.length > 0) {
        const sm = data.screenmanagers[0]; // Focus on first monitor for now
        document.getElementById('screen-name').innerText = sm.active_screen.name;
        document.getElementById('screen-duration').innerText = `Duration: ${sm.active_screen.run_time}s / ${sm.active_screen.duration}s`;
        
        const pauseBtn = document.getElementById('pause-btn');
        pauseBtn.innerText = sm.disable_autorotation ? 'Resume' : 'Pause';
        
        // Update Streams
        const streamList = document.getElementById('stream-list');
        streamList.innerHTML = '';
        
        sm.active_screen.streams.forEach(stream => {
            const item = document.createElement('div');
            item.className = 'stream-item';
            item.innerHTML = `
                <span>${stream.name}</span>
                <span class="stream-status ${stream.online ? 'status-online' : 'status-offline'}">
                    ${stream.online ? 'ONLINE' : 'OFFLINE'}
                </span>
            `;
            streamList.appendChild(item);
        });

        // Update Monitors
        const monitorList = document.getElementById('monitor-list');
        monitorList.innerHTML = data.monitors.map(m => `
            <div style="margin-bottom: 0.5rem">
                <strong>Monitor ${m.monitor_number + 1}</strong>: ${m.resolution.width}x${m.resolution.height} (${m.monitor_id})
            </div>
        `).join('');
    }
}

async function nextScreen() {
    await fetch('/api/next', { method: 'POST' });
    fetchData();
}

async function toggleRotation() {
    await fetch('/api/toggle-rotation', { method: 'POST' });
    fetchData();
}

// Initial fetch and poll every 2 seconds
fetchData();
setInterval(fetchData, 2000);
