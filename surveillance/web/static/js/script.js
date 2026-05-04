async function fetchData() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        updateUI(data);
    } catch (error) {
        console.error('Error fetching status:', error);
        document.getElementById('system-status').innerText = 'System Offline';
        const dot = document.querySelector('.status-dot');
        if (dot) {
            dot.style.background = 'var(--danger-color)';
            dot.style.boxShadow = '0 0 10px var(--danger-color)';
        }
    }
}

function updateUI(data) {
    // Update Screens
    if (data.screenmanagers && data.screenmanagers.length > 0) {
        const sm = data.screenmanagers[0]; // Focus on first monitor for now
        
        const screenNameElem = document.getElementById('screen-name');
        const screenDurElem = document.getElementById('screen-duration');
        const pauseBtn = document.getElementById('pause-btn');

        if (screenNameElem) screenNameElem.innerText = sm.active_screen.name || 'None';
        if (screenDurElem) {
            screenDurElem.innerText = sm.active_screen.duration ? 
                `Duration: ${sm.active_screen.run_time}s / ${sm.active_screen.duration}s` : 'Manual Mode';
        }
        if (pauseBtn) pauseBtn.innerText = sm.disable_autorotation ? 'Resume' : 'Pause';
        
        // Update Streams
        const streamList = document.getElementById('stream-list');
        if (streamList) {
            streamList.innerHTML = '';
            if (sm.active_screen.streams) {
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
            }
        }

        // Update Monitors
        const monitorList = document.getElementById('monitor-list');
        if (monitorList) {
            monitorList.innerHTML = data.monitors.map(m => `
                <div style="margin-bottom: 0.5rem">
                    <strong>Monitor ${m.monitor_number + 1}</strong>: ${m.resolution.width}x${m.resolution.height} (${m.monitor_id})
                </div>
            `).join('');
        }

        // Update System Info
        if (data.system) {
            setElemText('sys-os', data.system.os);
            setElemText('sys-hw', data.system.hardware);
            setElemText('sys-ip', data.system.ip_address);
            setElemText('sys-cpu', data.system.cpu_usage);
            setElemText('sys-mem', data.system.memory);
            setElemText('sys-uptime', formatUptime(data.system.uptime));

            // Update Manager Link
            const managerLink = document.getElementById('manager-link');
            if (managerLink && data.system.ip_address) {
                managerLink.href = `http://${data.system.ip_address}:6453`;
            }
        }
    }
}

function setElemText(id, text) {
    const el = document.getElementById(id);
    if (el) el.innerText = text;
}

function formatUptime(seconds) {
    const d = Math.floor(seconds / (3600*24));
    const h = Math.floor(seconds % (3600*24) / 3600);
    const m = Math.floor(seconds % 3600 / 60);
    return `${d}d ${h}h ${m}m`;
}

async function nextScreen() {
    await fetch('/api/next', { method: 'POST' });
    fetchData();
}

async function toggleRotation() {
    await fetch('/api/toggle-rotation', { method: 'POST' });
    fetchData();
}

async function restartService() {
    if (confirm('Are you sure you want to restart the OpenSurv service?')) {
        await fetch('/api/restart-service', { method: 'POST' });
        alert('Restarting service...');
    }
}

async function stopService() {
    if (confirm('Are you sure you want to stop the OpenSurv service? This will shut down the display.')) {
        await fetch('/api/stop-service', { method: 'POST' });
        alert('Service is stopping. This connection will be lost.');
    }
}

async function rebootHost() {
    if (confirm('DANGER: This will reboot the entire machine. Proceed?')) {
        await fetch('/api/reboot-host', { method: 'POST' });
        alert('Host is rebooting. This connection will be lost.');
    }
}

// Update Management
async function checkForUpdates(manual = false) {
    try {
        const response = await fetch('/api/check-update');
        const data = await response.json();
        
        if (data.error) {
            document.getElementById('local-version-display').innerText = 'Error';
            if (manual) alert(`Update check failed: ${data.error}`);
            return;
        }

        document.getElementById('local-version-display').innerText = data.local || 'Unknown';
        const headerVer = document.getElementById('header-version');
        if (headerVer && data.local) headerVer.innerText = `v${data.local}`;

        if (data.update_available) {
            document.getElementById('remote-version-tag').textContent = `(v${data.remote})`;
            document.getElementById('update-notification').style.display = 'block';
            if (manual) alert(`A new update is available: v${data.remote}`);
        } else {
            if (manual) alert('Your system is already up to date!');
        }
    } catch (e) {
        console.error('Update check failed:', e);
        if (manual) alert('Failed to connect to the local update API.');
    }
}

function closeUpdateNotification() {
    document.getElementById('update-notification').style.display = 'none';
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    fetchData();
    checkForUpdates();
    setInterval(fetchData, 2000);
});
