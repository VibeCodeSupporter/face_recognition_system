/**
 * Face Access Control System - Web Portal
 * Main Application Script
 */

'use strict';

/* ================================================
   MOCK DATA
   ================================================ */
const MOCK_USERS = [
  { id: 'USR001', name: 'Nguyễn Văn An', email: 'an.nguyen@company.vn', dept: 'Kỹ thuật', role: 'Engineer', status: 'active', faceStatus: 'enrolled', created: '2026-01-10', lastAccess: '2026-09-29 14:32' },
  { id: 'USR002', name: 'Trần Thị Bình', email: 'binh.tran@company.vn', dept: 'Nhân sự', role: 'HR Manager', status: 'active', faceStatus: 'enrolled', created: '2026-02-15', lastAccess: '2026-09-29 08:05' },
  { id: 'USR003', name: 'Phạm Thành Đạt', email: 'dat.pham@company.vn', dept: 'IT', role: 'Admin', status: 'active', faceStatus: 'enrolled', created: '2026-01-05', lastAccess: '2026-09-29 15:10' },
  { id: 'USR004', name: 'Phạm Thị Dung', email: 'dung.pham@company.vn', dept: 'Tài chính', role: 'Accountant', status: 'inactive', faceStatus: 'pending', created: '2026-03-20', lastAccess: 'Chưa có' },
  { id: 'USR005', name: 'Hoàng Minh Em', email: 'em.hoang@company.vn', dept: 'Kinh doanh', role: 'Sales', status: 'active', faceStatus: 'enrolled', created: '2026-04-01', lastAccess: '2026-09-28 17:45' },
  { id: 'USR006', name: 'Ngô Thị Phương', email: 'phuong.ngo@company.vn', dept: 'Marketing', role: 'Designer', status: 'active', faceStatus: 'failed', created: '2026-05-12', lastAccess: '2026-09-29 09:20' },
  { id: 'USR007', name: 'Vũ Đình Quân', email: 'quan.vu@company.vn', dept: 'Kỹ thuật', role: 'Engineer', status: 'active', faceStatus: 'enrolled', created: '2026-06-18', lastAccess: '2026-09-29 13:55' },
  { id: 'USR008', name: 'Đinh Thị Hoa', email: 'hoa.dinh@company.vn', dept: 'Nhân sự', role: 'Recruiter', status: 'inactive', faceStatus: 'pending', created: '2026-07-02', lastAccess: 'Chưa có' },
];

const MOCK_ACCESS_LOGS = [
  { id: 'LOG001', userId: 'USR003', name: 'Phạm Thành Đạt', device: 'Cổng chính A', result: 'granted', time: '15:10:22', date: '29/09/2026', confidence: 98.5 },
  { id: 'LOG002', userId: null, name: 'Người lạ #042', device: 'Cổng phụ B', result: 'denied', time: '15:05:11', date: '29/09/2026', confidence: 12.3 },
  { id: 'LOG003', userId: 'USR001', name: 'Nguyễn Văn An', device: 'Cổng chính A', result: 'granted', time: '14:32:45', date: '29/09/2026', confidence: 96.2 },
  { id: 'LOG004', userId: 'USR007', name: 'Vũ Đình Quân', device: 'Cổng kho C', result: 'granted', time: '13:55:03', date: '29/09/2026', confidence: 97.8 },
  { id: 'LOG005', userId: null, name: 'Không xác định', device: 'Cổng chính A', result: 'denied', time: '13:42:18', date: '29/09/2026', confidence: 8.9 },
  { id: 'LOG006', userId: 'USR005', name: 'Hoàng Minh Em', device: 'Cổng chính A', result: 'granted', time: '12:10:55', date: '29/09/2026', confidence: 94.7 },
  { id: 'LOG007', userId: 'USR002', name: 'Trần Thị Bình', device: 'Cổng phụ B', result: 'granted', time: '08:05:33', date: '29/09/2026', confidence: 99.1 },
  { id: 'LOG008', userId: null, name: 'Người lạ #043', device: 'Cổng kho C', result: 'denied', time: '07:58:12', date: '29/09/2026', confidence: 5.4 },
];

