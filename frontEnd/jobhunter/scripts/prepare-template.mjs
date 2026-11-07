import { copyFile, mkdir, access } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const source = path.resolve(root, '../velson_template/src/assets');
const destination = path.join(root, 'public/assets/template');
// Only the supplied illustration is needed; Poppins is shipped under its OFL license.
// We retain the supplied layout/tokens, without shipping demo scripts or vendor bundles.
const files = ['images/signin.png'];
const optional =
  process.argv.includes('--optional') || process.env['JOBHUNTER_TEMPLATE_OPTIONAL'] === '1';
try {
  await access(source);
} catch {
  if (optional) {
    console.log(
      'Local reference unavailable: using the built-in font and CSS illustration fallback.',
    );
    process.exit(0);
  }
  throw new Error(
    'Velson reference missing. Restore the private reference folder or use --optional.',
  );
}
for (const file of files) {
  await mkdir(path.dirname(path.join(destination, file)), { recursive: true });
  await copyFile(path.join(source, file), path.join(destination, file));
}
console.log('Prepared the local reference illustration; original template untouched.');
