# Portal browser acceptance recipes

These CLI recipes exercise a real browser through Playwright CLI; they are not
Playwright Test specifications. Install the pinned CSS development dependencies,
rebuild CSS, and use the workspace SSD Python environment before running them.

```sh
npm ci --ignore-scripts --include=dev
npm run build:css
uv run python -m scripts.qa.build_portal_fixture --output <temporary-portal-directory>
uv run python -m scripts.qa.serve_portal --root <temporary-portal-directory> --port 8893
```

The fixture cycles the current canonical metadata under 5,000 unique synthetic IDs.
Each node references its next 50 peers; all other nodes also reference the first
node. This produces 254,949 directed edges and 4,999 citations of the hub. None of
these synthetic records or edges are canonical observations. The output records
source hashes, asset hashes, fixture counts and build measurements. The generator
refuses output locations inside canonical `data` or deployed `docs` directories.

Open a dedicated browser session at the project base path, then run the recipes:

```sh
npx --package @playwright/cli playwright-cli -s=portal-qa open http://127.0.0.1:8893/awesome-gaussian-splatting/ --browser msedge
npx --package @playwright/cli playwright-cli -s=portal-qa --raw run-code --filename scripts/qa/portal_cold_loads.js
npx --package @playwright/cli playwright-cli -s=portal-qa --raw run-code --filename scripts/qa/portal_controls.js
npx --package @playwright/cli playwright-cli -s=portal-qa --raw run-code --filename scripts/qa/relationship_pagination.js
npx --package @playwright/cli playwright-cli -s=portal-qa --raw run-code --filename scripts/qa/inline_relationships.js
npx --package @playwright/cli playwright-cli -s=portal-qa --raw run-code --filename scripts/qa/dense_graph.js
npx --package @playwright/cli playwright-cli -s=portal-qa close
```

Inspect every returned JSON result and its pass fields; CLI transport success
alone does not prove acceptance. Save evidence in `output/playwright/`. Stop the
owned preview server after QA. The cold-load recipe verifies five distinct
navigation origins with caches disabled, 4× CPU slowdown, 10/1 Mbps and 100 ms
latency. It measures 50 mounted cards through two animation frames. Graph timing
uses 4× CPU slowdown and unthrottled loopback; only ego views have the specified
two-second post-resource target. Cross-origin transfer sizes may be unavailable
without Timing-Allow-Origin. Five samples support a median and slowest result,
not a robust p95 claim.
