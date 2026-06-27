const assert = require('node:assert/strict');
const { test } = require('node:test');

const { extractArticleFromDocument } = require('../content.js');

function element(textContent, attrs = {}) {
  return {
    textContent,
    getAttribute(name) {
      return attrs[name] ?? null;
    },
  };
}

function fakeDocument() {
  const meta = {
    'meta[property="og:site_name"]': element('', { content: '微信公众平台' }),
    'meta[name="author"]': element('', { content: '作者' }),
    'meta[property="article:published_time"]': element('', {
      content: '2026-06-27T08:00:00Z',
    }),
    'meta[property="og:image"]': element('', {
      content: 'https://example.com/cover.jpg',
    }),
  };
  return {
    title: '示例文章标题 - 微信公众平台',
    location: { href: 'https://mp.weixin.qq.com/s/sVgTl03Hh3zaNFBh7X-ckQ' },
    documentElement: { lang: 'zh-CN' },
    querySelector(selector) {
      if (selector === 'article') {
        return element('第一段正文。\n\n第二段正文。');
      }
      return meta[selector] ?? null;
    },
  };
}

test('extracts article payload from the active document', () => {
  const payload = extractArticleFromDocument(fakeDocument());

  assert.deepEqual(payload, {
    source_url: 'https://mp.weixin.qq.com/s/sVgTl03Hh3zaNFBh7X-ckQ',
    title: '示例文章标题 - 微信公众平台',
    text_content: '第一段正文。\n第二段正文。',
    site_name: '微信公众平台',
    author: '作者',
    published_at: '2026-06-27T08:00:00Z',
    cover_url: 'https://example.com/cover.jpg',
    language_hint: 'zh-CN',
  });
});

test('falls back to body text when no article element exists', () => {
  const doc = fakeDocument();
  doc.querySelector = (selector) => {
    if (selector === 'body') {
      return element('页面正文');
    }
    return null;
  };

  const payload = extractArticleFromDocument(doc);

  assert.equal(payload.text_content, '页面正文');
  assert.equal(payload.site_name, null);
});