const MOCK_DEVICES = [
  { id: 'DEV001', name: 'Cổng Chính A', location: 'Tầng 1 - Sảnh chính', ip: '192.168.1.101', firmware: 'v2.4.1', status: 'online', lastSync: '2 phút trước', uptime: '14 ngày 6h', totalToday: 47 },
  { id: 'DEV002', name: 'Cổng Phụ B', location: 'Tầng 1 - Cửa hông', ip: '192.168.1.102', firmware: 'v2.4.1', status: 'online', lastSync: '5 phút trước', uptime: '7 ngày 2h', totalToday: 18 },
  { id: 'DEV003', name: 'Cổng Kho C', location: 'Tầng B1 - Kho hàng', ip: '192.168.1.103', firmware: 'v2.3.8', status: 'warning', lastSync: '2 giờ trước', uptime: '3 ngày 11h', totalToday: 12 },
  { id: 'DEV004', name: 'Cổng Server Room', location: 'Tầng 3 - Phòng máy chủ', ip: '192.168.1.104', firmware: 'v2.4.1', status: 'online', lastSync: '1 phút trước', uptime: '21 ngày 9h', totalToday: 8 },
  { id: 'DEV005', name: 'Cổng Tầng 2', location: 'Tầng 2 - Cầu thang', ip: '192.168.1.105', firmware: 'v2.1.0', status: 'offline', lastSync: '3 ngày trước', uptime: '---', totalToday: 0 },
];

const MOCK_SESSIONS = [
  { id: 'SES001', userId: 'USR004', userName: 'Phạm Thị Dung', requestBy: 'Admin', status: 'pending', created: '2026-09-29 10:00', expires: '2026-09-30 10:00', device: 'DEV001' },
  { id: 'SES002', userId: 'USR008', userName: 'Đinh Thị Hoa', requestBy: 'HR Manager', status: 'pending', created: '2026-09-29 11:30', expires: '2026-09-30 11:30', device: 'DEV001' },
  { id: 'SES003', userId: 'USR006', userName: 'Ngô Thị Phương', requestBy: 'Admin', status: 'completed', created: '2026-09-28 14:00', expires: '2026-09-29 14:00', device: 'DEV002' },
];

/* ================================================
   APP STATE
   ================================================ */
const App = {
  isLoggedIn: false,
  currentPage: 'dashboard',
  currentUser: { name: 'Phạm Thành Đạt', role: 'Super Admin', initials: 'PD' },
  registrationStep: 1,
  capturedImages: 0,
  faceRegStep: 1,
};

/* ================================================
   DOM UTILITIES
   ================================================ */
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

/* ================================================
   NAVIGATION
   ================================================ */
function navigateTo(pageId) {
  $$('.page-content').forEach(p => p.classList.remove('active'));
  $$('.nav-item').forEach(n => n.classList.remove('active'));

  const page = $(`#page-${pageId}`);
  if (page) page.classList.add('active');

  const navItem = $(`.nav-item[data-page="${pageId}"]`);
  if (navItem) navItem.classList.add('active');

  App.currentPage = pageId;

  const titles = {
    dashboard: 'Dashboard <span>Overview</span>',
    users: 'Quản lý <span>Người dùng</span>',
    registration: 'Đăng ký <span>Khuôn mặt</span>',
    history: 'Lịch sử <span>Truy cập</span>',
    devices: 'Quản lý <span>Thiết bị</span>',
    config: 'Cấu hình <span>Hệ thống</span>',
  };
  const topbarTitle = $('#topbar-title');
  if (topbarTitle) topbarTitle.innerHTML = titles[pageId] || 'Portal';
}

/* ================================================
   LOGIN / LOGOUT
   ================================================ */
function handleLogin(e) {
  e.preventDefault();
  const email = $('#login-email').value.trim();
  const pass  = $('#login-pass').value.trim();

  if (!email || !pass) {
    showToast('error', 'Lỗi đăng nhập', 'Vui lòng nhập đầy đủ thông tin.');
    return;
  }
  // Simulate login
  const btn = $('#login-btn');
  btn.disabled = true;
  btn.innerHTML = '<span style="display:inline-flex;align-items:center;gap:8px"><span class="spinner"></span> Đang đăng nhập...</span>';

  setTimeout(() => {
    App.isLoggedIn = true;
    $('#login-page').classList.remove('active');
    $('#app-shell').style.display = 'flex';
    updateSidebarUser();
    navigateTo('dashboard');
    showToast('success', 'Đăng nhập thành công', `Xin chào, ${App.currentUser.name}!`);
    btn.disabled = false;
    btn.innerHTML = '<span>🔐</span> Đăng nhập';
    renderDashboard();
    renderUserTable();
    renderLogFeed();
    renderDevices();
    renderSessionTable();
    renderHistoryTable();
  }, 1200);
}

