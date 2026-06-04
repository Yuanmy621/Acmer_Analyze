const statusEl = document.getElementById('status');
const buttonEl = document.getElementById('send-current-page');
const targetTeamEl = document.getElementById('target-team');
const linksEl = document.getElementById('links');

const BRIDGE_BASE_URL = 'http://127.0.0.1:8765';

function setStatus(message, type = '') {
  statusEl.textContent = message;
  statusEl.className = 'status-box ' + type;
  linksEl.innerHTML = '';
}

function showLinks(data) {
  const reportUrl = data?.report_path ? `${BRIDGE_BASE_URL}/${data.report_path}` : null;
  const visualizationUrl = data?.visualization_path ? `${BRIDGE_BASE_URL}/${data.visualization_path}` : null;
  const validationUrl = data?.validation_path ? `${BRIDGE_BASE_URL}/${data.validation_path}` : null;

  let html = '';
  if (reportUrl) html += `<div>📊 <a href="${reportUrl}" target="_blank">查看分析报告</a></div>`;
  if (visualizationUrl) html += `<div>📈 <a href="${visualizationUrl}" target="_blank">查看可视化图表</a></div>`;
  if (validationUrl) html += `<div>✅ <a href="${validationUrl}" target="_blank">查看验证结果</a></div>`;
  linksEl.innerHTML = html;
}

function buildErrorMessage(data) {
  const errorType = data?.error_type ? `[${data.error_type}] ` : '';
  return `${errorType}${data?.error || 'unknown error'}`;
}

buttonEl.addEventListener('click', async () => {
  const targetTeam = targetTeamEl.value.trim();
  if (!targetTeam) {
    setStatus('请先填写目标队伍', 'error');
    return;
  }

  const aliases = [targetTeam];
  setStatus('正在读取当前页面...');

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    setStatus('未找到当前标签页', 'error');
    return;
  }

  chrome.tabs.sendMessage(tab.id, { type: 'collect-page-payload', targetTeam, aliases }, (contentResponse) => {
    if (chrome.runtime.lastError) {
      setStatus(`读取页面失败: ${chrome.runtime.lastError.message}`, 'error');
      return;
    }
    if (!contentResponse?.ok) {
      setStatus(`页面提取失败: ${contentResponse?.error || 'content script error'}`, 'error');
      return;
    }

    setStatus('正在分析中...');

    chrome.runtime.sendMessage(
      { type: 'bridge-import-and-run', payload: contentResponse.payload },
      (bridgeResponse) => {
        if (chrome.runtime.lastError) {
          setStatus(`发送失败: ${bridgeResponse.lastError?.message}`, 'error');
          return;
        }
        const data = bridgeResponse?.data || { error: 'unknown error' };
        if (!bridgeResponse?.ok || data.ok === false) {
          setStatus(`分析失败: ${buildErrorMessage(data)}`, 'error');
          return;
        }
        setStatus('✅ 分析完成', 'success');
        showLinks(data);
      },
    );
  });
});
