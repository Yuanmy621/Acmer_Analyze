function buildFallbackPayload(targetTeam, aliases) {
  const title = document.title || 'Unknown Page';
  const currentUrl = window.location.href;
  return {
    source: 'browser_bridge',
    site: 'codeforces',
    target_team: targetTeam,
    aliases,
    raw_payload: {
      contests: [
        {
          contest_id: 'cf_demo_page',
          source: 'codeforces',
          title,
          start_time: new Date().toISOString(),
          duration_seconds: 0,
          type: 'page_capture',
          url: currentUrl,
        },
      ],
      problems: [],
      standings: [],
    },
    metadata: {
      page_url: currentUrl,
      captured_at: new Date().toISOString(),
      collector: 'codeforces-fallback',
    },
  };
}

function parseContestIdFromUrl() {
  const match = window.location.pathname.match(/\/(contest|gym)\/(\d+)\/standings/);
  return match ? Number(match[2]) : null;
}

function isCodeforcesStandingsPage() {
  return /\/standings/.test(window.location.pathname) && /codeforces\.com$/.test(window.location.hostname);
}

function buildContestId(contestId) {
  return `cf_${contestId}`;
}

function buildProblemId(contestId, label) {
  return `cf_${contestId}_${label}`;
}

function toIso8601FromSeconds(seconds) {
  if (typeof seconds !== 'number') {
    return new Date().toISOString();
  }
  return new Date(seconds * 1000).toISOString();
}

function deriveTeamRawName(party) {
  if (party?.teamName) {
    return String(party.teamName);
  }
  const handles = (party?.members || []).map((member) => member?.handle).filter(Boolean);
  if (handles.length) {
    return handles.join(' ');
  }
  if (party?.participantId != null) {
    return `party_${party.participantId}`;
  }
  return 'unknown_party';
}

function buildContestPayload(contestId, contest) {
  return {
    contest_id: buildContestId(contestId),
    source: 'codeforces',
    title: contest?.name || `Codeforces Contest ${contestId}`,
    start_time: toIso8601FromSeconds(contest?.startTimeSeconds),
    duration_seconds: Number(contest?.durationSeconds || 0),
    type: contest?.type || 'standings_page',
    url: window.location.href,
  };
}

function buildProblemPayload(contestId, problems) {
  return problems.map((problem) => ({
    problem_id: buildProblemId(contestId, problem.index),
    contest_id: buildContestId(contestId),
    label: problem.index,
    title: problem.name || `Problem ${problem.index}`,
    tags: Array.isArray(problem.tags) ? problem.tags : [],
    difficulty: problem.rating ?? null,
  }));
}

function buildProblemResults(contestId, problems, results) {
  let solvedCount = 0;
  const payload = problems.map((problem, index) => {
    const result = results[index] || {};
    const points = Number(result.points || 0);
    const accepted = points > 0;
    if (accepted) {
      solvedCount += 1;
    }
    const bestSubmissionTimeSeconds = result.bestSubmissionTimeSeconds;
    return {
      problem_id: buildProblemId(contestId, problem.index),
      accepted,
      attempts: Number(result.rejectedAttemptCount || 0) + (accepted ? 1 : 0),
      first_ac_time: typeof bestSubmissionTimeSeconds === 'number'
        ? Math.floor(bestSubmissionTimeSeconds / 60)
        : null,
    };
  });
  return { payload, solvedCount };
}

function buildStandingsPayload(contestId, problems, rows) {
  return rows.map((row) => {
    const { payload, solvedCount } = buildProblemResults(contestId, problems, row.problemResults || []);
    return {
      contest_id: buildContestId(contestId),
      team_raw_name: deriveTeamRawName(row.party || {}),
      rank: Number(row.rank || 0),
      solved_count: solvedCount,
      penalty: Number(row.penalty || 0),
      problem_results: payload,
    };
  });
}

async function buildPayloadFromApi(targetTeam, aliases) {
  const contestId = parseContestIdFromUrl();
  if (!contestId) {
    throw new Error('当前页面不是可识别的 Codeforces standings 页面');
  }

  const response = await fetch(`https://codeforces.com/api/contest.standings?contestId=${contestId}`, {
    method: 'GET',
    credentials: 'omit',
  });
  if (!response.ok) {
    throw new Error(`Codeforces standings API 请求失败: HTTP ${response.status}`);
  }

  const payload = await response.json();
  if (payload.status !== 'OK') {
    throw new Error(`Codeforces standings API 返回失败: ${payload.comment || 'unknown error'}`);
  }

  const result = payload.result || {};
  const contest = result.contest || {};
  const problems = Array.isArray(result.problems) ? result.problems : [];
  const rows = Array.isArray(result.rows) ? result.rows : [];

  return {
    source: 'browser_bridge',
    site: 'codeforces',
    target_team: targetTeam,
    aliases,
    raw_payload: {
      contests: [buildContestPayload(contestId, contest)],
      problems: buildProblemPayload(contestId, problems),
      standings: buildStandingsPayload(contestId, problems, rows),
    },
    metadata: {
      page_url: window.location.href,
      captured_at: new Date().toISOString(),
      collector: 'codeforces-standings-api',
    },
  };
}

