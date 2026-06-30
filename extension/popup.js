const EXTRACT_ARTICLE_MESSAGE = { type: 'WEB2AUDIO_EXTRACT_ARTICLE' };
const UNSUPPORTED_TAB_MESSAGE =
  '当前页面不支持正文提取，请切换到普通 http/https 文章页后重试。';
const CONTENT_SCRIPT_UNAVAILABLE_MESSAGE =
  '当前页面还没有可用的正文提取脚本，请刷新当前网页或切换到普通文章页后重试。';

const hasDocument = typeof document !== 'undefined';
const serverUrlInput = hasDocument ? document.getElementById('server-url') : null;
const authTokenInput = hasDocument ? document.getElementById('auth-token') : null;
const submitButton = hasDocument ? document.getElementById('submit') : null;
const statusNode = hasDocument ? document.getElementById('status') : null;

function setStatus(message) {
  if (statusNode) {
    statusNode.textContent = message;
  }
}

function normalizeServerUrl(value) {
  return String(value || '').replace(/\/+$/, '');
}

async function loadSettings(chromeApi = chrome) {
  const saved = await chromeApi.storage.local.get(['serverUrl', 'authToken']);
  if (saved.serverUrl && serverUrlInput) {
    serverUrlInput.value = saved.serverUrl;
  }
  if (saved.authToken && authTokenInput) {
    authTokenInput.value = saved.authToken;
  }
}

async function saveSettings(serverUrl, authToken, chromeApi = chrome) {
  await chromeApi.storage.local.set({ serverUrl, authToken });
}

async function getActiveTab(chromeApi = chrome) {
  const [tab] = await chromeApi.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) {
    throw new Error('未找到当前标签页');
  }
  return tab;
}

function isSupportedArticleTabUrl(url) {
  return /^https?:\/\//i.test(String(url || ''));
}

function isMissingReceiverError(error) {
  const message = error && error.message ? error.message : String(error || '');
  return (
    message.includes('Could not establish connection') ||
    message.includes('Receiving end does not exist')
  );
}

async function sendExtractArticleMessage(chromeApi, tabId) {
  return chromeApi.tabs.sendMessage(tabId, EXTRACT_ARTICLE_MESSAGE);
}

async function injectContentScript(chromeApi, tabId) {
  await chromeApi.scripting.executeScript({
    target: { tabId },
    files: ['content.js'],
  });
}

async function extractArticleFromTab(chromeApi, tab) {
  if (!tab || !tab.id) {
    throw new Error('未找到当前标签页');
  }
  if (tab.url && !isSupportedArticleTabUrl(tab.url)) {
    throw new Error(UNSUPPORTED_TAB_MESSAGE);
  }

  let response;
  try {
    response = await sendExtractArticleMessage(chromeApi, tab.id);
  } catch (error) {
    if (!isMissingReceiverError(error)) {
      throw error;
    }
    try {
      await injectContentScript(chromeApi, tab.id);
      response = await sendExtractArticleMessage(chromeApi, tab.id);
    } catch (retryError) {
      if (isMissingReceiverError(retryError)) {
        throw new Error(CONTENT_SCRIPT_UNAVAILABLE_MESSAGE);
      }
      throw retryError;
    }
  }

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

if (submitButton) {
  submitButton.addEventListener('click', async () => {
    const serverUrl = normalizeServerUrl(serverUrlInput.value);
    const authToken = authTokenInput.value;
    submitButton.disabled = true;
    setStatus('正在提交...');
    try {
      await saveSettings(serverUrl, authToken);
      const tab = await getActiveTab();
      const payload = await extractArticleFromTab(chrome, tab);
      const result = await submitArticle(serverUrl, authToken, payload);
      setStatus(result.created ? '已提交文章任务' : '文章已存在，已返回当前任务');
    } catch (error) {
      setStatus(error.message || '提交失败');
    } finally {
      submitButton.disabled = false;
    }
  });
}

if (hasDocument && typeof chrome !== 'undefined' && chrome.storage) {
  loadSettings().catch((error) => {
    setStatus(error.message || '配置读取失败');
  });
}

if (typeof module !== 'undefined') {
  module.exports = {
    extractArticleFromTab,
    isMissingReceiverError,
    isSupportedArticleTabUrl,
    normalizeServerUrl,
  };
}
