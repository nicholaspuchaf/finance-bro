import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { compile } from 'svelte/compiler';
import { render } from 'svelte/server';

// Render real components offline, using the same compiler as the application.
// Production SSR avoids opening a dev server or connecting to banks/services.
const output = mkdtempSync(resolve(tmpdir(), 'finance-bro-i18n-'));
const compiled = new Map();
const sourceRoot = fileURLToPath(new URL('../src/', import.meta.url));

function serverComponent(filename) {
  if (compiled.has(filename)) return compiled.get(filename);
  const target = pathToFileURL(resolve(output, `${basename(filename)}.mjs`)).href;
  compiled.set(filename, target);
  const { js } = compile(readFileSync(filename, 'utf8'), { filename, generate: 'server', dev: false });
  const code = js.code.replace(/import\s+(['"])[^'"]+\.css\1;?/g, '').replace(/^([ \t]*import\b[^;]*?\bfrom\s*)(['"])([^'"]+)\2/gm, (original, prefix, quote, specifier) => {
    let url;
    if (specifier.startsWith('.')) {
      const dependency = resolve(dirname(filename), specifier);
      url = specifier.endsWith('.svelte') ? serverComponent(dependency) : pathToFileURL(dependency).href;
    } else url = import.meta.resolve(specifier);
    return prefix + JSON.stringify(url);
  });
  writeFileSync(new URL(target), code);
  return target;
}

export async function renderComponent(name, props = {}) {
  const { default: component } = await import(serverComponent(resolve(sourceRoot, name)));
  return render(component, { props });
}
