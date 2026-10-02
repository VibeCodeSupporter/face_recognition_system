'use strict';

const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const VIEWS = {
  users: { title: 'Người dùng', create: 'Thêm người dùng', path: '/users', headers: ['Người dùng', 'Mã nhân viên', 'Phòng ban', 'Chức danh', 'Liên hệ', 'Trạng thái', 'Ngày tạo', 'Thao tác'] },
  devices: { title: 'Thiết bị', create: 'Thêm thiết bị', path: '/devices', headers: ['Thiết bị', 'Mã thiết bị', 'Vị trí', 'Trạng thái', 'Cấu hình', 'Lần hoạt động', 'Thao tác'] },
  sessions: { title: 'Phiên đăng ký', create: 'Tạo phiên', path: '/registration-sessions', headers: ['Người dùng', 'Thiết bị', 'Trạng thái', 'Ngày tạo', 'Hết hạn', 'Hoàn tất', 'Thao tác'] },
  logs: { title: 'Lịch sử truy cập', create: 'Ghi sự kiện', path: '/access-logs', headers: ['Người dùng', 'Thiết bị', 'Kết quả', 'Độ tin cậy', 'Thời điểm truy cập', 'Đồng bộ', 'Thao tác'] },
};
const App = {
  view: 'users', rows: [], loaded: false, page: 0, pageSize: 20, hasMore: false, filters: {}, loading: false,
  users: [], devices: [], lookupsReady: false, loadVersion: 0, controller: null, editor: null, confirmation: null,
  pending: false, opening: false, token: '', toastTimer: null,
};

function dateText(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('vi-VN', {
    timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  }).format(date);
}
function toast(message, isError = false) {
  clearTimeout(App.toastTimer);
  $('#toast').textContent = message;
  $('#toast').className = `toast${isError ? ' error' : ''}`;
  $('#toast').hidden = false;
  App.toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 6500);
}
function showError(selector, error) {
  const element = $(selector);
  element.textContent = errorText(error);
  element.hidden = false;
}
function connectionState(connected, failed = false) {
  $('#connection-status').textContent = connected ? 'Đã kết nối' : failed ? 'Mất kết nối' : 'Chưa kết nối';
  $('#connection-status').className = `connection-status${connected ? ' connected' : failed ? ' failed' : ''}`;
  $('#connect-button span').textContent = connected ? 'API key' : 'Kết nối';
  $('#disconnect-button').hidden = !connected;
  updateControls();
}
function updateControls() {
  const blocked = !Api.key || App.loading || App.pending || App.opening;
  for (const selector of ['#create-button', '#apply-filters', '#reset-filters', '#page-size']) $(selector).disabled = blocked;
  $('#refresh-button').disabled = !Api.key || App.loading || App.pending;
  $('#previous-page').disabled = blocked || !App.loaded || App.page === 0;
  $('#next-page').disabled = blocked || !App.loaded || !App.hasMore;
  for (const button of $$('#table-body button')) button.disabled = blocked || !UUID_PATTERN.test(button.dataset.id);
}
function disconnect(failed = false) {
  Api.key = '';
  App.controller?.abort();
  App.loadVersion++;
  App.rows = []; App.users = []; App.devices = []; App.lookupsReady = false; App.loaded = false; App.loading = false; App.page = 0;
  App.token = '';
  $('#api-key').value = '';
  for (const dialog of $$('dialog[open]')) if (!App.pending) dialog.close();
  $('#detail-content').replaceChildren();
  $('#editor-fields').replaceChildren();
  App.editor = null;
  $('#page-error').hidden = !failed;
  if (failed) $('#page-error').textContent = ERROR_MESSAGES.UNAUTHORIZED;
  connectionState(false, failed);
  render();
}
Api.onUnauthorized = () => disconnect(true);

