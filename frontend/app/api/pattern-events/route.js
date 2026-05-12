import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

// Root of the Aviator project (one level above frontend/)
const DATA_DIR = path.join(process.cwd(), '..');

const FILES = [
  'post_bad_tracking.txt',
  'post_bad_tracking2.txt',
  'post_bad_tracking3.txt',
];

function computeCumulative(values, fileIdx) {
  let running = 0;
  const points = [{ index: 0, value: 0 }];
  values.forEach((v, i) => {
    let inc = 0.33;
    if (v === 1) {
      if (fileIdx === 0) inc = 0.2;
      else if (fileIdx === 1) inc = 0.33;
      else if (fileIdx === 2) inc = 0.5;
    } else {
      inc = -1;
    }
    running = parseFloat((running + inc).toFixed(4));
    points.push({ index: i + 1, value: running });
  });
  return points;
}

export async function GET() {
  const result = FILES.map((filename, fileIdx) => {
    const filePath = path.join(DATA_DIR, filename);
    let content = '';

    try {
      content = fs.readFileSync(filePath, 'utf-8');
    } catch {
      content = '{}';
    }

    let data = {};
    try {
      data = JSON.parse(content) || {};
    } catch {
      data = {};
    }

    const lists = {};
    let totalValues = 0;

    for (let i = 0; i < 6; i++) {
      const arr = data[String(i)] || [];
      totalValues += arr.length;
      const series = computeCumulative(arr, fileIdx);
      lists[i] = {
        rawValues: arr,
        series,
        eventCount: arr.length,
        lastValue: arr.length > 0 ? arr[arr.length - 1] : null,
        currentY: arr.length > 0 ? series.at(-1).value : 0,
      };
    }

    return {
      filename,
      fileIdx,
      lists,
      totalEvents: totalValues,
    };
  });

  return NextResponse.json({ data: result, updatedAt: Date.now() });
}
