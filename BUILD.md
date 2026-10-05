# 🏗️ Architecture & Build System

This repository serves as both the GitHub profile README for [`@pankajt25`](https://github.com/pankajt25) and a self-contained, automated asset generation system.

Instead of relying on external third-party dynamic badge services, all dynamic components (profile metrics, language charts, commit heatmaps, trophies, snake animations, and daily quotes) are generated via **first-party GitHub Actions pipelines** and baked into static SVGs committed directly to the repository.

---

## 💡 Core Design Philosophy

### The Problem with Third-Party Renderers
Traditional GitHub profile badges (e.g., dynamic Heroku/Vercel dynos, `komarev/github-profile-views-counter`, or `github-profile-trophy.vercel.app`) frequently encounter:
- Cold start delays and slow README load times.
- Upstream API rate limits and unexpected service outages.
- Broken image placeholders rendered on profile visits when external hosts go down.

### The Self-Hosted Solution
1. **Decoupled Computation**: Real data is ingested from official GitHub REST and GraphQL APIs in the background via scheduled GitHub Actions workflows.
2. **Static Asset Baking**: Python scripts generate standalone SVGs styled with custom dark-mode design tokens matching GitHub's interface.
3. **Commit to Repository**: Generated SVGs are committed directly back into `main`.
4. **100% Availability & Zero Lag**: When a user visits the profile, GitHub's fast raw CDN serves pre-rendered static SVGs. The profile never breaks or displays placeholder errors.

---

## 🏛️ System Architecture

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'darkMode': true, 'background': '#0d1117', 'primaryColor': '#161b22', 'primaryBorderColor': '#2d3341', 'primaryTextColor': '#c9d1d9', 'lineColor': '#4a90e2' }}}%%
flowchart TD
    subgraph Triggers ["Execution Triggers"]
        T_Cron["Cron Schedules (Daily)"]
        T_Push["Push to main"]
        T_Manual["workflow_dispatch"]
    end

    subgraph Workflows ["GitHub Actions Workflows"]
        W_Cards["update-cards.yml"]
        W_Snake["snake.yml"]
        W_Quote["update-quote.yml"]
    end

    subgraph Processors ["Scripts & Services"]
        S_Cards[".github/scripts/generate_cards.py"]
        S_Quote[".github/scripts/generate_quote.py"]
        A_Snake["Platane/snk@v3 Action"]
        CF_Worker["Cloudflare Worker (toxicmtest.workers.dev)"]
    end

    subgraph Sources ["Upstream Data"]
        API_GH["GitHub REST & GraphQL API"]
        API_Quote["ZenQuotes / Quotable API"]
        KV_Store["Cloudflare Workers KV"]
    end

    subgraph Artifacts ["Committed Static Assets"]
        SVG_Stats["stats-card.svg"]
        SVG_Langs["languages-card.svg"]
        SVG_Hours["commits-by-hour-card.svg"]
        SVG_Contrib["contributions-card.svg"]
        SVG_Trophies["trophies.svg"]
        SVG_Snake["dist/github-contribution-grid-snake.svg"]
        MD_Readme["ReadMe.md (Thought of the Day)"]
    end

    subgraph Client ["Client Profile"]
        Profile["GitHub Profile View (ReadMe.md)"]
    end

    T_Cron --> W_Cards & W_Snake & W_Quote
    T_Push --> W_Cards & W_Snake
    T_Manual --> W_Cards & W_Snake & W_Quote

    W_Cards --> S_Cards
    W_Snake --> A_Snake
    W_Quote --> S_Quote

    API_GH --> S_Cards
    API_GH --> A_Snake
    API_Quote --> S_Quote
    KV_Store <--> CF_Worker

    S_Cards -->|Commit [skip ci]| SVG_Stats & SVG_Langs & SVG_Hours & SVG_Contrib & SVG_Trophies
    A_Snake -->|Commit [skip ci]| SVG_Snake
    S_Quote -->|Commit [skip ci]| MD_Readme

    Profile --> SVG_Stats & SVG_Langs & SVG_Hours & SVG_Contrib & SVG_Trophies & SVG_Snake & MD_Readme
    Profile --> CF_Worker