function optionHTML(value, label) { return `<option value="${escapeHTML(value)}">${escapeHTML(label)}</option>`; }
function filterSelect(name, label, options) {
  return `<label><span class="filter-label">${label}</span><select name="${name}" aria-label="${label}">${optionHTML('', label)}${options.map(([value, text]) => optionHTML(value, text)).join('')}</select></label>`;
}
function renderFilters() {
  let markup = '';
  if (App.view === 'users') {
    markup = filterSelect('status', 'Mọi trạng thái', choices('active', 'inactive')) + '<label><span class="filter-label">Phòng ban</span><input name="department" placeholder="Phòng ban" aria-label="Phòng ban" maxlength="100"></label>';
  } else if (App.view === 'devices') {
    markup = filterSelect('status', 'Mọi trạng thái', choices('online', 'offline', 'warning')) + '<label><span class="filter-label">Mã thiết bị</span><input name="device_code" placeholder="Mã thiết bị" aria-label="Mã thiết bị" maxlength="50"></label>';
  } else {
    const users = App.users.map(user => [user.id, `${user.full_name} · ${user.user_code}`]);
    const devices = App.devices.map(device => [device.id, `${device.name} · ${device.device_code}`]);
    markup = filterSelect('user_id', 'Mọi người dùng', users) + filterSelect('device_id', 'Mọi thiết bị', devices);
    markup += App.view === 'sessions' ? filterSelect('status', 'Mọi trạng thái', choices('pending', 'completed', 'cancelled', 'expired', 'failed')) : filterSelect('result', 'Mọi kết quả', choices('granted', 'denied'));
  }
  $('#filter-fields').innerHTML = markup;
  for (const [name, value] of Object.entries(App.filters)) {
    const element = $('#filters-form').elements.namedItem(name);
    if (element) element.value = value;
  }
  $('.search-field').hidden = App.view !== 'users';
}
async function allDevices(signal) {
  const items = [];
  let offset = 0;
  while (true) {
    const { data } = await Api.request(`/devices${queryString({ limit: 100, offset })}`, { signal });
    if (!Array.isArray(data?.items)) throw new ApiError('Danh sách thiết bị không đúng định dạng.', 0, 'INVALID_RESPONSE');
    items.push(...data.items);
    if (!data.has_more) return items;
    if (!data.items.length || offset >= 100000) throw new ApiError('Không tải được đầy đủ danh sách thiết bị.', 0, 'INVALID_RESPONSE');
    offset += data.items.length;
  }
}
async function loadLookups(signal, force = false) {
  if (App.lookupsReady && !force) return;
  const { data: users } = await Api.request('/users', { signal });
  if (!Array.isArray(users)) throw new ApiError('GET /users cần trả data là mảng và có id để quản trị.', 0, 'INVALID_RESPONSE');
  const devices = await allDevices(signal);
  if (!Api.key || signal?.aborted) return;
  App.users = users; App.devices = devices; App.lookupsReady = true;
}
async function loadView(forceLookups = false) {
  if (!Api.key || App.pending) return;
  App.controller?.abort();
  const controller = new AbortController();
  App.controller = controller;
  const version = ++App.loadVersion;
  const view = App.view;
  App.loading = true; App.loaded = false; App.rows = []; App.hasMore = false;
  $('#page-error').hidden = true;
  render();
  try {
    if (view === 'sessions' || view === 'logs') {
      await loadLookups(controller.signal, forceLookups);
      if (version !== App.loadVersion) return;
      renderFilters();
    }
    const params = { ...App.filters };
    if (view !== 'users') Object.assign(params, { limit: App.pageSize, offset: App.page * App.pageSize });
    const { data } = await Api.request(`${VIEWS[view].path}${queryString(params)}`, { signal: controller.signal });
    if (version !== App.loadVersion) return;
    if (view === 'users') {
      if (!Array.isArray(data)) throw new ApiError('GET /users cần trả data là mảng.', 0, 'INVALID_RESPONSE');
      App.rows = data;
      if (!Object.keys(App.filters).length) { App.users = data; App.lookupsReady = false; }
    } else {
      if (!Array.isArray(data?.items)) throw new ApiError('Danh sách API thiếu data.items.', 0, 'INVALID_RESPONSE');
      App.rows = data.items; App.hasMore = Boolean(data.has_more);
    }
    App.loaded = true;
    connectionState(true);
  } catch (error) {
    if (version !== App.loadVersion || error.code === 'CANCELLED') return;
    showError('#page-error', error);
    if (!error.status) $('#connection-status').textContent = 'Không nhận được phản hồi';
  } finally {
    if (version === App.loadVersion) { App.loading = false; render(); }
  }
}
function navigate(view) {
  if (!VIEWS[view] || App.pending || App.opening) return;
  App.view = view; App.page = 0; App.filters = {}; App.rows = []; App.loaded = false;
  $('#search').value = '';
  $('#page-error').hidden = true;
  for (const button of $$('.nav-item')) {
    button.classList.toggle('active', button.dataset.view === view);
    if (button.dataset.view === view) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  }
  $('#breadcrumb').textContent = VIEWS[view].title;
  $('#page-title').textContent = VIEWS[view].title;
  $('#create-button span').textContent = VIEWS[view].create;
  renderFilters(); render();
  if (Api.key) void loadView();
}