function handleLogout() {
  App.isLoggedIn = false;
  $('#app-shell').style.display = 'none';
  $('#login-page').classList.add('active');
  showToast('info', 'Đã đăng xuất', 'Hẹn gặp lại!');
}

function updateSidebarUser() {
  const avatar = $('#sidebar-user-avatar');
  const name   = $('#sidebar-user-name');
  const role   = $('#sidebar-user-role');
  if (avatar) avatar.textContent = App.currentUser.initials;
  if (name)   name.textContent   = App.currentUser.name;
  if (role)   role.textContent   = App.currentUser.role;
}

/* ================================================
   DASHBOARD
   ================================================ */
function renderDashboard() {
  // Animate stat values
  animateCounter('#stat-users',   MOCK_USERS.length);
  animateCounter('#stat-active',  MOCK_USERS.filter(u => u.status === 'active').length);
  animateCounter('#stat-access',  85);
  animateCounter('#stat-denied',  MOCK_ACCESS_LOGS.filter(l => l.result === 'denied').length);
  animateCounter('#stat-devices', MOCK_DEVICES.filter(d => d.status === 'online').length);

  renderBarChart();
  renderDonutChart();
  renderRecentLogs();
}

function animateCounter(sel, target) {
  const el = $(sel);
  if (!el) return;
  let start = 0;
  const step = target / 30;
  const timer = setInterval(() => {
    start = Math.min(start + step, target);
    el.textContent = Math.round(start).toLocaleString();
    if (start >= target) clearInterval(timer);
  }, 30);
}

function renderBarChart() {
  const data = [
    { label: 'T2', granted: 72, denied: 5 },
    { label: 'T3', granted: 85, denied: 8 },
    { label: 'T4', granted: 91, denied: 3 },
    { label: 'T5', granted: 68, denied: 12 },
    { label: 'T6', granted: 95, denied: 4 },
    { label: 'T7', granted: 45, denied: 2 },
    { label: 'CN', granted: 22, denied: 1 },
  ];
  const maxVal = Math.max(...data.map(d => d.granted + d.denied));
  const chart = $('#bar-chart');
  if (!chart) return;
  chart.innerHTML = data.map(d => {
    const grantedH = (d.granted / maxVal) * 100;
    const deniedH  = (d.denied  / maxVal) * 100;
    return `
      <div class="bar-group">
        <div class="bar-col">
          <div class="bar blue" style="height:${grantedH}%" title="Vào: ${d.granted}"></div>
          <div class="bar gold" style="height:${deniedH}%" title="Từ chối: ${d.denied}"></div>
        </div>
        <span class="bar-label">${d.label}</span>
      </div>`;
  }).join('');
}

function renderDonutChart() {
  const granted = MOCK_ACCESS_LOGS.filter(l => l.result === 'granted').length;
  const denied  = MOCK_ACCESS_LOGS.filter(l => l.result === 'denied').length;
  const total   = granted + denied;
  const pct     = Math.round(granted / total * 100);
  const el      = $('#donut-val');
  if (el) el.textContent = pct + '%';

  // SVG donut
  const svg = $('#donut-svg');
  if (!svg) return;
  const r = 54; const circ = 2 * Math.PI * r;
  const grantedDash = (granted / total) * circ;
  const deniedDash  = (denied  / total) * circ;
  svg.innerHTML = `
    <circle cx="70" cy="70" r="${r}" fill="none" stroke="#e2edf9" stroke-width="14"/>
    <circle cx="70" cy="70" r="${r}" fill="none" stroke="#10b981" stroke-width="14"
      stroke-dasharray="${grantedDash} ${circ}" stroke-linecap="round"/>
    <circle cx="70" cy="70" r="${r}" fill="none" stroke="#ef4444" stroke-width="14"
      stroke-dasharray="${deniedDash} ${circ}" stroke-dashoffset="-${grantedDash}" stroke-linecap="round"/>`;
}

