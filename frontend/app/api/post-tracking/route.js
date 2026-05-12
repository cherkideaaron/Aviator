import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const DATA_DIR = path.join(process.cwd(), '..');

const FILES = [
  'post_bad_tracking.txt',
  'post_bad_tracking2.txt',
  'post_bad_tracking3.txt',
];

const LIST_COLORS = [
  '#5b8dee', '#a78bfa', '#00d4ff', '#00e5a0', '#ff9a3c', '#ff4d6d',
];

function score(v, fileIdx) {
  if (v !== 1) return -1;
  // File indices correspond to 1.21, 1.34, 1.51 thresholds
  if (fileIdx === 0) return 0.2;
  if (fileIdx === 1) return 0.33;
  if (fileIdx === 2) return 0.5;
  return 0.33; // Fallback
}

function computeCumulative(values, fileIdx) {
  let running = 0;
  const points = [{ index: 0, value: 0 }];
  values.forEach((v, i) => {
    running = parseFloat((running + score(v, fileIdx)).toFixed(4));
    points.push({ index: i + 1, value: running });
  });
  return points;
}

// Build a combined series from all 6 lists interleaved sequentially
// (list0[0], list1[0], ..., list5[0], list0[1], ...) — round-robin
function buildCombinedInterleaved(data) {
  const maxLen = Math.max(...Object.values(data).map((arr) => arr.length), 0);
  const combined = [];
  for (let pos = 0; pos < maxLen; pos++) {
    for (let li = 0; li < 6; li++) {
      const arr = data[String(li)] || [];
      if (pos < arr.length) combined.push(arr[pos]);
    }
  }
  return combined;
}

export async function GET() {
  const result = FILES.map((filename, fileIdx) => {
    const filePath = path.join(DATA_DIR, filename);
    let content = '';

    try {
      content = fs.readFileSync(filePath, 'utf-8');
    } catch {
      content = '';
    }

    let data = {};
    try {
      data = JSON.parse(content) || {};
    } catch {
      data = {};
    }

    // Individual list series
    const lists = {};
    let totalOnes = 0;
    let totalZeros = 0;

    for (let i = 0; i < 6; i++) {
      const arr = data[String(i)] || [];
      totalOnes += arr.filter((v) => v === 1).length;
      totalZeros += arr.filter((v) => v === 0).length;
      const series = computeCumulative(arr, fileIdx);
      lists[i] = {
        series,
        length: arr.length,
        currentY: series.at(-1)?.value ?? 0,
        color: LIST_COLORS[i],
      };
    }

    // Combined series for the main graph
    // If the JSON has a 'combined' key, use it (1 result per round).
    // Otherwise fallback to interleaving (legacy).
    const combined = data.combined || buildCombinedInterleaved(data);
    const combinedSeries = computeCumulative(combined, fileIdx);

    return {
      filename,
      fileIdx,
      lists,
      combinedSeries,
      stats: {
        total: totalOnes + totalZeros,
        ones: totalOnes,
        zeros: totalZeros,
        currentY: combinedSeries.at(-1)?.value ?? 0,
      },
    };
  });

  return NextResponse.json({ data: result, updatedAt: Date.now() });
}