function personCell(row) {
  return `<div class="person-cell"><span class="avatar">${escapeHTML((row.full_name || '?').slice(0, 1).toUpperCase())}</span><div><div class="cell-primary">${escapeHTML(row.full_name || 'Không xác định')}</div><div class="cell-secondary cell-code" title="${escapeHTML(row.id)}">${escapeHTML(row.id ? `${row.id.slice(0, 8)}…` : 'Thiếu ID')}</div></div></div>`;
}
function referenceName(rows, id, user = false) {
  if (!id) return 'Không xác định';
  const item = rows.find(row => row.id === id);
  return item ? (user ? `${item.full_name} · ${item.user_code}` : `${item.name} · ${item.device_code}`) : id;
}
function badge(value) { return `<span class="badge ${Object.hasOwn(STATUS_LABELS, value) ? value : ''}">${escapeHTML(STATUS_LABELS[value] || value || '—')}</span>`; }
function actionButton(action, id, icon, label, destructive = false) {
  return `<button type="button" class="icon-button${destructive ? ' destructive' : ''}" data-action="${action}" data-id="${escapeHTML(id)}" title="${label}" aria-label="${label}"${UUID_PATTERN.test(id) ? '' : ' disabled'}><i class="fa-solid ${icon}" aria-hidden="true"></i></button>`;
}
function rowHTML(row) {
  const view = App.view;
  const actions = [actionButton('detail', row.id, 'fa-eye', 'Chi tiết')];
  let cells;
  if (view === 'users') {
    cells = [personCell(row), escapeHTML(row.user_code), escapeHTML(row.department || '—'), escapeHTML(row.role || '—'),
      `<div>${escapeHTML(row.email || '—')}</div><div class="cell-secondary">${escapeHTML(row.phone || '—')}</div>`, badge(row.status), escapeHTML(dateText(row.created_at))];
    actions.push(actionButton('edit', row.id, 'fa-pen', 'Sửa người dùng'), actionButton('embedding', row.id, 'fa-fingerprint', 'Vector khuôn mặt'), actionButton('delete', row.id, 'fa-trash', 'Xóa người dùng', true));
  } else if (view === 'devices') {
    cells = [escapeHTML(row.name), escapeHTML(row.device_code), escapeHTML(row.location || '—'), badge(row.status),
      `${escapeHTML(row.settings?.threshold ?? '—')}% · ${escapeHTML(row.settings?.doorDuration ?? '—')}s<div class="cell-secondary">Liveness: ${row.settings?.liveness ? 'Bật' : 'Tắt'}</div>`, escapeHTML(dateText(row.last_seen_at))];
    actions.push(actionButton('edit', row.id, 'fa-pen', 'Sửa thiết bị'), actionButton('delete', row.id, 'fa-trash', 'Xóa thiết bị', true));
  } else if (view === 'sessions') {
    cells = [escapeHTML(referenceName(App.users, row.user_id, true)), escapeHTML(referenceName(App.devices, row.device_id)), badge(row.status), escapeHTML(dateText(row.created_at)), escapeHTML(dateText(row.expires_at)), escapeHTML(dateText(row.completed_at))];
    if (row.status === 'pending' && new Date(row.expires_at).getTime() > Date.now()) {
      actions.push(actionButton('embedding', row.user_id, 'fa-fingerprint', 'Vector khuôn mặt'), actionButton('completed', row.id, 'fa-check', 'Hoàn tất phiên'), actionButton('cancelled', row.id, 'fa-ban', 'Hủy phiên'), actionButton('failed', row.id, 'fa-triangle-exclamation', 'Đánh dấu thất bại'));
    }
    actions.push(actionButton('delete', row.id, 'fa-trash', 'Xóa phiên', true));
  } else {
    cells = [escapeHTML(referenceName(App.users, row.user_id, true)), escapeHTML(referenceName(App.devices, row.device_id)), badge(row.result), row.confidence == null ? '—' : `${escapeHTML(row.confidence)}%`, escapeHTML(dateText(row.access_time)), escapeHTML(dateText(row.synced_at))];
  }
  return `<tr data-record-id="${escapeHTML(row.id)}">${cells.map(cell => `<td>${cell}</td>`).join('')}<td><div class="cell-actions">${actions.join('')}</div></td></tr>`;
}
function render() {
  $('#table-head').innerHTML = `<tr>${VIEWS[App.view].headers.map(label => `<th scope="col">${label}</th>`).join('')}</tr>`;
  let rows = App.rows;
  let total = rows.length;
  if (App.view === 'users') {
    const search = $('#search').value.trim().toLocaleLowerCase('vi');
    rows = rows.filter(row => [row.full_name, row.user_code, row.email].some(value => String(value || '').toLocaleLowerCase('vi').includes(search)));
    total = rows.length;
    App.page = Math.min(App.page, Math.max(0, Math.ceil(total / App.pageSize) - 1));
    App.hasMore = (App.page + 1) * App.pageSize < total;
    rows = rows.slice(App.page * App.pageSize, (App.page + 1) * App.pageSize);
  }
  const empty = App.loading ? 'Đang tải dữ liệu...' : !Api.key ? 'Chưa kết nối backend' : !App.loaded ? 'Không tải được dữ liệu' : 'Không có bản ghi phù hợp';
  $('#table-body').innerHTML = rows.length ? rows.map(rowHTML).join('') : `<tr><td colspan="${VIEWS[App.view].headers.length}" class="empty-cell">${empty}</td></tr>`;
  $('#record-summary').textContent = App.loading ? 'Đang tải...' : !App.loaded ? 'Chưa tải dữ liệu' : App.view === 'users' ? `${total.toLocaleString('vi-VN')} người dùng` : `${rows.length} bản ghi trên trang hiện tại`;
  const first = rows.length ? App.page * App.pageSize + 1 : 0;
  const last = rows.length ? first + rows.length - 1 : 0;
  $('#page-range').textContent = App.loaded ? `${first}–${last}${App.view === 'users' ? ` / ${total}` : ''}` : '0 bản ghi';
  $('#page-number').textContent = App.page + 1;
  updateControls();
}

