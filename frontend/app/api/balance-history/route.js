import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const res = await fetch('http://127.0.0.1:5000/balance-history-data', {
      cache: 'no-store',
    });
    
    if (!res.ok) {
      throw new Error(`Failed to fetch from backend: ${res.status}`);
    }
    
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Balance history API error:', error);
    return NextResponse.json({ status: 'error', message: error.message }, { status: 500 });
  }
}
