<script lang="ts">
	type Segment = { value: string; matched: boolean };

	let { text, query }: { text: string; query: string } = $props();

	const segments = $derived.by((): Segment[] => {
		const needle = query.trim();
		if (!needle) return [{ value: text, matched: false }];
		const lowerText = text.toLocaleLowerCase();
		const lowerNeedle = needle.toLocaleLowerCase();
		const output: Segment[] = [];
		let cursor = 0;
		while (cursor < text.length) {
			const index = lowerText.indexOf(lowerNeedle, cursor);
			if (index < 0) {
				output.push({ value: text.slice(cursor), matched: false });
				break;
			}
			if (index > cursor) output.push({ value: text.slice(cursor, index), matched: false });
			output.push({ value: text.slice(index, index + needle.length), matched: true });
			cursor = index + needle.length;
		}
		return output.length ? output : [{ value: text, matched: false }];
	});
</script>

{#each segments as segment, index (`${index}-${segment.value}`)}
	{#if segment.matched}<mark>{segment.value}</mark>{:else}{segment.value}{/if}
{/each}

<style>
	mark {
		padding: 0 var(--space-1);
		border-bottom: 0.125rem solid var(--color-highlight);
		background: var(--color-secondary-faint);
		color: inherit;
	}
</style>