function setBusy(dialog, busy) {
  App.pending = busy;
  dialog.dataset.busy = String(busy);
  for (const element of dialog.querySelectorAll('button, input, select, textarea')) element.disabled = busy;
  for (const button of $$('.nav-item')) button.disabled = busy;
  $('#disconnect-button').disabled = busy;
  $('#connect-button').disabled = busy;
  updateControls();
}
function closeDialog(dialog) {
  if (dialog.dataset.busy === 'true') return;
  if (dialog.id === 'detail-dialog') {
    App.token = '';
    $('#detail-content').replaceChildren();
  }
  dialog.close();
}
function resetEditor() {
  $('#editor-error').hidden = true;
  $('#editor-error').textContent = '';
  $('#save-button span').textContent = 'Lưu';
}
async function openEditor(kind, id = null) {
  if (!Api.key || App.opening || App.pending) return;
  App.opening = true; updateControls();
  const generation = App.loadVersion;
  try {
    let original = {};
    if (kind === 'sessions' || kind === 'logs') await loadLookups(undefined, true);
    if (id) {
      const path = kind === 'embedding' ? `/users/${id}/face-embedding` : `${VIEWS[kind].path}/${id}`;
      try { original = (await Api.request(path)).data; }
      catch (error) { if (kind !== 'embedding' || error.status !== 404) throw error; }
    }
    if (!Api.key || generation !== App.loadVersion) return;
    resetEditor();
    App.editor = { kind, id, original };
    const title = kind === 'embedding' ? `Vector khuôn mặt · ${referenceName(App.users.length ? App.users : App.rows, id, true)}` : `${id ? 'Sửa' : 'Tạo'} ${kind === 'users' ? 'người dùng' : kind === 'devices' ? 'thiết bị' : kind === 'sessions' ? 'phiên đăng ký' : 'sự kiện truy cập'}`;
    $('#editor-title').textContent = title;
    Forms.render(kind, original, App, Boolean(id));
    if (kind === 'embedding' && original.user_id) {
      const remove = document.createElement('button');
      remove.type = 'button'; remove.className = 'button secondary'; remove.id = 'delete-embedding';
      remove.innerHTML = '<i class="fa-solid fa-trash" aria-hidden="true"></i><span>Xóa vector</span>';
      remove.addEventListener('click', () => {
        $('#editor-dialog').close();
        openConfirmation('delete-embedding', id);
      });
      $('#editor-fields').append(remove);
    }
    $('#editor-dialog').showModal();
  } catch (error) { showError('#page-error', error); }
  finally { App.opening = false; updateControls(); }
}
async function saveEditor(event) {
  event.preventDefault();
  if (App.pending || !App.editor) return;
  const { kind, id, original } = App.editor;
  let body;
  try {
    body = Forms.read(kind, Boolean(id));
    if (!body) return;
    if (id && kind !== 'embedding') {
      body = Object.fromEntries(Object.entries(body).filter(([name, value]) => {
        if (name === 'settings') return Object.keys(value).some(key => value[key] !== original.settings?.[key]);
        return value !== (original[name] ?? null);
      }));
      if (!Object.keys(body).length) { toast('Không có thay đổi để lưu.'); return; }
    }
  } catch (error) { showError('#editor-error', error); return; }
  setBusy($('#editor-dialog'), true);
  $('#save-button span').textContent = 'Đang lưu...';
  $('#editor-error').hidden = true;
  try {
    const path = kind === 'embedding' ? `/users/${id}/face-embedding` : `${VIEWS[kind].path}${id ? `/${id}` : ''}`;
    const { data, status } = await Api.request(path, { method: kind === 'embedding' ? 'PUT' : id ? 'PATCH' : 'POST', body });
    App.lookupsReady = false;
    $('#editor-dialog').close();
    toast(kind === 'logs' && status === 200 ? 'Sự kiện đã tồn tại với cùng nội dung, không tạo bản ghi trùng.' : 'Đã lưu vào database.');
    if (kind === 'devices' && !id && data.device_token) showDetail('Token thiết bị mới', data, kind, true);
  } catch (error) {
    showError('#editor-error', error);
    Forms.serverErrors(error.details);
  } finally {
    setBusy($('#editor-dialog'), false);
    $('#save-button span').textContent = 'Lưu';
    if (!$('#editor-dialog').open && Api.key) await loadView(true);
  }
}