function parseProblemCells(contestId) {
  const headerCells = Array.from(document.querySelectorAll('table.standings thead tr th'));
  const problems = [];
  for (const cell of headerCells) {
    const link = cell.querySelector('a');
    if (!link) {
      continue;
    }
    const labelText = (link.textContent || '').replace(/\s+/g, ' ').trim();
    if (!labelText || !/^[A-Z0-9]+$/.test(labelText)) {
      continue;
    }
    problems.push({
      problem_id: buildProblemId(contestId, labelText),
      contest_id: buildContestId(contestId),
      label: labelText,
      title: link.getAttribute('title') || `Problem ${labelText}`,
      tags: [],
      difficulty: null,
    });
  }
  return problems;
}

function parseStandingRows(contestId, problems) {
  const bodyRows = Array.from(document.querySelectorAll('table.standings tbody tr'));
  const standings = [];
  for (const row of bodyRows) {
    const rankCell = row.querySelector('td.standingsRank');
    const participantCell = row.querySelector('td.left');
    if (!rankCell || !participantCell) {
      continue;
    }

    const teamRawName = participantCell.textContent.replace(/\s+/g, ' ').trim();
    const rank = Number(rankCell.textContent.trim());
    if (!teamRawName || Number.isNaN(rank)) {
      continue;
    }

    const cells = Array.from(row.querySelectorAll('td'));
    const problemCells = cells.slice(-problems.length);
    const problemResults = problems.map((problem, index) => {
      const text = problemCells[index]?.textContent?.replace(/\s+/g, ' ').trim() || '';
      const accepted = /\+/.test(text);
      const attemptsMatch = text.match(/([+-]?\d+)/);
      const attempts = attemptsMatch ? Math.abs(Number(attemptsMatch[1])) : accepted ? 1 : 0;
      const timeMatch = text.match(/(\d{1,3})/g);
      const firstAcTime = accepted && timeMatch?.length ? Number(timeMatch[timeMatch.length - 1]) : null;
      return {
        problem_id: problem.problem_id,
        accepted,
        attempts,
        first_ac_time: Number.isNaN(firstAcTime) ? null : firstAcTime,
      };
    });

    standings.push({
      contest_id: buildContestId(contestId),
      team_raw_name: teamRawName,
      rank,
      solved_count: problemResults.filter((item) => item.accepted).length,
      penalty: 0,
      problem_results: problemResults,
    });
  }
  return standings;
}

function buildPayloadFromDom(targetTeam, aliases) {
  const contestId = parseContestIdFromUrl();
  if (!contestId) {
    return buildFallbackPayload(targetTeam, aliases);
  }

  const problems = parseProblemCells(contestId);
  const standings = parseStandingRows(contestId, problems);
  return {
    source: 'browser_bridge',
    site: 'codeforces',
    target_team: targetTeam,
    aliases,
    raw_payload: {
      contests: [
        {
          contest_id: buildContestId(contestId),
          source: 'codeforces',
          title: document.title || `Codeforces Contest ${contestId}`,
          start_time: new Date().toISOString(),
          duration_seconds: 0,
          type: 'standings_page_dom',
          url: window.location.href,
        },
      ],
      problems,
      standings,
    },
    metadata: {
      page_url: window.location.href,
      captured_at: new Date().toISOString(),
      collector: 'codeforces-standings-dom',
    },
  };
}

async function collectPagePayload(targetTeam, aliases) {
  if (!isCodeforcesStandingsPage()) {
    return buildFallbackPayload(targetTeam, aliases);
  }

  try {
    return await buildPayloadFromApi(targetTeam, aliases);
  } catch (error) {
    console.warn('Falling back to DOM extraction:', error);
    return buildPayloadFromDom(targetTeam, aliases);
  }
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== 'collect-page-payload') {
    return false;
  }
  const targetTeam = message.targetTeam || 'tourist';
  const aliases = Array.isArray(message.aliases) && message.aliases.length ? message.aliases : [targetTeam];

  collectPagePayload(targetTeam, aliases)
    .then((payload) => sendResponse({ ok: true, payload }))
    .catch((error) => sendResponse({ ok: false, error: String(error) }));

  return true;
});
