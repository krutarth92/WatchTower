<svelte:head>
	<title>Research | WATCHTOWER</title>
</svelte:head>

<section class="workspace-intro" aria-labelledby="research-title">
	<div class="intro-inner">
		<div class="hero-grid">
			<div class="hero-copy">
				<p class="eyebrow"><span aria-hidden="true"></span> INTELLIGENCE RESEARCH</p>
				<h1 id="research-title">Track adversaries. <span>Follow the evidence.</span></h1>
				<p class="lede">
					WATCHTOWER brings published intelligence, actor evolution, and source context into one
					private research workspace.
				</p>

				<dl class="principles" aria-label="Research workspace principles">
					<div>
						<dt>BOUNDARY</dt>
						<dd>Private by default</dd>
					</div>
					<div>
						<dt>MODEL</dt>
						<dd>Evidence linked</dd>
					</div>
					<div>
						<dt>WORKFLOW</dt>
						<dd>Review gated</dd>
					</div>
				</dl>
			</div>

			<aside class="signal-panel" aria-labelledby="surface-title">
				<div class="panel-bar">
					<div>
						<span class="panel-kicker">RESEARCH SURFACE</span>
						<h2 id="surface-title">Foundation telemetry</h2>
					</div>
					<span class="system-state"><span aria-hidden="true"></span> SYSTEM READY</span>
				</div>

				<div class="orbital-map" aria-hidden="true">
					<span class="axis axis-horizontal"></span>
					<span class="axis axis-vertical"></span>
					<span class="orbit orbit-outer"></span>
					<span class="orbit orbit-middle"></span>
					<span class="orbit orbit-inner"></span>
					<span class="sweep"></span>
					<span class="core"><span></span></span>
					<span class="node node-one"></span>
					<span class="node node-two"></span>
					<span class="node node-three"></span>
					<span class="map-label label-one">SOURCE</span>
					<span class="map-label label-two">ACTOR</span>
					<span class="map-label label-three">EVIDENCE</span>
				</div>

				<dl class="readout">
					<div>
						<dt>SURFACE</dt>
						<dd>Research</dd>
					</div>
					<div>
						<dt>BOUNDARY</dt>
						<dd>Server side</dd>
					</div>
					<div>
						<dt>INTEGRITY</dt>
						<dd>Checks enforced</dd>
					</div>
				</dl>
			</aside>
		</div>

		<div class="foundation-panel">
			<div class="foundation-copy">
				<p class="panel-label">WORKSPACE STATUS / 01</p>
				<h2>Built for evidence-first research</h2>
				<p>
					The operating surface is online. Search and evidence modules will arrive as reviewed
					capabilities, without weakening the private boundary.
				</p>
			</div>

			<ul class="foundation-grid" aria-label="Foundation capabilities">
				<li><span>INTERFACE</span><strong>Responsive shell</strong></li>
				<li><span>API BOUNDARY</span><strong>Server side</strong></li>
				<li><span>INTELLIGENCE</span><strong>Source linked</strong></li>
			</ul>

			<div class="integrity-note">
				<span class="status-chip"><span aria-hidden="true"></span> READY</span>
				<p>
					<strong>OBSERVED</strong> facts remain distinct from <strong>ASSESSED</strong> analysis.
				</p>
			</div>
		</div>
	</div>
</section>