const DETAIL_LABELS = {
  id: 'ID', user_code: 'Mã nhân viên', full_name: 'Họ và tên', email: 'Email', phone: 'Số điện thoại', department: 'Phòng ban', role: 'Chức danh', status: 'Trạng thái', created_at: 'Ngày tạo', updated_at: 'Cập nhật',
  device_code: 'Mã thiết bị', name: 'Tên thiết bị', location: 'Vị trí', settings: 'Cấu hình', last_seen_at: 'Lần hoạt động',
  user_id: 'Người dùng', device_id: 'Thiết bị', expires_at: 'Hết hạn', completed_at: 'Hoàn tất', result: 'Kết quả', confidence: 'Độ tin cậy (%)', access_time: 'Thời điểm truy cập', synced_at: 'Đồng bộ',
};
function showDetail(title, row, kind, withToken = false) {
  $('#detail-title').textContent = title;
  const list = document.createElement('dl'); list.className = 'metadata';
  const keys = kind === 'users' ? ['id', 'user_code', 'full_name', 'email', 'phone', 'department', 'role', 'status', 'created_at', 'updated_at'] :
    kind === 'devices' ? ['id', 'device_code', 'name', 'location', 'status', 'settings', 'last_seen_at', 'created_at'] :
    kind === 'sessions' ? ['id', 'user_id', 'device_id', 'status', 'created_at', 'expires_at', 'completed_at'] : ['id', 'user_id', 'device_id', 'result', 'confidence', 'access_time', 'synced_at'];
  for (const key of keys) {
    const term = document.createElement('dt'); term.textContent = DETAIL_LABELS[key];
    const value = document.createElement('dd');
    const raw = row[key];
    value.textContent = raw == null ? '—' : key.endsWith('_at') ? dateText(raw) : key === 'settings' ? JSON.stringify(raw, null, 2) : key === 'status' || key === 'result' ? STATUS_LABELS[raw] || raw : String(raw);
    list.append(term, value);
  }
  $('#detail-content').replaceChildren(list);
  App.token = withToken ? row.device_token : '';
  $('#copy-token').hidden = !App.token;
  if (App.token) {
    const notice = document.createElement('p'); notice.className = 'token-notice'; notice.textContent = 'Token chỉ trả về một lần khi tạo thiết bị. Lưu token trước khi đóng cửa sổ.';
    const token = document.createElement('code'); token.className = 'secret-token'; token.textContent = App.token;
    $('#detail-content').append(notice, token);
  }
  $('#detail-dialog').showModal();
}
async function openDetail(id) {
  if (!Api.key || App.pending || App.opening) return;
  App.opening = true; updateControls();
  const kind = App.view;
  try {
    const { data } = await Api.request(`${VIEWS[kind].path}/${id}`);
    if (Api.key && kind === App.view) showDetail('Chi tiết', data, kind);
  } catch (error) { showError('#page-error', error); }
  finally { App.opening = false; updateControls(); }
}
function openConfirmation(action, id) {
  const row = App.rows.find(item => item.id === id);
  App.confirmation = { action, id, kind: App.view };
  $('#confirm-error').hidden = true;
  const deletion = action.startsWith('delete');
  $('#confirm-title').textContent = deletion ? action === 'delete-embedding' ? 'Xóa vector khuôn mặt?' : 'Xóa bản ghi?' : `${STATUS_LABELS[action]} phiên đăng ký?`;
  $('#confirm-message').textContent = deletion ? `Thao tác không thể hoàn tác. ${row?.full_name || row?.name || row?.user_code || id}` : `Phiên ${id}. Trạng thái sau khi kết thúc không thể đổi lại.`;
  $('#confirm-button').className = `button ${deletion ? 'danger' : 'primary'}`;
  $('#confirm-button').textContent = deletion ? 'Xóa' : 'Xác nhận';
  $('#confirm-dialog').showModal();
}
async function submitConfirmation(event) {
  event.preventDefault();
  if (!App.confirmation || App.pending) return;
  const { action, id, kind } = App.confirmation;
  setBusy($('#confirm-dialog'), true);
  $('#confirm-error').hidden = true;
  try {
    if (action === 'delete-embedding') await Api.request(`/users/${id}/face-embedding`, { method: 'DELETE' });
    else if (action === 'delete') await Api.request(`${VIEWS[kind].path}/${id}`, { method: 'DELETE' });
    else await Api.request(`/registration-sessions/${id}`, { method: 'PATCH', body: { status: action } });
    App.lookupsReady = false;
    $('#confirm-dialog').close();
    toast(action.startsWith('delete') ? 'Đã xóa bản ghi.' : 'Đã cập nhật trạng thái phiên.');
  } catch (error) { showError('#confirm-error', error); }
  finally {
    setBusy($('#confirm-dialog'), false);
    if (!$('#confirm-dialog').open && Api.key) await loadView(true);
  }
}

