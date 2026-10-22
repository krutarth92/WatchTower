<script lang="ts">
	let { value }: { value: string } = $props();
	const date = $derived(new Date(value));
	const valid = $derived(!Number.isNaN(date.valueOf()));
	const iso = $derived(valid ? date.toISOString() : value);
	const display = $derived(
		valid
			? new Intl.DateTimeFormat(undefined, {
					dateStyle: 'medium',
					timeStyle: 'short',
					timeZone: 'UTC'
				}).format(date)
			: 'Invalid date'
	);
</script>

<time datetime={iso} title={valid ? `${iso} (UTC)` : value}>{display} <span>UTC</span></time>

<style>
	time {
		font-variant-numeric: tabular-nums;
	}

	span {
		color: var(--color-ink-subtle);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
	}
</style>
