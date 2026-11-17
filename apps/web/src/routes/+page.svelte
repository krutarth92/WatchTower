<script lang="ts">
	import type { PageProps } from './$types';
	import PlatformUpdateRail from '#lib/components/PlatformUpdateRail.svelte';
	import UtcDate from '#lib/components/UtcDate.svelte';
	import { latestPlatformUpdate, primaryNavigation } from '#lib/site/content.ts';

	let { data }: PageProps = $props();

	const actors = $derived(data.discovery?.recent.slice(0, 4) ?? []);
</script>

<svelte:head>
	<title>WATCHTOWER | Adversary intelligence</title>
	<meta
		name="description"
		content="Track adversaries, understand behavioral change and follow published evidence."
	/>
</svelte:head>

<div class="home-shell">
	<section class="hero" aria-labelledby="home-title">
		<div class="hero-copy">
			<p class="eyebrow">PUBLISHED ADVERSARY INTELLIGENCE</p>
			<h1 id="home-title">Track the adversary.<br /><span>Understand the change.</span></h1>
			<p class="lede">
				Follow actors, behaviors, vulnerabilities and evidence through a research surface built for
				traceable context.
			</p>
			<form action="/search" method="GET" role="search">
				<label for="home-search">Search the intelligence index</label>
				<div class="search-line">
					<span aria-hidden="true">WT://</span>
					<input
						id="home-search"
						type="search"
						name="q"
						minlength="2"
						maxlength="200"
						placeholder="indicator, CVE, actor, alias or technique"
					/>
					<button type="submit">Search <span aria-hidden="true">→</span></button>
				</div>
			</form>
		</div>

		<ol class="signal-map" aria-label="WATCHTOWER research path">
			<li><span>01</span><strong>Adversary</strong><small>Identity and aliases</small></li>
			<li><span>02</span><strong>Behavior</strong><small>Techniques and activity</small></li>
			<li><span>03</span><strong>Evolution</strong><small>Change over time</small></li>
			<li><span>04</span><strong>Evidence</strong><small>Source and confidence</small></li>
		</ol>
	</section>

	<PlatformUpdateRail update={latestPlatformUpdate} />

	<section class="feed-grid" aria-label="Latest published intelligence">
		<div class="advisory-feed">
			<header class="section-heading">
				<div>
					<p>INTELLIGENCE / LIVING ARTICLES</p>
					<h2>Latest intelligence</h2>
				</div>
				<a href="/advisories">View all <span aria-hidden="true">→</span></a>
			</header>

			{#if data.advisories?.data.length}
				<ol>
					{#each data.advisories.data as advisory, index (advisory.id)}
						<li>
							<span class="feed-index">{String(index + 1).padStart(2, '0')}</span>
							<div>
								<a class="feed-title" href={`/advisories/${advisory.slug}`}>{advisory.title}</a>
								<p>{advisory.summary}</p>
								<small>
									Published <UtcDate value={advisory.published_at} /> · revision {advisory.published_revision}
									{#if advisory.latest_update_at}
										· updated <UtcDate value={advisory.latest_update_at} />
									{/if}
								</small>
							</div>
						</li>
					{/each}
				</ol>
			{:else}
				<p class="empty-feed">
					{data.errors.advisories ?? 'No living intelligence advisories have been published yet.'}
				</p>
			{/if}
		</div>

		<aside class="actor-feed" aria-labelledby="active-actors-title">
			<div class="section-heading">
				<div>
					<p>ACTOR INDEX / RECENT</p>
					<h2 id="active-actors-title">Actors in motion</h2>
				</div>
				<a href="/actors">Directory <span aria-hidden="true">→</span></a>
			</div>
			{#if actors.length}
				<ul>
					{#each actors as actor (actor.id)}
						<li>
							<a href={`/actors/${actor.id}?fromSearch=%2F`}>{actor.canonical_name}</a>
							<p>{actor.description ?? 'Published actor profile with linked context.'}</p>
							<small>{actor.published_observation_count} published observations</small>
						</li>
					{/each}
				</ul>
			{:else}
				<p class="empty-feed">
					{data.errors.discovery ?? 'Actor discovery will populate from published observations.'}
				</p>
			{/if}
		</aside>
	</section>

	<section class="module-index" aria-labelledby="explore-title">
		<header>
			<p>PUBLIC WEBSITE NAVIGATION</p>
			<h2 id="explore-title">Explore WATCHTOWER</h2>
		</header>
		<div>
			{#each primaryNavigation as destination, index (destination.href)}
				<a href={destination.href}>
					<span>{String(index + 1).padStart(2, '0')}</span>
					<strong>{destination.label}</strong>
					<small>{destination.description}</small>
					<i aria-hidden="true">→</i>
				</a>
			{/each}
		</div>
	</section>
</div>

<style>
	.home-shell {
		max-width: var(--content-width);
		margin: 0 auto;
		padding: 0 var(--space-5);
	}

	.hero {
		display: grid;
		min-height: min(42rem, calc(100vh - var(--header-height)));
		grid-template-columns: minmax(0, 1.5fr) minmax(18rem, 0.7fr);
		gap: var(--space-8);
		align-items: center;
		padding: var(--space-8) 0 var(--space-7);
		background-image: var(--gradient-ambient), var(--texture-grid);
		background-size:
			auto,
			var(--grid-size) var(--grid-size);
	}

	.eyebrow,
	.section-heading p,
	.module-index header p,
	.feed-index,
	small,
	.signal-map span {
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}

	.eyebrow,
	.section-heading p,
	.module-index header p {
		margin: 0;
		color: var(--color-primary);
		font-weight: 700;
	}

	h1 {
		max-width: 13ch;
		margin: var(--space-3) 0 var(--space-5);
		font-size: clamp(2.6rem, 7vw, 5.8rem);
		letter-spacing: -0.055em;
		line-height: 0.96;
	}

	h1 span {
		background: var(--gradient-brand);
		background-clip: text;
		color: transparent;
	}

	.lede {
		max-width: 42rem;
		margin: 0 0 var(--space-6);
		color: var(--color-ink-muted);
		font-size: var(--font-size-lg);
	}

	form label {
		display: block;
		margin-bottom: var(--space-2);
		font-size: var(--font-size-sm);
		font-weight: 700;
	}

	.search-line {
		display: grid;
		max-width: 46rem;
		grid-template-columns: auto minmax(0, 1fr) auto;
		align-items: center;
		border-bottom: var(--border-width) solid var(--color-border-strong);
		background: var(--color-surface-glass);
	}

	.search-line > span {
		padding-left: var(--space-4);
		color: var(--color-primary);
		font-family: var(--font-mono);
		font-size: var(--font-size-sm);
	}

	input {
		min-width: 0;
		min-height: 3.5rem;
		border: 0;
		outline: 0;
		background: transparent;
		color: var(--color-ink);
	}

	button {
		min-height: 3.5rem;
		padding: 0 var(--space-5);
		border: 0;
		background: var(--color-primary);
		color: var(--color-canvas);
		font-weight: 800;
		cursor: pointer;
	}

	.signal-map {
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.signal-map li {
		display: grid;
		grid-template-columns: 2.5rem minmax(0, 1fr);
		gap: 0 var(--space-3);
		padding: var(--space-4) 0;
		border-bottom: var(--border-width) solid var(--color-border);
	}

	.signal-map li:first-child {
		border-top: var(--border-width) solid var(--color-border);
	}

	.signal-map span {
		grid-row: 1 / 3;
		color: var(--color-primary);
	}

	.signal-map strong {
		font-size: var(--font-size-lg);
	}

	.signal-map small,
	small {
		color: var(--color-ink-subtle);
	}

	.feed-grid {
		display: grid;
		grid-template-columns: minmax(0, 1.65fr) minmax(18rem, 0.85fr);
		gap: var(--space-8);
		padding: var(--space-8) 0;
	}

	.section-heading {
		display: flex;
		align-items: end;
		justify-content: space-between;
		gap: var(--space-4);
		padding-bottom: var(--space-4);
		border-bottom: var(--border-width) solid var(--color-border-strong);
	}

	.section-heading h2,
	.module-index h2 {
		margin: var(--space-1) 0 0;
		font-size: clamp(1.7rem, 4vw, 2.7rem);
	}

	.section-heading a,
	.module-index a,
	.actor-feed a,
	.feed-title {
		color: var(--color-primary);
		text-decoration: none;
	}

	.advisory-feed ol,
	.actor-feed ul {
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.advisory-feed li {
		display: grid;
		grid-template-columns: 2.25rem minmax(0, 1fr);
		gap: var(--space-4);
		padding: var(--space-5) 0;
		border-bottom: var(--border-width) solid var(--color-border);
	}

	.feed-index {
		color: var(--color-secondary);
	}

	.feed-title {
		color: var(--color-ink);
		font-size: clamp(1.1rem, 2.4vw, 1.45rem);
		font-weight: 750;
	}

	.advisory-feed li p,
	.actor-feed li p {
		margin: var(--space-2) 0;
		color: var(--color-ink-muted);
	}

	.actor-feed li {
		padding: var(--space-4) 0;
		border-bottom: var(--border-width) solid var(--color-border);
	}

	.actor-feed li > a {
		color: var(--color-ink);
		font-size: var(--font-size-lg);
		font-weight: 750;
	}

	.empty-feed {
		padding: var(--space-6) 0;
		color: var(--color-ink-muted);
	}

	.module-index {
		display: grid;
		grid-template-columns: minmax(14rem, 0.6fr) minmax(0, 1.4fr);
		gap: var(--space-8);
		padding: var(--space-7) 0;
		border-top: var(--border-width) solid var(--color-border-strong);
	}

	.module-index > div {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0 var(--space-7);
	}

	.module-index a {
		position: relative;
		display: grid;
		grid-template-columns: 2rem minmax(0, 1fr) auto;
		gap: 0 var(--space-3);
		padding: var(--space-4) 0;
		border-bottom: var(--border-width) solid var(--color-border);
		color: var(--color-ink);
	}

	.module-index a span {
		grid-row: 1 / 3;
		color: var(--color-ink-subtle);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
	}

	.module-index a strong {
		font-size: var(--font-size-lg);
	}

	.module-index a small {
		grid-column: 2;
	}

	.module-index a i {
		grid-column: 3;
		grid-row: 1 / 3;
		align-self: center;
		color: var(--color-primary);
		font-style: normal;
	}

	.module-index a:hover strong {
		color: var(--color-primary);
	}

	@media (max-width: 58rem) {
		.hero,
		.feed-grid,
		.module-index {
			grid-template-columns: 1fr;
			gap: var(--space-6);
		}

		.hero {
			min-height: auto;
		}
	}

	@media (max-width: 40rem) {
		.home-shell {
			padding-inline: var(--space-4);
		}

		.hero {
			padding-top: var(--space-7);
		}

		.search-line {
			grid-template-columns: auto minmax(0, 1fr);
		}

		button {
			grid-column: 1 / -1;
		}

		.module-index > div {
			grid-template-columns: 1fr;
		}
	}
</style>