function renderRecentLogs() {
  const feed = $('#dashboard-log-feed');
  if (!feed) return;
  feed.innerHTML = MOCK_ACCESS_LOGS.slice(0, 6).map(log => `
    <div class="log-item">
      <div class="log-icon ${log.result}">${log.result === 'granted' ? '✅' : '🚫'}</div>
      <div class="log-body">
        <div class="log-name">${log.name}</div>
        <div class="log-meta">${log.device} · Độ chính xác: ${log.confidence}%</div>
      </div>
      <span class="log-time">${log.time}</span>
    </div>`).join('');
}

/* ================================================
   USER TABLE
   ================================================ */
function renderUserTable(filter = '') {
  const tbody = $('#user-tbody');
  if (!tbody) return;
  const filtered = MOCK_USERS.filter(u =>
    u.name.toLowerCase().includes(filter.toLowerCase()) ||
    u.id.toLowerCase().includes(filter.toLowerCase()) ||
    u.dept.toLowerCase().includes(filter.toLowerCase())
  );
  tbody.innerHTML = filtered.map(u => `
    <tr>
      <td>
        <div class="table-avatar">
          <div class="table-avatar-img">${u.name.charAt(0)}</div>
          <div class="table-avatar-info">
            <div class="name">${u.name}</div>
            <div class="email">${u.email}</div>
          </div>
        </div>
      </td>
      <td><code style="font-size:0.78rem;color:var(--text-secondary)">${u.id}</code></td>
      <td>${u.dept}</td>
      <td>${u.role}</td>
      <td>${faceStatusBadge(u.faceStatus)}</td>
      <td>${statusBadge(u.status)}</td>
      <td style="color:var(--text-muted);font-size:0.8rem">${u.lastAccess}</td>
      <td>
        <div style="display:flex;gap:6px">
          <button class="btn btn-sm btn-outline" onclick="openEditUser('${u.id}')">✏️ Sửa</button>
          <button class="btn btn-sm btn-gold" onclick="openFaceReg('${u.id}')">📸 Khuôn mặt</button>
        </div>
      </td>
    </tr>`).join('');
}

function statusBadge(status) {
  return status === 'active'
    ? '<span class="badge badge-success">Hoạt động</span>'
    : '<span class="badge badge-neutral">Vô hiệu</span>';
}

function faceStatusBadge(fs) {
  const map = {
    enrolled: '<span class="badge badge-success">Đã đăng ký</span>',
    pending:  '<span class="badge badge-warning">Chờ đăng ký</span>',
    failed:   '<span class="badge badge-danger">Thất bại</span>',
  };
  return map[fs] || '<span class="badge badge-neutral">-</span>';
}

/* ================================================
   FACE REGISTRATION PAGE
   ================================================ */
function renderSessionTable(filter = '') {
  const tbody = $('#session-tbody');
  if (!tbody) return;
  const filtered = MOCK_SESSIONS.filter(s =>
    s.userName.toLowerCase().includes(filter.toLowerCase()) ||
    s.id.toLowerCase().includes(filter.toLowerCase())
  );
  tbody.innerHTML = filtered.map(s => `
    <tr>
      <td><code style="font-size:0.78rem;color:var(--text-secondary)">${s.id}</code></td>
      <td>
        <div class="table-avatar">
          <div class="table-avatar-img">${s.userName.charAt(0)}</div>
          <div class="table-avatar-info">
            <div class="name">${s.userName}</div>
            <div class="email">${s.userId}</div>
          </div>
        </div>
      </td>
      <td>${s.requestBy}</td>
      <td>${s.created}</td>
      <td>${s.expires}</td>
      <td>${sessionStatusBadge(s.status)}</td>
      <td>
        <div style="display:flex;gap:6px">
          ${s.status === 'pending'
            ? `<button class="btn btn-sm btn-primary" onclick="startRegistration('${s.id}')">▶ Bắt đầu</button>
               <button class="btn btn-sm btn-ghost" onclick="cancelSession('${s.id}')">✕ Hủy</button>`
            : `<button class="btn btn-sm btn-ghost" onclick="viewSession('${s.id}')">👁 Xem</button>`
          }
        </div>
      </td>
    </tr>`).join('');
}

