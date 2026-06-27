function readMeta(doc, selectors) {
  for (const selector of selectors) {
    const node = doc.querySelector(selector);
    if (!node) {
      continue;
    }
    const value = node.getAttribute('content') || node.textContent || '';
    const trimmed = normalizeText(value);
    if (trimmed) {
      return trimmed;
    }
  }
  return null;
}

function normalizeText(value) {
  return String(value || '')
    .replace(/\r/g, '\n')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{2,}/g, '\n')
    .replace(/[ \t]{2,}/g, ' ')
    .trim();
}

function readArticleText(doc) {
  const selectors = ['article', 'main', '[role="main"]', 'body'];
  for (const selector of selectors) {
    const node = doc.querySelector(selector);
    if (!node) {
      continue;
    }
    const text = normalizeText(node.textContent);
    if (text) {
      return text;
    }
  }
  return '';
}

function extractArticleFromDocument(doc = document) {
  return {
    source_url: doc.location.href,
    title:
      readMeta(doc, [
        'meta[property="og:title"]',
        'meta[name="twitter:title"]',
      ]) || normalizeText(doc.title),
    text_content: readArticleText(doc),
    site_name: readMeta(doc, [
      'meta[property="og:site_name"]',
      'meta[name="application-name"]',
    ]),
    author: readMeta(doc, [
      'meta[name="author"]',
      'meta[property="article:author"]',
    ]),
    published_at: readMeta(doc, [
      'meta[property="article:published_time"]',
      'meta[name="publishdate"]',
      'time[datetime]',
    ]),
    cover_url: readMeta(doc, [
      'meta[property="og:image"]',
      'meta[name="twitter:image"]',
    ]),
    language_hint: doc.documentElement ? doc.documentElement.lang || null : null,
  };
}

if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.onMessage) {
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message && message.type === 'WEB2AUDIO_EXTRACT_ARTICLE') {
      sendResponse({ ok: true, payload: extractArticleFromDocument(document) });
    }
    return true;
  });
}

if (typeof module !== 'undefined') {
  module.exports = {
    extractArticleFromDocument,
    normalizeText,
  };
}
