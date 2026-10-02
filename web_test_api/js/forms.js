'use strict';

const STATUS_LABELS = {
  active: 'Hoạt động', inactive: 'Ngừng hoạt động', online: 'Online', offline: 'Offline', warning: 'Cảnh báo',
  pending: 'Chờ đăng ký', completed: 'Hoàn tất', cancelled: 'Đã hủy', expired: 'Hết hạn', failed: 'Thất bại',
  granted: 'Cho phép', denied: 'Từ chối',
};
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const choices = (...values) => values.map(value => [value, STATUS_LABELS[value]]);
const FORM_FIELDS = {
  users: [
    { name: 'user_code', label: 'Mã nhân viên', required: true, max: 50 },
    { name: 'full_name', label: 'Họ và tên', required: true, max: 150 },
    { name: 'email', label: 'Email', type: 'email', max: 150, nullable: true },
    { name: 'phone', label: 'Số điện thoại', type: 'tel', max: 20, nullable: true },
    { name: 'department', label: 'Phòng ban', max: 100, nullable: true },
    { name: 'role', label: 'Chức danh', max: 50, nullable: true },
    { name: 'status', label: 'Trạng thái', type: 'select', options: choices('active', 'inactive'), value: 'active' },
  ],
  devices: [
    { name: 'device_code', label: 'Mã thiết bị', required: true, max: 50 },
    { name: 'name', label: 'Tên thiết bị', required: true, max: 100 },
    { name: 'location', label: 'Vị trí', max: 200, nullable: true },
    { name: 'status', label: 'Trạng thái', type: 'select', options: choices('online', 'offline', 'warning'), value: 'offline' },
    { name: 'settings.threshold', label: 'Ngưỡng nhận diện (%)', type: 'number', min: 0, max: 100, step: 'any', required: true, value: 80 },
    { name: 'settings.doorDuration', label: 'Thời gian mở cửa (giây)', type: 'number', min: 1, max: 60, step: 1, required: true, value: 3 },
    { name: 'settings.liveness', label: 'Kiểm tra liveness', type: 'checkbox', value: true },
  ],
  sessions: [
    { name: 'user_id', label: 'Người dùng', type: 'select', source: 'activeUsers', required: true },
    { name: 'device_id', label: 'Thiết bị', type: 'select', source: 'devices', required: true },
    { name: 'expires_at', label: 'Hết hạn (giờ máy)', type: 'datetime-local', optional: true },
  ],
  logs: [
    { name: 'id', label: 'Mã sự kiện (UUID)', required: true, uuid: true },
    { name: 'device_id', label: 'Thiết bị', type: 'select', source: 'devices', required: true },
    { name: 'user_id', label: 'Người dùng', type: 'select', source: 'users', nullable: true },
    { name: 'result', label: 'Kết quả', type: 'select', options: choices('granted', 'denied'), value: 'denied' },
    { name: 'confidence', label: 'Độ tin cậy (%)', type: 'number', min: 0, max: 100, step: 'any', nullable: true },
    { name: 'access_time', label: 'Thời điểm truy cập (giờ máy)', type: 'datetime-local', required: true },
  ],
  embedding: [
    { name: 'model_name', label: 'Tên model', required: true, max: 100 },
    { name: 'model_version', label: 'Phiên bản model', required: true, max: 30 },
    { name: 'dimension', label: 'Số chiều', type: 'number', min: 1, max: 4096, step: 1, required: true },
    { name: 'image_url', label: 'URL ảnh', max: 2048, nullable: true },
    { name: 'embedding_data', label: 'Vector (mảng JSON)', type: 'textarea', required: true, max: 100000, wide: true },
  ],
};

function nestedValue(object, name) {
  return name.split('.').reduce((value, key) => value?.[key], object);
}

function localDateInput(value = new Date()) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const parts = [date.getFullYear(), date.getMonth() + 1, date.getDate(), date.getHours(), date.getMinutes(), date.getSeconds()];
  return `${parts[0]}-${String(parts[1]).padStart(2, '0')}-${String(parts[2]).padStart(2, '0')}T${String(parts[3]).padStart(2, '0')}:${String(parts[4]).padStart(2, '0')}:${String(parts[5]).padStart(2, '0')}`;
}

