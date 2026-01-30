document.addEventListener('DOMContentLoaded', () => {
    const commitList = document.getElementById('commit-list');
    const detailView = document.getElementById('detail-view');
    const repoStats = document.getElementById('repo-stats');

    let historyData = [];
    let selectedIndex = 0; // Default to first (latest)

    fetch('data.json')
        .then(response => response.json())
        .then(data => {
            historyData = data;
            renderSidebar();
            if (historyData.length > 0) {
                renderDetail(0);
                repoStats.textContent = `${historyData.length} snapshots found`;
            } else {
                repoStats.textContent = 'No history';
            }
        })
        .catch(error => {
            console.error('Error loading data:', error);
            commitList.innerHTML = '<div class="loading">Error loading history data.</div>';
        });

    function renderSidebar() {
        commitList.innerHTML = '';

        if (!historyData || historyData.length === 0) {
            commitList.innerHTML = '<div class="loading">No history found.</div>';
            return;
        }

        historyData.forEach((item, index) => {
            const el = document.createElement('div');
            el.className = `sidebar-item ${index === selectedIndex ? 'selected' : ''}`;
            el.onclick = () => selectCommit(index);

            const date = new Date(item.date).toLocaleDateString('en-US', {
                year: 'numeric', month: 'short', day: 'numeric'
            });

            // Calculate simple net change for badge
            // Note: Use stored counts if available, else calc
            const added = item.stats.added_count;
            const removed = item.stats.removed_count;
            let diffHtml = '';
            if (added > 0) diffHtml += `<span class="diff-badge pos">+${added}</span> `;
            if (removed > 0) diffHtml += `<span class="diff-badge neg">-${removed}</span>`;
            if (added === 0 && removed === 0) diffHtml = '<span class="diff-badge">No changes</span>';

            el.innerHTML = `
                <span class="date">${date}</span>
                <span class="message">${item.message}</span>
                <div class="meta-row">
                    <span class="author">${item.author}</span>
                    <span class="badg">${diffHtml}</span>
                </div>
            `;
            commitList.appendChild(el);
        });
    }

    function selectCommit(index) {
        selectedIndex = index;
        // Update sidebar visual state
        const items = commitList.getElementsByClassName('sidebar-item');
        for (let i = 0; i < items.length; i++) {
            if (i === index) items[i].classList.add('selected');
            else items[i].classList.remove('selected');
        }
        renderDetail(index);
    }

    function renderDetail(index) {
        const item = historyData[index];
        if (!item) return;

        const date = new Date(item.date).toLocaleString('en-US', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });

        // Generate HTML for added/removed
        const summaryHtml = renderServiceSummary(item.diff);
        const changesHtml = renderChanges(item.diff);

        detailView.innerHTML = `
            <div class="detail-header">
                <div class="detail-title">${item.message}</div>
                <div class="detail-meta">
                    Committed by <strong>${item.author}</strong> on ${date} <br>
                    Commit Hash: <span style="font-family:monospace">${item.hash.substring(0, 8)}</span>
                </div>
            </div>

            <div class="stats-bar">
                <div class="stat">
                    <span class="stat-label">Total Perms</span>
                    <span class="stat-value">${item.stats.total_permissions}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Services</span>
                    <span class="stat-value">${item.stats.service_count}</span>
                </div>
                 <div class="stat">
                    <span class="stat-label">Added</span>
                    <span class="stat-value text-green">+${item.stats.added_count}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Removed</span>
                    <span class="stat-value text-red">-${item.stats.removed_count}</span>
                </div>
            </div>

            ${summaryHtml}

            <div class="changes-container">
                ${changesHtml}
            </div>
        `;

        // Scroll detail view to top on switch
        detailView.scrollTop = 0;
    }

    function renderServiceSummary(diff) {
        let stats = {};

        // Aggregate stats
        if (diff.added) {
            for (const [service, perms] of Object.entries(diff.added)) {
                if (!stats[service]) stats[service] = { added: 0, removed: 0 };
                stats[service].added += perms.length;
            }
        }
        if (diff.removed) {
            for (const [service, perms] of Object.entries(diff.removed)) {
                if (!stats[service]) stats[service] = { added: 0, removed: 0 };
                stats[service].removed += perms.length;
            }
        }

        if (Object.keys(stats).length === 0) return '';

        let html = '<div class="summary-box"><h3>Service Impact Summary</h3><div class="summary-grid">';

        // Sort by total activity (added + removed)
        const sortedServices = Object.keys(stats).sort((a, b) => {
            const totalA = stats[a].added + stats[a].removed;
            const totalB = stats[b].added + stats[b].removed;
            return totalB - totalA;
        });

        for (const service of sortedServices) {
            const s = stats[service];
            let parts = [];
            if (s.added > 0) parts.push(`<span class="text-green">+${s.added} new</span>`);
            if (s.removed > 0) parts.push(`<span class="text-red">-${s.removed} removed</span>`);

            html += `
                <div class="summary-item">
                    <div class="service-label">${service}</div>
                    <div class="service-stats">${parts.join(', ')}</div>
                </div>
            `;
        }
        html += '</div></div>';
        return html;
    }

    function renderChanges(diff) {
        let html = '';

        if (diff.added && Object.keys(diff.added).length > 0) {
            html += `<h4 class="change-header text-green">Added Permissions</h4>`;
            for (const [service, perms] of Object.entries(diff.added)) {
                html += `
                    <div class="service-group">
                        <div class="service-name text-green">${service} <span class="count">(${perms.length})</span></div>
                        <ul class="permission-list">
                            ${perms.map(p => `
                                <li class="diff-row-add">
                                    <span class="marker">+</span>${p}
                                </li>`).join('')}
                        </ul>
                    </div>
                `;
            }
        }

        if (diff.removed && Object.keys(diff.removed).length > 0) {
            html += `<h4 class="change-header text-red">Removed Permissions</h4>`;
            for (const [service, perms] of Object.entries(diff.removed)) {
                html += `
                    <div class="service-group">
                        <div class="service-name text-red">${service} <span class="count">(${perms.length})</span></div>
                        <ul class="permission-list">
                            ${perms.map(p => `
                                <li class="diff-row-del">
                                    <span class="marker">-</span>${p}
                                </li>`).join('')}
                        </ul>
                    </div>
                `;
            }
        }

        if (!html) {
            html = '<div class="no-changes" style="text-align:center; color:#8b949e; margin-top:50px;">No permission changes detected in this snapshot.</div>';
        }

        return html;
    }
});