function sessionStatusBadge(status) {
  const map = {
    pending:   '<span class="badge badge-warning">Chờ xử lý</span>',
    completed: '<span class="badge badge-success">Hoàn thành</span>',
    expired:   '<span class="badge badge-danger">Hết hạn</span>',
    cancelled: '<span class="badge badge-neutral">Đã hủy</span>',
  };
  return map[status] || '<span class="badge badge-neutral">-</span>';
}

/* ================================================
   ACCESS HISTORY TABLE
   ================================================ */
function renderHistoryTable(filter = '') {
  const tbody = $('#history-tbody');
  if (!tbody) return;
  const filtered = MOCK_ACCESS_LOGS.filter(l =>
    l.name.toLowerCase().includes(filter.toLowerCase()) ||
    l.device.toLowerCase().includes(filter.toLowerCase())
  );
  tbody.innerHTML = filtered.map(l => `
    <tr>
      <td><code style="font-size:0.78rem;color:var(--text-secondary)">${l.id}</code></td>
      <td>
        <div style="display:flex;align-items:center;gap:8px">
          <div class="log-icon ${l.result}" style="width:28px;height:28px;font-size:0.8rem">${l.result === 'granted' ? '✅' : '🚫'}</div>
          <span>${l.name}</span>
        </div>
      </td>
      <td>${l.device}</td>
      <td>${l.date} ${l.time}</td>
      <td>${l.result === 'granted'
        ? '<span class="badge badge-success">Cho phép</span>'
        : '<span class="badge badge-danger">Từ chối</span>'}</td>
      <td>
        <div style="display:flex;align-items:center;gap:8px">
          <div class="progress-bar-wrap" style="width:80px;height:6px">
            <div class="progress-bar-fill" style="width:${l.confidence}%;background:${l.confidence > 80 ? 'var(--success)' : l.confidence > 50 ? 'var(--warning)' : 'var(--danger)'}"></div>
          </div>
          <span style="font-size:0.78rem;font-weight:600">${l.confidence}%</span>
        </div>
      </td>
    </tr>`).join('');
}

/* ================================================
   LOG FEED
   ================================================ */
function renderLogFeed() {
  const feed = $('#live-log-feed');
  if (!feed) return;
  feed.innerHTML = MOCK_ACCESS_LOGS.map(log => `
    <div class="log-item">
      <div class="log-icon ${log.result}">${log.result === 'granted' ? '✅' : '🚫'}</div>
      <div class="log-body">
        <div class="log-name">${log.name}</div>
        <div class="log-meta">${log.device} · ${log.date}</div>
      </div>
      <span class="log-time">${log.time}</span>
    </div>`).join('');
}

/* ================================================
   DEVICES
   ================================================ */
function renderDevices() {
  const grid = $('#devices-grid');
  if (!grid) return;
  grid.innerHTML = MOCK_DEVICES.map(d => `
    <div class="device-card ${d.status}" onclick="openDeviceDetail('${d.id}')">
      <div class="device-header">
        <div>
          <div class="device-name">${d.name}</div>
          <div class="device-id">${d.id} · ${d.ip}</div>
        </div>
        <div class="device-icon">📡</div>
      </div>
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
        <span class="status-indicator">
          <span class="status-dot ${d.status}"></span>
          ${d.status === 'online' ? 'Trực tuyến' : d.status === 'warning' ? 'Cảnh báo' : 'Ngoại tuyến'}
        </span>
        <span style="font-size:0.75rem;color:var(--text-muted)">FW ${d.firmware}</span>
      </div>
      <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:12px">📍 ${d.location}</div>
      <div class="device-metrics">
        <div class="device-metric">
          <div class="metric-label">Lần cuối đồng bộ</div>
          <div class="metric-value">${d.lastSync}</div>
        </div>
        <div class="device-metric">
          <div class="metric-label">Hôm nay</div>
          <div class="metric-value">${d.totalToday} lượt</div>
        </div>
        <div class="device-metric">
          <div class="metric-label">Uptime</div>
          <div class="metric-value">${d.uptime}</div>
        </div>
        <div class="device-metric">
          <div class="metric-label">Trạng thái</div>
          <div class="metric-value" style="color:${d.status === 'online' ? 'var(--success)' : d.status === 'warning' ? 'var(--warning)' : 'var(--danger)'}">
            ${d.status === 'online' ? '● Online' : d.status === 'warning' ? '⚠ Warning' : '○ Offline'}
          </div>
        </div>
      </div>
    </div>`).join('');
}

