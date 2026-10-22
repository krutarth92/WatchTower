<script lang="ts">
	let { eyebrow, title, description }: { eyebrow: string; title: string; description?: string } =
		$props();
</script>

<header>
	<p class="eyebrow"><span aria-hidden="true"></span>{eyebrow}</p>
	<h1>{title}</h1>
	{#if description}<p class="description">{description}</p>{/if}
</header>

<style>
	header {
		max-width: 52rem;
	}

	.eyebrow {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		margin: 0;
		color: var(--color-primary);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		font-weight: 700;
		letter-spacing: var(--letter-spacing-label);
	}

	.eyebrow span {
		width: var(--space-5);
		height: var(--border-width);
		background: var(--gradient-brand);
	}

	h1 {
		margin: var(--space-3) 0;
		font-size: clamp(2rem, 5vw, 4rem);
		line-height: var(--line-height-tight);
		letter-spacing: -0.04em;
	}

	.description {
		margin: 0;
		color: var(--color-ink-muted);
		font-size: var(--font-size-lg);
	}
</style>