const Forms = {
  fields: [],
  render(kind, original, lookups, editing = false) {
    this.fields = FORM_FIELDS[kind];
    const container = document.querySelector('#editor-fields');
    container.replaceChildren();
    for (const field of this.fields) {
      const wrapper = document.createElement('div');
      wrapper.className = `field${field.wide ? ' wide' : ''}`;
      const label = document.createElement('label');
      const id = `field-${field.name.replaceAll('.', '-')}`;
      label.htmlFor = id;
      label.textContent = field.label;
      if (field.required) {
        const marker = document.createElement('span');
        marker.className = 'required';
        marker.textContent = ' *';
        label.append(marker);
      }
      let input;
      if (field.type === 'select') {
        input = document.createElement('select');
        let options = field.options;
        if (field.source) {
          const rows = field.source === 'devices' ? lookups.devices : lookups.users.filter(user => field.source !== 'activeUsers' || user.status === 'active');
          options = rows.filter(row => UUID_PATTERN.test(row.id)).map(row => [row.id,
            field.source === 'devices' ? `${row.name} · ${row.device_code}` : `${row.full_name} · ${row.user_code}`]);
          const blank = new Option(field.required ? 'Chọn...' : 'Không xác định', '');
          input.add(blank);
        }
        for (const [value, text] of options || []) input.add(new Option(text, value));
      } else {
        input = document.createElement(field.type === 'textarea' ? 'textarea' : 'input');
        if (field.type !== 'textarea') input.type = field.type || 'text';
      }
      input.id = id;
      input.name = field.name;
      input.required = Boolean(field.required);
      if (field.max !== undefined) {
        if (field.type === 'number') input.max = field.max;
        else input.maxLength = field.max;
      }
      if (field.min !== undefined) input.min = field.min;
      if (field.step !== undefined) input.step = field.step;
      if (field.type === 'datetime-local') input.step = '1';
      if (field.uuid) input.pattern = UUID_PATTERN.source.replaceAll('^', '').replaceAll('$', '');
      let value = nestedValue(original, field.name) ?? field.value ?? '';
      if (kind === 'logs' && !editing && field.name === 'id') value = crypto.randomUUID();
      if (kind === 'logs' && !editing && field.name === 'access_time') value = localDateInput();
      if (field.type === 'textarea' && Array.isArray(value)) value = JSON.stringify(value);
      if (field.type === 'datetime-local' && value) value = localDateInput(value);
      if (field.type === 'checkbox') input.checked = Boolean(value);
      else input.value = value;
      const error = document.createElement('span');
      error.id = `${id}-error`;
      error.className = 'field-error';
      input.setAttribute('aria-describedby', error.id);
      input.addEventListener('input', () => {
        input.setCustomValidity('');
        input.removeAttribute('aria-invalid');
        error.textContent = '';
      });
      if (field.type === 'checkbox') {
        wrapper.classList.add('checkbox-field');
        wrapper.append(input, label, error);
      } else wrapper.append(label, input, error);
      container.append(wrapper);
    }
  },
  clearErrors() {
    for (const field of this.fields) {
      const input = document.querySelector('#editor-form').elements.namedItem(field.name);
      input.setCustomValidity('');
      input.removeAttribute('aria-invalid');
      document.getElementById(`${input.id}-error`).textContent = '';
    }
  },
  fail(name, message) {
    const input = document.querySelector('#editor-form').elements.namedItem(name);
    if (input) {
      input.setAttribute('aria-invalid', 'true');
      document.getElementById(`${input.id}-error`).textContent = message;
      input.focus();
    }
    throw new ApiError(message, 400, 'CLIENT_VALIDATION');
  },
  read(kind, editing = false) {
    this.clearErrors();
    const form = document.querySelector('#editor-form');
    for (const input of form.querySelectorAll('input:not([type=checkbox]), textarea')) {
      if (!['number', 'datetime-local'].includes(input.type)) input.value = input.value.trim();
    }
    if (!form.reportValidity()) return null;
    const body = {};
    for (const field of this.fields) {
      const input = form.elements.namedItem(field.name);
      let value = input.type === 'checkbox' ? input.checked : input.value.trim();
      if (value === '' && field.optional) continue;
      if (value === '' && field.nullable) {
        if (!editing && kind !== 'logs') continue;
        value = null;
      } else if (field.type === 'number') {
        value = Number(value);
        if (!Number.isFinite(value)) this.fail(field.name, 'Giá trị phải là một số hữu hạn.');
      } else if (field.type === 'datetime-local') {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) this.fail(field.name, 'Ngày giờ không hợp lệ.');
        value = date.toISOString();
      } else if (field.type === 'textarea') {
        try { value = JSON.parse(value); }
        catch { this.fail(field.name, 'Vector phải là mảng JSON hợp lệ.'); }
      }
      if (field.uuid && !UUID_PATTERN.test(value)) this.fail(field.name, 'Mã phải là UUID hợp lệ.');
      if (field.name.startsWith('settings.')) {
        body.settings ||= {};
        body.settings[field.name.split('.')[1]] = value;
      } else body[field.name] = value;
    }
    if (kind === 'embedding') {
      if (!Array.isArray(body.embedding_data) || body.embedding_data.some(value => typeof value !== 'number' || !Number.isFinite(value))) {
        this.fail('embedding_data', 'Vector chỉ được chứa các số hữu hạn.');
      }
      if (body.embedding_data.length !== body.dimension) this.fail('dimension', `Số chiều phải bằng số phần tử vector (${body.embedding_data.length}).`);
    }
    if (kind === 'sessions' && body.expires_at && new Date(body.expires_at).getTime() <= Date.now() + 60000) {
      this.fail('expires_at', 'Thời hạn phải cách hiện tại hơn một phút.');
    }
    if (kind === 'logs' && body.result === 'granted' && !body.user_id) this.fail('user_id', 'Kết quả cho phép phải có người dùng.');
    return body;
  },
  serverErrors(details) {
    for (const detail of details || []) {
      let name = (detail.path || (detail.loc || []).join('.')).replace(/^body\./, '');
      if (name.startsWith('embedding_data.')) name = 'embedding_data';
      const input = document.querySelector('#editor-form').elements.namedItem(name);
      if (input) {
        input.setAttribute('aria-invalid', 'true');
        document.getElementById(`${input.id}-error`).textContent = detail.message || detail.msg || 'Giá trị không hợp lệ';
      }
    }
  },
};
