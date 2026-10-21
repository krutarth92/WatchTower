import { readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const stylesDirectory = dirname(fileURLToPath(import.meta.url));
const sourceDirectory = join(stylesDirectory, '..', '..');
const tokenPath = join(stylesDirectory, 'tokens.css');
const colorLiteral = /#[0-9a-f]{3,8}\b|\b(?:rgb|hsl)a?\(/i;

function filesBelow(directory: string): string[] {
	return readdirSync(directory).flatMap((entry) => {
		const path = join(directory, entry);
		return statSync(path).isDirectory() ? filesBelow(path) : [path];
	});
}

describe('design token source', () => {
	it('defines every foundational token in the authoritative stylesheet', () => {
		const tokens = readFileSync(tokenPath, 'utf8');

		for (const name of [
			'--color-canvas',
			'--color-primary',
			'--font-sans',
			'--space-4',
			'--radius-md',
			'--shadow-panel',
			'--motion-standard'
		]) {
			expect(tokens).toContain(name);
		}
	});

	it('keeps color literals out of component and route styles', () => {
		const violations = filesBelow(sourceDirectory)
			.filter((path) => (path.endsWith('.css') || path.endsWith('.svelte')) && path !== tokenPath)
			.filter((path) => colorLiteral.test(readFileSync(path, 'utf8')))
			.map((path) => relative(sourceDirectory, path));

		expect(violations).toEqual([]);
	});
});
