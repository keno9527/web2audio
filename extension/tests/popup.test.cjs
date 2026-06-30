const assert = require('node:assert/strict');
const { test } = require('node:test');

const {
  extractArticleFromTab,
  isSupportedArticleTabUrl,
} = require('../popup.js');

const MISSING_RECEIVER_ERROR =
  'Could not establish connection. Receiving end does not exist.';

function fakeChromeWithSendSequence(sequence) {
  const calls = {
    sendMessages: [],
    injections: [],
  };
  const chromeApi = {
    tabs: {
      async sendMessage(tabId, message) {
        calls.sendMessages.push({ tabId, message });
        const next = sequence.shift();
        if (next instanceof Error) {
          throw next;
        }
        return next;
      },
    },
    scripting: {
      async executeScript(options) {
        calls.injections.push(options);
      },
    },
  };
  return { chromeApi, calls };
}

test('recognizes regular article page URLs as supported', () => {
  assert.equal(isSupportedArticleTabUrl('https://example.com/article'), true);
  assert.equal(isSupportedArticleTabUrl('http://127.0.0.1:3000/post'), true);
  assert.equal(isSupportedArticleTabUrl('chrome://extensions'), false);
});

test('injects content script and retries when the active tab has no receiver', async () => {
  const payload = {
    source_url: 'https://example.com/article',
    title: '示例文章',
    text_content: '正文',
  };
  const { chromeApi, calls } = fakeChromeWithSendSequence([
    new Error(MISSING_RECEIVER_ERROR),
    { ok: true, payload },
  ]);

  const result = await extractArticleFromTab(chromeApi, {
    id: 42,
    url: 'https://example.com/article',
  });

  assert.deepEqual(result, payload);
  assert.equal(calls.sendMessages.length, 2);
  assert.deepEqual(calls.injections, [
    {
      target: { tabId: 42 },
      files: ['content.js'],
    },
  ]);
  assert.deepEqual(calls.sendMessages[0], {
    tabId: 42,
    message: { type: 'WEB2AUDIO_EXTRACT_ARTICLE' },
  });
});

test('does not message unsupported browser pages', async () => {
  const { chromeApi, calls } = fakeChromeWithSendSequence([]);

  await assert.rejects(
    () =>
      extractArticleFromTab(chromeApi, {
        id: 7,
        url: 'chrome://extensions',
      }),
    /当前页面不支持正文提取/,
  );

  assert.equal(calls.sendMessages.length, 0);
  assert.equal(calls.injections.length, 0);
});