/* ================================================
   MODALS
   ================================================ */
function openModal(id) {
  const overlay = $(`#modal-${id}`);
  if (overlay) overlay.classList.add('open');
}
function closeModal(id) {
  const overlay = $(`#modal-${id}`);
  if (overlay) overlay.classList.remove('open');
}

function openAddUser() { openModal('add-user'); }
function openEditUser(userId) {
  const user = MOCK_USERS.find(u => u.id === userId);
  if (!user) return;
  $('#edit-user-name').value  = user.name;
  $('#edit-user-email').value = user.email;
  $('#edit-user-dept').value  = user.dept;
  $('#edit-user-role').value  = user.role;
  openModal('edit-user');
}
function openFaceReg(userId) {
  const user = MOCK_USERS.find(u => u.id === userId);
  if (user) $('#quick-reg-user-name').textContent = user.name;
  openModal('quick-face-reg');
}
function openDeviceDetail(deviceId) {
  const dev = MOCK_DEVICES.find(d => d.id === deviceId);
  if (!dev) return;
  $('#device-detail-name').textContent   = dev.name;
  $('#device-detail-id').textContent     = dev.id;
  $('#device-detail-ip').textContent     = dev.ip;
  $('#device-detail-fw').textContent     = dev.firmware;
  $('#device-detail-loc').textContent    = dev.location;
  $('#device-detail-sync').textContent   = dev.lastSync;
  $('#device-detail-uptime').textContent = dev.uptime;
  openModal('device-detail');
}
function startRegistration(sessionId) {
  App.faceRegStep = 1;
  updateFaceRegWizard();
  openModal('face-capture');
}
function cancelSession(sessionId) {
  showToast('warning', 'Đã hủy phiên', `Phiên ${sessionId} đã được hủy.`);
}
function viewSession(sessionId) {
  showToast('info', 'Xem phiên', `Đang xem chi tiết phiên ${sessionId}.`);
}

function openNewSessionModal() { openModal('new-session'); }

/* ================================================
   FACE REGISTRATION WIZARD
   ================================================ */
function updateFaceRegWizard() {
  const steps = $$('#modal-face-capture .step');
  steps.forEach((step, i) => {
    step.classList.toggle('active', i === App.faceRegStep - 1);
    step.classList.toggle('done',   i < App.faceRegStep - 1);
  });
  $$('.reg-step-content').forEach((c, i) => {
    c.style.display = i === App.faceRegStep - 1 ? 'block' : 'none';
  });
}

function nextFaceRegStep() {
  if (App.faceRegStep < 3) {
    App.faceRegStep++;
    updateFaceRegWizard();
    if (App.faceRegStep === 2) startFakeScanAnimation();
  }
}
function prevFaceRegStep() {
  if (App.faceRegStep > 1) {
    App.faceRegStep--;
    updateFaceRegWizard();
  }
}

let scanInterval;
function startFakeScanAnimation() {
  clearInterval(scanInterval);
  App.capturedImages = 0;
  const counter    = $('#scan-counter');
  const progressFill = $('#scan-progress-fill');
  const statusMsg  = $('#scan-status-msg');
  const msgs = ['Đang định vị khuôn mặt...', 'Phát hiện khuôn mặt tốt!', 'Đang chụp ảnh...', 'Đang xử lý embedding...', 'Lưu dữ liệu...'];

  scanInterval = setInterval(() => {
    App.capturedImages++;
    const pct = Math.min((App.capturedImages / 5) * 100, 100);
    if (counter)     counter.textContent = `${App.capturedImages}/5`;
    if (progressFill) progressFill.style.width = pct + '%';
    if (statusMsg)   statusMsg.textContent = msgs[App.capturedImages - 1] || 'Hoàn thành!';
    if (App.capturedImages >= 5) {
      clearInterval(scanInterval);
      setTimeout(() => nextFaceRegStep(), 800);
    }
  }, 1200);
}

