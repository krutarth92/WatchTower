<script lang="ts">
	import { page } from '$app/state';
</script>

<svelte:head>
	<title>Unavailable | WATCHTOWER</title>
</svelte:head>

<section class="error-shell" aria-labelledby="error-title">
	<p class="eyebrow">REQUEST UNAVAILABLE</p>
	<h1 id="error-title">The research workspace could not load this view.</h1>
	<p>
		Status {page.status}. Return to the research workspace and try again. No private error detail is
		shown in the browser.
	</p>
	<a href="/search">Return to Research</a>
</section>

<style>
	.error-shell {
		max-width: var(--content-width);
		margin: 0 auto;
		padding: var(--space-8) var(--space-5);
	}

	.eyebrow {
		color: var(--color-critical);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}

	h1 {
		max-width: 18ch;
		margin: var(--space-3) 0;
		font-size: var(--font-size-xl);
		line-height: var(--line-height-tight);
	}

	p:not(.eyebrow) {
		max-width: 42rem;
		color: var(--color-ink-muted);
	}

	a {
		display: inline-block;
		margin-top: var(--space-5);
		padding: var(--space-3) var(--space-4);
		border: var(--border-width) solid var(--color-primary);
		border-radius: var(--radius-md);
		color: var(--color-primary);
		text-decoration: none;
	}
</style>
