import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const key =
  process.env['JOBHUNTER_TLS_KEY'] || path.resolve(root, '../../local-data/tls/localhost.key');
const cert =
  process.env['JOBHUNTER_TLS_CERT'] || path.resolve(root, '../../local-data/tls/localhost.crt');
if (!existsSync(key) || !existsSync(cert)) {
  console.error(
    'Create local TLS first: from backend run .venv/Scripts/python.exe -m app.setup tls',
  );
  process.exit(1);
}
const cli = path.join(root, 'node_modules/@angular/cli/bin/ng.js');
const child = spawn(
  process.execPath,
  [
    cli,
    'serve',
    '--host',
    'localhost',
    '--port',
    process.env['JOBHUNTER_FRONTEND_PORT'] || '4200',
    '--ssl',
    '--ssl-key',
    key,
    '--ssl-cert',
    cert,
    '--proxy-config',
    'proxy.conf.cjs',
  ],
  { cwd: root, stdio: 'inherit', windowsHide: true },
);
child.on('exit', (code) => process.exit(code ?? 1));
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
