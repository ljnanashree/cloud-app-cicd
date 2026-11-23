/**
 * CloudPulse - Frontend Controller
 * Handles async REST interactions, live filtering, modals, toasts, and telemetry.
 */

document.addEventListener('DOMContentLoaded', () => {
    // State
    let currentTasks = [];
    let editModeTaskId = null;

    // DOM Elements
    const tasksList = document.getElementById('tasks-list');
    const searchInput = document.getElementById('task-search-input');
    const statusFilter = document.getElementById('status-filter');
    const priorityFilter = document.getElementById('priority-filter');
    const refreshBtn = document.getElementById('refresh-tasks-btn');

    // Modal Elements
    const taskModal = document.getElementById('task-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalCancelBtn = document.getElementById('modal-cancel-btn');
    const openCreateBtn = document.getElementById('open-create-modal-btn');
    const taskForm = document.getElementById('task-form');
    const taskIdInput = document.getElementById('task-id');
    const taskTitleInput = document.getElementById('task-title');
    const taskDescInput = document.getElementById('task-desc');
    const taskStatusInput = document.getElementById('task-status');
    const taskPriorityInput = document.getElementById('task-priority');
    const taskCategoryInput = document.getElementById('task-category');
    const taskDueInput = document.getElementById('task-due');

    // Theme Elements
    const themeToggle = document.getElementById('theme-toggle');

    // Initialize
    initTheme();
    loadTasks();
    pollHealthAndStats();

    // Event Listeners
    if (openCreateBtn) openCreateBtn.addEventListener('click', () => openModal());
    if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeModal);
    if (modalCancelBtn) modalCancelBtn.addEventListener('click', closeModal);
    if (taskModal) {
        taskModal.addEventListener('click', (e) => {
            if (e.target === taskModal) closeModal();
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && taskModal.classList.contains('active')) {
            closeModal();
        }
    });

    if (taskForm) taskForm.addEventListener('submit', handleTaskFormSubmit);

    // Filter & Search with Debounce
    let searchTimeout = null;
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(loadTasks, 250);
        });
    }

    if (statusFilter) statusFilter.addEventListener('change', loadTasks);
    if (priorityFilter) priorityFilter.addEventListener('change', loadTasks);
    if (refreshBtn) refreshBtn.addEventListener('click', () => {
        loadTasks();
        pollHealthAndStats();
        showToast('Refreshed tasks and diagnostics', 'info');
    });

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('cloudpulse-theme', newTheme);
        });
    }

    // ================= Functions ================= //

    function initTheme() {
        const savedTheme = localStorage.getItem('cloudpulse-theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
    }

    async function loadTasks() {
        try {
            const params = new URLSearchParams();
            if (statusFilter && statusFilter.value) params.append('status', statusFilter.value);
            if (priorityFilter && priorityFilter.value) params.append('priority', priorityFilter.value);
            if (searchInput && searchInput.value.trim()) params.append('search', searchInput.value.trim());

            const response = await fetch(`/api/tasks?${params.toString()}`);
            const data = await response.json();

            if (data.success) {
                currentTasks = data.tasks;
                renderTasks(currentTasks);
            } else {
                showToast(data.error || 'Failed to load tasks', 'error');
            }
        } catch (err) {
            console.error('Error fetching tasks:', err);
            tasksList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">⚠️</div>
                    <h4 class="empty-state-title">Unable to Connect</h4>
                    <p class="empty-state-desc">Could not retrieve tasks from server. Check your network or server status.</p>
                </div>
            `;
        }
    }

    function renderTasks(tasks) {
        if (!tasksList) return;

        if (!tasks || tasks.length === 0) {
            tasksList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📂</div>
                    <h4 class="empty-state-title">No Tasks Found</h4>
                    <p class="empty-state-desc">No tasks match your current query or filter criteria.</p>
                    <button class="btn btn-outline btn-sm" style="margin-top: 1rem;" onclick="document.getElementById('task-search-input').value=''; document.getElementById('status-filter').value=''; document.getElementById('priority-filter').value=''; document.getElementById('refresh-tasks-btn').click();">Reset Filters</button>
                </div>
            `;
            return;
        }

        tasksList.innerHTML = tasks.map(task => `
            <div class="task-card" data-task-id="${task.id}">
                <div class="task-card-header">
                    <div>
                        <h3 class="task-title">${escapeHtml(task.title)}</h3>
                        ${task.description ? `<p class="task-desc">${escapeHtml(task.description)}</p>` : ''}
                    </div>
                    <div class="task-actions">
                        <button class="btn btn-sm btn-outline edit-task-btn" data-id="${task.id}" title="Edit Task">✎ Edit</button>
                        <button class="btn btn-sm btn-danger-outline delete-task-btn" data-id="${task.id}" title="Delete Task">🗑</button>
                    </div>
                </div>

                <div class="task-meta-row">
                    <div class="task-badges">
                        <span class="badge ${getStatusBadgeClass(task.status)}">${escapeHtml(task.status)}</span>
                        <span class="badge ${getPriorityBadgeClass(task.priority)}">${escapeHtml(task.priority)} Priority</span>
                        ${task.category ? `<span class="badge badge-category">📁 ${escapeHtml(task.category)}</span>` : ''}
                        ${task.due_date ? `<span class="badge badge-outline">📅 Due: ${escapeHtml(task.due_date)}</span>` : ''}
                    </div>

                    <div class="quick-status-group">
                        <select class="form-select quick-status-select" data-id="${task.id}" style="padding: 0.2rem 0.5rem; font-size: 0.75rem;">
                            <option value="Backlog" ${task.status === 'Backlog' ? 'selected' : ''}>Backlog</option>
                            <option value="In Progress" ${task.status === 'In Progress' ? 'selected' : ''}>In Progress</option>
                            <option value="Review" ${task.status === 'Review' ? 'selected' : ''}>Review</option>
                            <option value="Completed" ${task.status === 'Completed' ? 'selected' : ''}>Completed</option>
                        </select>
                    </div>
                </div>
            </div>
        `).join('');

        // Attach Card Action Handlers
        document.querySelectorAll('.edit-task-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = parseInt(btn.getAttribute('data-id'), 10);
                const task = currentTasks.find(t => t.id === id);
                if (task) openModal(task);
            });
        });

        document.querySelectorAll('.delete-task-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = parseInt(btn.getAttribute('data-id'), 10);
                confirmAndDeleteTask(id);
            });
        });

        document.querySelectorAll('.quick-status-select').forEach(select => {
            select.addEventListener('change', async (e) => {
                const id = parseInt(e.target.getAttribute('data-id'), 10);
                const newStatus = e.target.value;
                await updateTaskStatus(id, newStatus);
            });
        });
    }

    async function handleTaskFormSubmit(e) {
        e.preventDefault();

        const title = taskTitleInput.value.trim();
        if (!title) {
            showToast('Task title is required', 'error');
            return;
        }

        const payload = {
            title: title,
            description: taskDescInput.value.trim(),
            status: taskStatusInput.value,
            priority: taskPriorityInput.value,
            category: taskCategoryInput.value.trim() || 'General',
            due_date: taskDueInput.value || null
        };

        try {
            let url = '/api/tasks';
            let method = 'POST';

            if (editModeTaskId) {
                url = `/api/tasks/${editModeTaskId}`;
                method = 'PUT';
            }

            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await res.json();

            if (res.ok && result.success) {
                showToast(editModeTaskId ? 'Task updated successfully' : 'Task created successfully', 'success');
                closeModal();
                loadTasks();
                pollHealthAndStats();
            } else {
                const errMsg = result.errors ? result.errors.join(', ') : (result.error || 'Failed to save task');
                showToast(errMsg, 'error');
            }
        } catch (err) {
            console.error('Error saving task:', err);
            showToast('Server connection failed', 'error');
        }
    }

    async function updateTaskStatus(taskId, status) {
        try {
            const res = await fetch(`/api/tasks/${taskId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: status })
            });
            const result = await res.json();
            if (res.ok && result.success) {
                showToast(`Task status changed to ${status}`, 'success');
                loadTasks();
                pollHealthAndStats();
            } else {
                showToast(result.error || 'Failed to update status', 'error');
            }
        } catch (err) {
            showToast('Failed to update status', 'error');
        }
    }

    async function confirmAndDeleteTask(taskId) {
        if (!confirm(`Are you sure you want to delete task #${taskId}?`)) {
            return;
        }

        try {
            const res = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
            const result = await res.json();

            if (res.ok && result.success) {
                showToast('Task deleted successfully', 'success');
                loadTasks();
                pollHealthAndStats();
            } else {
                showToast(result.error || 'Failed to delete task', 'error');
            }
        } catch (err) {
            showToast('Failed to delete task', 'error');
        }
    }

    function openModal(task = null) {
        if (task) {
            editModeTaskId = task.id;
            modalTitle.textContent = `Edit Task #${task.id}`;
            taskIdInput.value = task.id;
            taskTitleInput.value = task.title;
            taskDescInput.value = task.description || '';
            taskStatusInput.value = task.status;
            taskPriorityInput.value = task.priority;
            taskCategoryInput.value = task.category || 'General';
            taskDueInput.value = task.due_date || '';
        } else {
            editModeTaskId = null;
            modalTitle.textContent = 'Create New Task';
            taskForm.reset();
            taskIdInput.value = '';
            taskStatusInput.value = 'Backlog';
            taskPriorityInput.value = 'Medium';
            taskCategoryInput.value = 'General';
        }
        taskModal.classList.add('active');
        taskTitleInput.focus();
    }

    function closeModal() {
        taskModal.classList.remove('active');
        editModeTaskId = null;
    }

    async function pollHealthAndStats() {
        try {
            // Health check endpoint
            const healthRes = await fetch('/health');
            const healthData = await healthRes.json();

            if (healthData && healthData.database) {
                const navHealthDot = document.querySelector('.status-dot');
                const navHealthText = document.getElementById('nav-health-text');
                const navDbLatency = document.getElementById('nav-db-latency');
                const statDbLatency = document.getElementById('stat-db-latency');
                const diagDbPing = document.getElementById('diag-db-ping');

                if (navHealthDot && navHealthText) {
                    if (healthData.status === 'healthy') {
                        navHealthDot.className = 'status-dot healthy';
                        navHealthText.textContent = 'Cloud Healthy';
                    } else {
                        navHealthDot.className = 'status-dot degraded';
                        navHealthText.textContent = 'Degraded';
                    }
                }

                const latencyText = `${healthData.database.latency_ms}ms`;
                if (navDbLatency) navDbLatency.textContent = latencyText;
                if (statDbLatency) statDbLatency.textContent = latencyText;
                if (diagDbPing) diagDbPing.textContent = latencyText;
            }

            // Stats API endpoint
            const statsRes = await fetch('/api/stats');
            const statsData = await statsRes.json();

            if (statsData && statsData.success) {
                const s = statsData.stats;
                const statTotal = document.getElementById('stat-total-tasks');
                const statInProgress = document.getElementById('stat-in-progress');
                const statCompleted = document.getElementById('stat-completed');
                const statProgress = document.getElementById('stat-progress-bar');
                const statRate = document.getElementById('stat-completion-rate');

                if (statTotal) statTotal.textContent = s.total_tasks;
                if (statInProgress) statInProgress.textContent = s.status_breakdown['In Progress'] || 0;
                if (statCompleted) statCompleted.textContent = s.status_breakdown['Completed'] || 0;
                if (statProgress) statProgress.style.width = `${s.completion_rate}%`;
                if (statRate) statRate.textContent = `${s.completion_rate}% done`;
            }

            // Activity API endpoint
            const actRes = await fetch('/api/activity?limit=6');
            const actData = await actRes.json();
            if (actData && actData.success && actData.activity) {
                const timeline = document.getElementById('activity-timeline');
                if (timeline && actData.activity.length > 0) {
                    timeline.innerHTML = actData.activity.map(a => `
                        <div class="timeline-item">
                            <div class="timeline-marker"></div>
                            <div class="timeline-content">
                                <p class="timeline-text">${escapeHtml(a.details)}</p>
                                <span class="timeline-time">${escapeHtml(a.created_at)}</span>
                            </div>
                        </div>
                    `).join('');
                }
            }
        } catch (err) {
            console.warn('Diagnostics polling encountered an error:', err);
        }
    }

    function showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        const icons = { success: '✅', error: '❌', info: 'ℹ️' };
        toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${escapeHtml(message)}</span>`;

        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    function getStatusBadgeClass(status) {
        switch (status) {
            case 'Backlog': return 'badge-status-backlog';
            case 'In Progress': return 'badge-status-in-progress';
            case 'Review': return 'badge-status-review';
            case 'Completed': return 'badge-status-completed';
            default: return 'badge-outline';
        }
    }

    function getPriorityBadgeClass(priority) {
        switch (priority) {
            case 'Low': return 'badge-priority-low';
            case 'Medium': return 'badge-priority-medium';
            case 'High': return 'badge-priority-high';
            case 'Urgent': return 'badge-priority-urgent';
            default: return 'badge-outline';
        }
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
});