```

---

## ⚙️ Workflows & Script Responsibilities

### 1. Profile Cards & Trophies Pipeline
- **Workflow**: [`.github/workflows/update-cards.yml`](.github/workflows/update-cards.yml)
- **Script**: [`.github/scripts/generate_cards.py`](.github/scripts/generate_cards.py)
- **Triggers**: Scheduled daily at `00:15 UTC` (~5:45 AM IST), push to `main`, and manual dispatch.
- **Responsibilities**:
  - **Repository Analysis**: Calls `/users/{username}/repos` to calculate total stars and top 5 languages across all owned repositories.
  - **Contribution Ingestion**: Executes GraphQL queries against `contributionsCollection` to extract total commits, PRs, issues, contributed repositories, and the past year's calendar weeks.
  - **Hourly Activity Histogram**: Samples recent commit timestamps across top repositories and adjusts them to the configured time zone (`UTC_OFFSET_HOURS = 5.5` for IST) to generate an activity distribution chart.
  - **Self-Hosted Trophies**: Evaluates user stats against custom tier thresholds (`SSS` through `C`) to generate self-rendered trophy cards without relying on external trophy APIs.
  - **Outputs**: `stats-card.svg`, `languages-card.svg`, `commits-by-hour-card.svg`, `contributions-card.svg`, `trophies.svg`.

### 2. Contribution Snake Animation
- **Workflow**: [`.github/workflows/snake.yml`](.github/workflows/snake.yml)
- **Action**: `Platane/snk@v3`
- **Triggers**: Scheduled daily at `00:20 UTC`, push to `main`, and manual dispatch.
- **Responsibilities**:
  - Reads the profile's contribution matrix.
  - Simulates a game of snake traversing the contribution squares to eat commits.
  - **Outputs**: `dist/github-contribution-grid-snake.svg` and `dist/github-contribution-grid-snake-dark.svg`.

### 3. Daily Thought & Quote Updater
- **Workflow**: [`.github/workflows/update-quote.yml`](.github/workflows/update-quote.yml)
- **Script**: [`.github/scripts/generate_quote.py`](.github/scripts/generate_quote.py)
- **Triggers**: Scheduled daily at `03:00 UTC` (~8:30 AM IST) and manual dispatch.
- **Responsibilities**:
  - Fetches a quote from ZenQuotes (`zenquotes.io/api/random`).
  - Automatically falls back to Quotable (`api.quotable.io/random`) and a static quote safety fallback in the event of upstream network failures.
  - Injects the quote cleanly between the `<!-- QUOTE:START -->` and `<!-- QUOTE:END -->` markers in [`ReadMe.md`](ReadMe.md).

### 4. Edge Profile View Counter
- **Endpoint**: `https://profile-views.toxicmtest.workers.dev`
- **Infrastructure**: Standalone Cloudflare Worker backed by Cloudflare Workers KV.
- **Responsibilities**:
  - Increments and persists view counts atomically at edge locations on each SVG request.
  - Eliminates reliance on external analytics services while guaranteeing sub-millisecond responses.

---

## 🎨 Design System & Conventions

All generated SVG cards and diagrams adhere to a consistent dark-theme design palette that blends natively with GitHub's dark theme:

| Element | Color Hex | Description |
| :--- | :--- | :--- |
| **Card Background** | `#0d1117` | GitHub primary dark canvas |
| **Card Border** | `#2d3341` | Subtle divider border with 12px corner radius |
| **Headers & Accents** | `#4a90e2` | Crisp sky blue accent |
| **Primary Text** | `#c9d1d9` | High-contrast readable body text |
| **Secondary Text** | `#8b949e` | Subdued labels and metadata |
| **Trophy S-Tiers** | `#f1c40f` | Gold badge border and tier text (`SSS`, `SS`, `S`) |
| **Trophy A-Tiers** | `#e67e22` | Bronze/Orange badge border and tier text (`AAA`, `AA`, `A`) |
| **Trophy B/C-Tiers** | `#3498db` | Blue badge border and tier text (`B`, `C`) |

---

## 🔄 Git & Automation Rules

- **Commit Suffix `[skip ci]`**: Every automated commit authored by `github-actions[bot]` concludes with `[skip ci]` to prevent cascading, infinite workflow loops.
- **Merge Strategy**: This repository uses `git pull --no-rebase` when pulling down updates to smoothly integrate frequent bot-generated commits.
- **File Integrity**: Root `*.svg` files and the content between `<!-- QUOTE:START -->` / `<!-- QUOTE:END -->` in `ReadMe.md` are exclusively managed by automated scripts and must not be manually edited.
