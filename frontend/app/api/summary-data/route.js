export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const res = await fetch('http://127.0.0.1:5000/summary-data', {
      cache: 'no-store',
    });
    const data = await res.json();
    return Response.json(data);
  } catch (err) {
    return Response.json({ status: 'error', message: err.message }, { status: 500 });
  }
}
