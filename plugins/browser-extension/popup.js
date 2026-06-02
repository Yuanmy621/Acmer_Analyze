const statusEl = document.getElementById('status');
const buttonEl = document.getElementById('send-current-page');
const targetTeamEl = document.getElementById('target-team');
const aliasesEl = document.getElementById('aliases');
const resultSummaryEl = document.getElementById('result-summary');

function setStatus(message) {
  statusEl.textContent = message;
}

function renderSummary(data) {
  const status = data?.status || 'unknown';
  const runId = data?.run_id || '-';
  const reportPath = data?.report_path || '-';
  const validationPath = data?.validation_path || '-';
  resultSummaryEl.innerHTML = `
    <div>状态：<code>${status}</code></div>
    <div>run_id：<code>${runId}</code></div>
    <div>report：<code>${reportPath}</code></div>
    <div>validation：<code>${validationPath}</code></div>
  `;
}

function parseAliases(rawValue, targetTeam) {
  const aliases = rawValue
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
  if (!aliases.includes(targetTeam)) {
    aliases.unshift(targetTeam);
  }
  return aliases;
}

function buildErrorMessage(data) {
  const errorType = data?.error_type ? `[${data.error_type}] ` : '';
  return `${errorType}${data?.error || 'unknown error'}`;
}

buttonEl.addEventListener('click', async () => {
  const targetTeam = targetTeamEl.value.trim();
  if (!targetTeam) {
    setStatus('请先填写目标队伍');
    return;
  }
  const aliases = parseAliases(aliasesEl.value.trim(), targetTeam);
  setStatus('正在读取当前页面...');
  renderSummary(null);

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    setStatus('未找到当前标签页');
    return;
  }

  chrome.tabs.sendMessage(tab.id, { type: 'collect-page-payload', targetTeam, aliases }, (contentResponse) => {
    if (chrome.runtime.lastError) {
      setStatus(`读取页面失败: ${chrome.runtime.lastError.message}`);
      return;
    }
    if (!contentResponse?.ok) {
      setStatus(`页面提取失败: ${contentResponse?.error || 'content script error'}`);
      return;
    }

    setStatus('正在发送到本地 bridge 并启动分析...');
    chrome.runtime.sendMessage(
      { type: 'bridge-import-and-run', payload: contentResponse.payload },
      (bridgeResponse) => {
        if (chrome.runtime.lastError) {
          setStatus(`发送失败: ${chrome.runtime.lastError.message}`);
          return;
        }
        const data = bridgeResponse?.data || { error: 'unknown error' };
        renderSummary(data);
        if (!bridgeResponse?.ok || data.ok === false) {
          setStatus(`bridge 执行失败: ${buildErrorMessage(data)}`);
          return;
        }
        setStatus(JSON.stringify(data, null, 2));
      },
    );
  });
});
