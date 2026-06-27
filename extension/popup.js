const serverUrlInput = document.getElementById('server-url');
const authTokenInput = document.getElementById('auth-token');
const submitButton = document.getElementById('submit');
const statusNode = document.getElementById('status');

function setStatus(message) {
  statusNode.textContent = message;
}

function normalizeServerUrl(value) {
  return String(value || '').replace(/\/+$/, '');
}

async function loadSettings() {
  const saved = await chrome.storage.local.get(['serverUrl', 'authToken']);
  if (saved.serverUrl) {
    serverUrlInput.value = saved.serverUrl;
  }
  if (saved.authToken) {
    authTokenInput.value = saved.authToken;
  }
}

async function saveSettings(serverUrl, authToken) {
  await chrome.storage.local.set({ serverUrl, authToken });
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) {
    throw new Error('未找到当前标签页');
  }
  return tab;
}

async function extractArticle(tabId) {
  const response = await chrome.tabs.sendMessage(tabId, {
    type: 'WEB2AUDIO_EXTRACT_ARTICLE',
  });
  if (!response || !response.ok) {
    throw new Error('无法提取当前页面正文');
  }
  return response.payload;
}

async function submitArticle(serverUrl, authToken, payload) {
  const response = await fetch(`${serverUrl}/api/articles`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  if (!response.ok) {
    const message = body && body.error ? body.error.message : '提交失败';
    throw new Error(message);
  }
  return body;
}

submitButton.addEventListener('click', async () => {
  const serverUrl = normalizeServerUrl(serverUrlInput.value);
  const authToken = authTokenInput.value;
  submitButton.disabled = true;
  setStatus('正在提交...');
  try {
    await saveSettings(serverUrl, authToken);
    const tab = await getActiveTab();
    const payload = await extractArticle(tab.id);
    const result = await submitArticle(serverUrl, authToken, payload);
    setStatus(result.created ? '已提交文章任务' : '文章已存在，已返回当前任务');
  } catch (error) {
    setStatus(error.message || '提交失败');
  } finally {
    submitButton.disabled = false;
  }
});

loadSettings().catch((error) => {
  setStatus(error.message || '配置读取失败');
});
