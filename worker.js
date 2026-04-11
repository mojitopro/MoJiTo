// Cloudflare Worker - Free CORS Proxy
// Deploy at: https://workers.cloudflare.com

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const target = url.searchParams.get('url');
    
    if (!target) {
      return new Response('Missing url parameter', { status: 400 });
    }
    
    const headers = new Headers();
    headers.set('Access-Control-Allow-Origin', '*');
    headers.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    headers.set('Access-Control-Allow-Headers', 'Content-Type');
    
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers });
    }
    
    try {
      const response = await fetch(target, {
        method: request.method,
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
          'Accept': 'application/json',
        }
      });
      
      const body = await response.text();
      
      return new Response(body, {
        status: response.status,
        headers: headers
      });
    } catch (e) {
      return new Response(e.message, { status: 500, headers });
    }
  }
};