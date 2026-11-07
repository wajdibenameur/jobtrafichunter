// Local HTTPS preview of the production build, with a loopback-only API proxy.
import https from 'node:https';
import { readFileSync, existsSync, createReadStream, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const directory = path.join(root, 'dist/jobhunter/browser');
const key =
  process.env['JOBHUNTER_TLS_KEY'] || path.resolve(root, '../../local-data/tls/localhost.key');
const cert =
  process.env['JOBHUNTER_TLS_CERT'] || path.resolve(root, '../../local-data/tls/localhost.crt');
const target = new URL(process.env['JOBHUNTER_API_TARGET'] || 'https://localhost:8443');
if (
  target.protocol !== 'https:' ||
  !['localhost', '127.0.0.1', '[::1]'].includes(target.hostname)
) {
  throw new Error('API target must be HTTPS loopback.');
}
if (!existsSync(path.join(directory, 'index.html')))
  throw new Error('Build the frontend first: npm run build');
const types = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ttf': 'font/ttf',
  '.woff2': 'font/woff2',
  '.json': 'application/json',
};
const server = https.createServer(
  { key: readFileSync(key), cert: readFileSync(cert) },
  (request, response) => {
    const url = new URL(request.url || '/', 'https://localhost');
    if (url.pathname.startsWith('/api/') || url.pathname === '/health') {
      const proxied = https.request(
        new URL(request.url || '/', target),
        {
          method: request.method,
          headers: { ...request.headers, host: target.host },
          rejectUnauthorized: false,
        },
        (upstream) => {
          response.writeHead(upstream.statusCode || 502, upstream.headers);
          upstream.pipe(response);
        },
      );
      proxied.on('error', () => {
        if (!response.headersSent) response.writeHead(502, { 'Content-Type': 'application/json' });
        response.end('{"error":{"code":"API_UNAVAILABLE"}}');
      });
      request.on('aborted', () => proxied.destroy());
      request.pipe(proxied);
      return;
    }
    if (!['GET', 'HEAD'].includes(request.method || '')) {
      response.writeHead(405);
      response.end();
      return;
    }
    let file;
    try {
      file = path.resolve(directory, '.' + decodeURIComponent(url.pathname));
    } catch {
      response.writeHead(400);
      response.end();
      return;
    }
    if (file !== directory && !file.startsWith(directory + path.sep)) {
      response.writeHead(403);
      response.end();
      return;
    }
    if (!existsSync(file) || !statSync(file).isFile()) {
      if (path.extname(url.pathname)) {
        response.writeHead(404);
        response.end();
        return;
      }
      file = path.join(directory, 'index.html');
    }
    response.writeHead(200, {
      'Content-Type': types[path.extname(file)] || 'application/octet-stream',
      'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'Strict-Transport-Security': 'max-age=31536000',
      'Referrer-Policy': 'no-referrer',
      'Content-Security-Policy':
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    });
    if (request.method === 'HEAD') response.end();
    else createReadStream(file).pipe(response);
  },
);
const port = Number(process.env['JOBHUNTER_FRONTEND_PORT'] || 4200);
server.listen(port, 'localhost', () => console.log(`Local: https://localhost:${port}`));
for (const signal of ['SIGINT', 'SIGTERM'])
  process.on(signal, () => server.close(() => process.exit(0)));