/* ================================================
   TOAST NOTIFICATIONS
   ================================================ */
function showToast(type, title, msg) {
  const iconMap = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
  const container = $('#toast-container');
  if (!container) return;
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `
    <span class="toast-icon">${iconMap[type]}</span>
    <div class="toast-body">
      <div class="toast-title">${title}</div>
      <div class="toast-msg">${msg}</div>
    </div>
    <button class="toast-close" onclick="this.parentElement.remove()">✕</button>`;
  container.appendChild(el);
  setTimeout(() => {
    el.classList.add('hide');
    setTimeout(() => el.remove(), 350);
  }, 4000);
}

/* ================================================
   FORM VALIDATION (basic)
   ================================================ */
function validateAddUser() {
  const name  = $('#new-user-name').value.trim();
  const email = $('#new-user-email').value.trim();
  const dept  = $('#new-user-dept').value;
  if (!name || !email || !dept) {
    showToast('error', 'Thiếu thông tin', 'Vui lòng điền đầy đủ các trường bắt buộc.');
    return false;
  }
  const emailReg = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailReg.test(email)) {
    showToast('error', 'Email không hợp lệ', 'Vui lòng nhập địa chỉ email hợp lệ.');
    return false;
  }
  return true;
}

function submitAddUser() {
  if (!validateAddUser()) return;
  const newUser = {
    id: 'USR' + String(MOCK_USERS.length + 1).padStart(3, '0'),
    name:       $('#new-user-name').value.trim(),
    email:      $('#new-user-email').value.trim(),
    dept:       $('#new-user-dept').value,
    role:       $('#new-user-role').value || 'Employee',
    status:     'active',
    faceStatus: 'pending',
    created:    new Date().toISOString().split('T')[0],
    lastAccess: 'Chưa có',
  };
  MOCK_USERS.push(newUser);
  closeModal('add-user');
  renderUserTable();
  showToast('success', 'Thêm người dùng', `${newUser.name} đã được thêm thành công.`);
  $('#add-user-form').reset();
}

function submitNewSession() {
  const userId = $('#session-user-select').value;
  const device = $('#session-device-select').value;
  if (!userId || !device) {
    showToast('error', 'Thiếu thông tin', 'Vui lòng chọn người dùng và thiết bị.');
    return;
  }
  const user = MOCK_USERS.find(u => u.id === userId);
  const newSession = {
    id: 'SES' + String(MOCK_SESSIONS.length + 1).padStart(3, '0'),
    userId, userName: user ? user.name : userId,
    requestBy: App.currentUser.name,
    status: 'pending',
    created: new Date().toLocaleString('vi-VN'),
    expires: 'Ngày mai',
    device,
  };
  MOCK_SESSIONS.push(newSession);
  closeModal('new-session');
  renderSessionTable();
  showToast('success', 'Tạo phiên đăng ký', `Phiên mới cho ${newSession.userName} đã được tạo.`);
}

function finishRegistration() {
  clearInterval(scanInterval);
  closeModal('face-capture');
  closeModal('quick-face-reg');
  showToast('success', 'Đăng ký hoàn tất', 'Khuôn mặt đã được đăng ký thành công!');
  renderUserTable();
  renderSessionTable();
}

/* ================================================
   SEARCH HANDLERS
   ================================================ */
function setupSearch() {
  const userSearch = $('#user-search-input');
  if (userSearch) userSearch.addEventListener('input', e => renderUserTable(e.target.value));

  const historySearch = $('#history-search-input');
  if (historySearch) historySearch.addEventListener('input', e => renderHistoryTable(e.target.value));

  const sessionSearch = $('#session-search-input');
  if (sessionSearch) sessionSearch.addEventListener('input', e => renderSessionTable(e.target.value));
}

/* ================================================
   PASSWORD TOGGLE
   ================================================ */
