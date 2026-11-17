<script lang="ts">
	import UtcDate from '#lib/components/UtcDate.svelte';
	import { platformUpdates } from '#lib/site/content.ts';
</script>

<svelte:head>
	<title>Platform updates | WATCHTOWER</title>
	<meta
		name="description"
		content="A factual release record for shipped WATCHTOWER capabilities."
	/>
</svelte:head>

<article class="updates-page">
	<header>
		<p>PRODUCT CHANGELOG / SHIPPED CAPABILITIES</p>
		<h1>Platform updates</h1>
		<span>What changed, when it changed and where to review the result.</span>
	</header>

	<ol>
		{#each platformUpdates as update, index (update.id)}
			<li id={update.id}>
				<div class="date">
					<span>{String(index + 1).padStart(2, '0')}</span><UtcDate value={update.publishedAt} />
				</div>
				<div class="release">
					<p>{update.label}</p>
					<h2>{update.title}</h2>
					<span>{update.summary}</span>
					<a href={update.href}>{update.linkLabel}<span aria-hidden="true"> →</span></a>
				</div>
			</li>
		{/each}
	</ol>
</article>

<style>
	.updates-page {
		max-width: 68rem;
		margin: 0 auto;
		padding: var(--space-8) var(--space-5);
	}

	header {
		max-width: 48rem;
		padding-bottom: var(--space-7);
	}

	header p,
	.release p,
	.date {
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}

	header p,
	.release p {
		margin: 0;
		color: var(--color-primary);
		font-weight: 700;
		text-transform: uppercase;
	}

	h1 {
		margin: var(--space-3) 0;
		font-size: var(--font-size-xl);
		line-height: var(--line-height-tight);
	}

	header > span,
	.release > span {
		color: var(--color-ink-muted);
	}

	ol {
		margin: 0;
		padding: 0;
		border-top: var(--border-width) solid var(--color-border-strong);
		list-style: none;
	}

	li {
		display: grid;
		grid-template-columns: minmax(10rem, 0.45fr) minmax(0, 1.55fr);
		gap: var(--space-7);
		padding: var(--space-6) 0;
		border-bottom: var(--border-width) solid var(--color-border);
	}

	.date {
		display: flex;
		align-items: flex-start;
		gap: var(--space-3);
		color: var(--color-ink-subtle);
	}

	.date > span {
		color: var(--color-secondary);
	}

	.release h2 {
		margin: var(--space-2) 0 var(--space-3);
		font-size: clamp(1.35rem, 3vw, 2rem);
	}

	.release a {
		display: inline-flex;
		min-height: 2.75rem;
		align-items: center;
		margin-top: var(--space-3);
		color: var(--color-primary);
		font-weight: 700;
		text-decoration: none;
	}

	@media (max-width: 42rem) {
		li {
			grid-template-columns: 1fr;
			gap: var(--space-3);
		}
	}
</style>