<style>
	.workspace-intro {
		position: relative;
		min-height: calc(100vh - var(--header-height));
		overflow: hidden;
		background-color: var(--color-canvas);
		background-image: var(--gradient-ambient), var(--texture-grid);
		background-size:
			auto,
			var(--grid-size) var(--grid-size);
	}

	.workspace-intro::before {
		position: absolute;
		top: 0;
		left: 50%;
		width: min(80rem, 100%);
		height: var(--border-width);
		transform: translateX(-50%);
		background: var(--gradient-brand);
		content: '';
		opacity: 0.7;
	}

	.intro-inner {
		position: relative;
		max-width: var(--content-width);
		margin: 0 auto;
		padding: clamp(3rem, 7vw, 6.5rem) var(--space-5) var(--space-8);
	}

	.hero-grid {
		display: grid;
		grid-template-columns: minmax(0, 1.1fr) minmax(22rem, 0.9fr);
		align-items: center;
		gap: clamp(3rem, 7vw, 7rem);
	}

	.hero-copy {
		position: relative;
	}

	.eyebrow,
	.panel-label,
	.panel-kicker {
		margin: 0;
		color: var(--color-primary);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		font-weight: 700;
		letter-spacing: var(--letter-spacing-label);
	}

	.eyebrow {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.eyebrow span {
		width: var(--space-5);
		height: var(--border-width);
		background: var(--color-primary);
		box-shadow: 0 0 var(--space-3) var(--color-primary-glow);
	}

	h1 {
		max-width: 14ch;
		margin: var(--space-4) 0;
		font-size: clamp(2.5rem, 6vw, 5.25rem);
		font-weight: 640;
		line-height: 0.98;
		letter-spacing: -0.05em;
	}

	h1 span {
		background: var(--gradient-brand);
		background-clip: text;
		color: transparent;
	}

	.lede {
		max-width: 40rem;
		margin: 0;
		color: var(--color-ink-muted);
		font-size: var(--font-size-lg);
	}

	.principles {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		max-width: 38rem;
		margin: var(--space-7) 0 0;
		border-top: var(--border-width) solid var(--color-border);
		border-bottom: var(--border-width) solid var(--color-border);
	}

	.principles div {
		padding: var(--space-3) var(--space-4);
		border-left: var(--border-width) solid var(--color-border);
	}

	.principles div:first-child {
		padding-left: 0;
		border-left: 0;
	}

	.principles dt,
	.readout dt,
	.foundation-grid span {
		color: var(--color-ink-subtle);
		font-family: var(--font-mono);
		font-size: 0.625rem;
		letter-spacing: var(--letter-spacing-label);
	}

	.principles dd,
	.readout dd {
		margin: var(--space-1) 0 0;
		font-size: var(--font-size-sm);
	}

	.signal-panel {
		position: relative;
		min-width: 0;
		overflow: hidden;
		border: var(--border-width) solid var(--color-border-strong);
		border-radius: var(--radius-lg);
		background: var(--gradient-surface), var(--color-surface-glass);
		box-shadow: var(--shadow-panel), var(--shadow-glow);
	}

	.signal-panel::before,
	.signal-panel::after {
		position: absolute;
		width: var(--space-5);
		height: var(--space-5);
		content: '';
	}

	.signal-panel::before {
		top: var(--space-2);
		left: var(--space-2);
		border-top: var(--border-width) solid var(--color-primary);
		border-left: var(--border-width) solid var(--color-primary);
	}

	.signal-panel::after {
		right: var(--space-2);
		bottom: var(--space-2);
		border-right: var(--border-width) solid var(--color-primary);
		border-bottom: var(--border-width) solid var(--color-primary);
	}

	.panel-bar {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-3);
		padding: var(--space-4) var(--space-5);
		border-bottom: var(--border-width) solid var(--color-border);
	}

	.panel-bar h2 {
		margin: var(--space-1) 0 0;
		font-size: var(--font-size-base);
	}

	.system-state,
	.status-chip {
		display: inline-flex;
		flex: none;
		align-items: center;
		gap: var(--space-2);
		color: var(--color-observed);
		font-family: var(--font-mono);
		font-size: 0.625rem;
		font-weight: 700;
		letter-spacing: var(--letter-spacing-label);
	}

	.system-state span,
	.status-chip span {
		width: 0.375rem;
		height: 0.375rem;
		border-radius: 50%;
		background: currentColor;
		box-shadow: 0 0 var(--space-2) currentColor;
	}

	.orbital-map {
		position: relative;
		display: grid;
		height: 22rem;
		place-items: center;
		overflow: hidden;
	}

	.axis {
		position: absolute;
		background: var(--color-border);
		opacity: 0.6;
	}

	.axis-horizontal {
		width: 82%;
		height: var(--border-width);
	}

	.axis-vertical {
		width: var(--border-width);
		height: 82%;
	}

	.orbit {
		position: absolute;
		border: var(--border-width) solid var(--color-border-strong);
		border-radius: 50%;
	}

	.orbit-outer {
		width: 18rem;
		height: 18rem;
	}

	.orbit-middle {
		width: 12rem;
		height: 12rem;
		border-style: dashed;
	}

	.orbit-inner {
		width: 5.5rem;
		height: 5.5rem;
		border-color: var(--color-primary);
		box-shadow: inset 0 0 2rem var(--color-primary-faint);
	}

	.sweep {
		position: absolute;
		width: 17rem;
		height: 17rem;
		border-top: var(--border-width) solid var(--color-secondary);
		border-radius: 50%;
		animation: scan var(--motion-ambient) linear infinite;
	}

	.core {
		display: grid;
		width: var(--space-6);
		height: var(--space-6);
		place-items: center;
		border: var(--border-width) solid var(--color-primary);
		border-radius: 50%;
		background: var(--color-primary-faint);
		box-shadow: 0 0 2rem var(--color-primary-glow);
	}

	.core span {
		width: var(--space-2);
		height: var(--space-2);
		border-radius: 50%;
		background: var(--color-primary);
	}

	.node {
		position: absolute;
		width: var(--space-3);
		height: var(--space-3);
		border: var(--border-width) solid var(--color-secondary);
		border-radius: 50%;
		background: var(--color-surface);
		box-shadow: 0 0 var(--space-4) var(--color-secondary-faint);
	}

	.node-one {
		transform: translate(6rem, -5.5rem);
	}

	.node-two {
		transform: translate(-7rem, 3rem);
		border-color: var(--color-observed);
	}

	.node-three {
		transform: translate(4.5rem, 6.5rem);
		border-color: var(--color-highlight);
	}

	.map-label {
		position: absolute;
		padding: var(--space-1) var(--space-2);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-sm);
		background: var(--color-surface-glass);
		color: var(--color-ink-muted);
		font-family: var(--font-mono);
		font-size: 0.5625rem;
		letter-spacing: var(--letter-spacing-label);
	}

	.label-one {
		top: 17%;
		right: 9%;
	}

	.label-two {
		bottom: 22%;
		left: 7%;
	}

	.label-three {
		right: 12%;
		bottom: 9%;
	}

	.readout {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		margin: 0;
		border-top: var(--border-width) solid var(--color-border);
	}

	.readout div {
		padding: var(--space-3) var(--space-4);
		border-left: var(--border-width) solid var(--color-border);
	}

	.readout div:first-child {
		border-left: 0;
	}

	.foundation-panel {
		display: grid;
		grid-template-columns: minmax(16rem, 1.1fr) minmax(24rem, 1.5fr);
		gap: var(--space-6) var(--space-7);
		margin-top: var(--space-8);
		padding: var(--space-6);
		border: var(--border-width) solid var(--color-border-strong);
		border-radius: var(--radius-lg);
		background: var(--gradient-surface), var(--color-surface);
		box-shadow: var(--shadow-panel);
	}

	.foundation-copy h2 {
		margin: var(--space-2) 0;
		font-size: clamp(1.35rem, 3vw, 2rem);
	}

	.foundation-copy > p:last-child {
		margin: 0;
		color: var(--color-ink-muted);
	}

	.foundation-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		align-self: center;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.foundation-grid li {
		display: grid;
		gap: var(--space-2);
		padding: var(--space-4);
		border-left: var(--border-width) solid var(--color-border);
	}

	.foundation-grid strong {
		font-size: var(--font-size-sm);
	}

	.integrity-note {
		display: flex;
		grid-column: 1 / -1;
		align-items: center;
		gap: var(--space-4);
		padding-top: var(--space-4);
		border-top: var(--border-width) solid var(--color-border);
	}

	.integrity-note p {
		margin: 0;
		color: var(--color-ink-muted);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: 0.03em;
	}

	.integrity-note strong:first-child {
		color: var(--color-observed);
	}

	.integrity-note strong:last-child {
		color: var(--color-assessed);
	}

	.status-chip {
		padding: var(--space-1) var(--space-2);
		border: var(--border-width) solid var(--color-observed);
		border-radius: var(--radius-sm);
	}

	@keyframes scan {
		to {
			transform: rotate(360deg);
		}
	}

	@media (max-width: 62rem) {
		.hero-grid {
			grid-template-columns: 1fr;
		}

		.hero-copy {
			max-width: 46rem;
		}

		.signal-panel {
			max-width: 40rem;
		}

		.foundation-panel {
			grid-template-columns: 1fr;
		}
	}

	@media (max-width: 40rem) {
		.intro-inner {
			padding-top: var(--space-7);
		}

		h1 {
			font-size: clamp(2.5rem, 13vw, 4rem);
		}

		.principles,
		.foundation-grid {
			grid-template-columns: 1fr;
		}

		.principles div,
		.principles div:first-child,
		.foundation-grid li {
			padding: var(--space-3) 0;
			border-top: var(--border-width) solid var(--color-border);
			border-left: 0;
		}

		.principles div:first-child {
			border-top: 0;
		}

		.panel-bar {
			align-items: flex-start;
			padding: var(--space-4);
		}

		.system-state {
			font-size: 0;
		}

		.orbital-map {
			height: 18rem;
			transform: scale(0.86);
		}

		.readout {
			grid-template-columns: 1fr;
		}

		.readout div {
			display: flex;
			align-items: center;
			justify-content: space-between;
			padding: var(--space-2) var(--space-4);
			border-top: var(--border-width) solid var(--color-border);
			border-left: 0;
		}

		.readout div:first-child {
			border-top: 0;
		}

		.readout dd {
			margin: 0;
		}

		.foundation-panel {
			padding: var(--space-5);
		}

		.foundation-grid li:first-child {
			border-top: 0;
		}

		.integrity-note {
			align-items: flex-start;
			flex-direction: column;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.sweep {
			animation: none;
		}
	}
</style>