$('#connection-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (App.pending) return;
  const key = $('#api-key').value.trim();
  if (!/^[A-Za-z0-9_-]{32,256}$/.test(key)) {
    showError('#connection-error', new ApiError('Nhập BACKEND_API_KEY, không dùng Supabase key hoặc tiền tố Bearer.'));
    return;
  }
  setBusy($('#connection-dialog'), true);
  $('#connection-error').hidden = true;
  try {
    await Api.request('/health', { key });
    Api.key = key;
    $('#api-key').value = '';
    App.lookupsReady = false;
    $('#connection-dialog').close();
    connectionState(true);
  } catch (error) { showError('#connection-error', error); }
  finally {
    setBusy($('#connection-dialog'), false);
    if (!$('#connection-dialog').open && Api.key) await loadView(true);
  }
});
$('#connect-button').addEventListener('click', () => {
  $('#connection-error').hidden = true;
  $('#api-key').value = '';
  $('#api-origin').value = `${location.origin}/api/v1`;
  $('#connection-dialog').showModal();
});
$('#disconnect-button').addEventListener('click', () => disconnect());
$('#refresh-button').addEventListener('click', () => { void loadView(true); });
$('#create-button').addEventListener('click', () => { void openEditor(App.view); });
$('#editor-form').addEventListener('submit', saveEditor);
$('#confirm-form').addEventListener('submit', submitConfirmation);
for (const button of $$('.nav-item')) button.addEventListener('click', () => navigate(button.dataset.view));
$('.brand').addEventListener('click', event => { event.preventDefault(); navigate('users'); });
$('#filters-form').addEventListener('submit', event => {
  event.preventDefault();
  if (!Api.key || App.pending) return;
  App.filters = Object.fromEntries([...new FormData(event.target)].map(([name, value]) => [name, String(value).trim()]).filter(([, value]) => value));
  App.page = 0;
  void loadView();
});
$('#reset-filters').addEventListener('click', () => { App.filters = {}; App.page = 0; $('#search').value = ''; renderFilters(); void loadView(); });
$('#search').addEventListener('input', () => { App.page = 0; render(); });
$('#page-size').addEventListener('change', () => {
  App.pageSize = Number($('#page-size').value); App.page = 0;
  if (App.view === 'users') render(); else void loadView();
});
$('#previous-page').addEventListener('click', () => { if (App.page > 0) App.page--; if (App.view === 'users') render(); else void loadView(); });
$('#next-page').addEventListener('click', () => { if (!App.hasMore) return; App.page++; if (App.view === 'users') render(); else void loadView(); });
$('#table-body').addEventListener('click', event => {
  const button = event.target.closest('button[data-action]');
  if (!button || button.disabled || !UUID_PATTERN.test(button.dataset.id)) return;
  const { action, id } = button.dataset;
  if (action === 'detail') void openDetail(id);
  else if (action === 'edit') void openEditor(App.view, id);
  else if (action === 'embedding') void openEditor('embedding', id);
  else openConfirmation(action, id);
});
for (const button of $$('[data-close]')) button.addEventListener('click', () => closeDialog(button.closest('dialog')));
for (const dialog of $$('dialog')) {
  dialog.addEventListener('cancel', event => { if (dialog.dataset.busy === 'true') event.preventDefault(); });
  dialog.addEventListener('close', () => {
    if (dialog.id === 'connection-dialog') $('#api-key').value = '';
    if (dialog.id === 'detail-dialog') { App.token = ''; $('#detail-content').replaceChildren(); }
    if (!Api.key && !App.pending) { $('#editor-fields').replaceChildren(); App.editor = null; }
  });
}
$('#copy-token').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText(App.token); toast('Đã sao chép token thiết bị.'); }
  catch { toast('Không sao chép được. Bạn có thể chọn token để sao chép thủ công.', true); }
});
window.addEventListener('pagehide', () => { Api.key = ''; App.token = ''; });
navigate('users');