function togglePassword(inputId, btnEl) {
  const input = $(`#${inputId}`);
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    btnEl.textContent = '🙈';
  } else {
    input.type = 'password';
    btnEl.textContent = '👁';
  }
}

/* ================================================
   SIMULATE LIVE LOG
   ================================================ */
function startLiveSimulation() {
  const names = ['Nguyễn Văn An', 'Trần Thị Bình', 'Khách vãng lai', 'Lê Hoàng Cường', 'Unknown visitor'];
  const devices = ['Cổng Chính A', 'Cổng Phụ B', 'Cổng Kho C'];
  setInterval(() => {
    const isGranted = Math.random() > 0.25;
    const log = {
      id: 'LOG' + Date.now(),
      name: isGranted ? names[Math.floor(Math.random() * 4)] : names[4],
      device: devices[Math.floor(Math.random() * devices.length)],
      result: isGranted ? 'granted' : 'denied',
      time: new Date().toLocaleTimeString('vi-VN'),
      date: '29/09/2026',
      confidence: isGranted ? (85 + Math.random() * 15).toFixed(1) : (3 + Math.random() * 25).toFixed(1),
    };
    MOCK_ACCESS_LOGS.unshift(log);
    if (MOCK_ACCESS_LOGS.length > 50) MOCK_ACCESS_LOGS.pop();
    if (App.currentPage === 'dashboard') renderRecentLogs();
    if (App.currentPage === 'history') renderHistoryTable($('#history-search-input')?.value || '');
  }, 8000);
}

/* ================================================
   CONFIG PAGE HANDLERS
   ================================================ */
function setupConfigPage() {
  const saveConfigBtn = $('#save-config-btn');
  if (saveConfigBtn) {
    saveConfigBtn.addEventListener('click', () => {
      showToast('success', 'Lưu cấu hình', 'Các thay đổi đã được lưu thành công.');
    });
  }
}

/* ================================================
   POPULATE SELECT BOXES
   ================================================ */
function populateSelects() {
  const userSelect = $('#session-user-select');
  if (userSelect) {
    userSelect.innerHTML = '<option value="">-- Chọn người dùng --</option>' +
      MOCK_USERS.filter(u => u.faceStatus !== 'enrolled').map(u =>
        `<option value="${u.id}">${u.name} (${u.id})</option>`
      ).join('');
  }

  const deviceSelect = $('#session-device-select');
  if (deviceSelect) {
    deviceSelect.innerHTML = '<option value="">-- Chọn thiết bị --</option>' +
      MOCK_DEVICES.filter(d => d.status === 'online').map(d =>
        `<option value="${d.id}">${d.name}</option>`
      ).join('');
  }
}

/* ================================================
   INIT
   ================================================ */
document.addEventListener('DOMContentLoaded', () => {
  // Show login page
  $('#login-page').classList.add('active');
  $('#app-shell').style.display = 'none';

  // Login form
  const loginForm = $('#login-form');
  if (loginForm) loginForm.addEventListener('submit', handleLogin);

  // Nav items
  $$('.nav-item[data-page]').forEach(item => {
    item.addEventListener('click', () => navigateTo(item.dataset.page));
  });

  // Modal close buttons
  $$('.modal-close, [data-close-modal]').forEach(btn => {
    btn.addEventListener('click', () => {
      const overlay = btn.closest('.modal-overlay');
      if (overlay) overlay.classList.remove('open');
    });
  });
  $$('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => {
      if (e.target === overlay) overlay.classList.remove('open');
    });
  });

  // Logout
  const logoutBtn = $('#logout-btn');
  if (logoutBtn) logoutBtn.addEventListener('click', handleLogout);

  // Setup searches
  setupSearch();
  setupConfigPage();
  populateSelects();

  // Generate floating bubbles on login
  const bubbleContainer = $('#login-bubbles');
  if (bubbleContainer) {
    for (let i = 0; i < 12; i++) {
      const b = document.createElement('div');
      b.className = 'bubble';
      const size = 30 + Math.random() * 100;
      b.style.cssText = `width:${size}px;height:${size}px;left:${Math.random()*100}%;animation-duration:${8+Math.random()*12}s;animation-delay:${Math.random()*8}s`;
      bubbleContainer.appendChild(b);
    }
  }

  startLiveSimulation();
});

