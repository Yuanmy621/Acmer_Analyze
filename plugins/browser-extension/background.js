chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== 'bridge-import' && message?.type !== 'bridge-import-and-run') {
    return false;
  }

  const endpoint = message.type === 'bridge-import-and-run'
    ? 'http://127.0.0.1:8765/api/bridge/import-and-run'
    : 'http://127.0.0.1:8765/api/bridge/import';

  fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(message.payload),
  })
    .then(async (response) => {
      const data = await response.json();
      sendResponse({ ok: response.ok, data });
    })
    .catch((error) => {
      sendResponse({ ok: false, data: { error: String(error) } });
    });

  return true;
});
