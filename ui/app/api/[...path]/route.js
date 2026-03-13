import { NextResponse } from 'next/server';

const getBackendUrl = () => process.env.BACKEND_API_URL || 'http://localhost:8000';

export async function GET(request, { params }) {
  const path = params.path ? params.path.join('/') : '';
  const url = new URL(request.url);
  
  try {
    const res = await fetch(`${getBackendUrl()}/${path}${url.search}`, {
      method: 'GET',
      headers: {
        'Content-Type': request.headers.get('content-type') || 'application/json',
      },
    });
    
    const data = await res.text();
    return new NextResponse(data, {
      status: res.status,
      headers: { 'Content-Type': res.headers.get('content-type') || 'application/json' }
    });
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function POST(request, { params }) {
  const path = params.path ? params.path.join('/') : '';
  const url = new URL(request.url);
  
  try {
    const body = await request.text();
    const res = await fetch(`${getBackendUrl()}/${path}${url.search}`, {
      method: 'POST',
      headers: {
        'Content-Type': request.headers.get('content-type') || 'application/json',
      },
      body: body || null,
    });
    
    const data = await res.text();
    return new NextResponse(data, {
      status: res.status,
      headers: { 'Content-Type': res.headers.get('content-type') || 'application/json' }
    });
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export const dynamic = 'force-dynamic';
