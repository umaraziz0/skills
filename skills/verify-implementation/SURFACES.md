# Surfaces

How to exercise each kind of surface. Read only the sections your scenario
matrix uses.

## Browser UI

- Use the browser tool the host provides. Close every tab you open.
- Check at least one mobile and one desktop viewport. At each one, confirm the
  page has no horizontal scroll.
- Look at the page. At each viewport, take a screenshot and view the image
  itself, beside an existing sibling page or component. Measurements answer
  only the questions you thought to ask; the look catches spacing, alignment,
  and clipping you did not predict.
- View or copy each screenshot to the scratchpad before the next run: some
  runners empty their screenshot folder when a run starts (Pest's browser
  plugin does).
- Where the change overrides a library default (a class, a margin, a token),
  measure what the default gave and confirm the override still gives it.
- Target elements by locator or accessibility ref. Before you click by
  coordinates, confirm the viewport width matches the screenshot width, because
  scaled screenshots shift clicks.
- If an input drops keystrokes or a click has no effect, suspect delayed
  hydration: interact with the page once (a scroll or click), then retry.
- Read the console for warnings your change caused, such as router misses or
  hydration mismatches. Check the network calls your change makes: URL, status,
  payload.
- Third-party widgets (captcha, payment iframes) often reject automation. Reach
  the branches behind them with a `stub` or `forced` method, and label it.
- If the app supports dark mode, check it on surfaces where text colour
  matters.
- When snapshots time out or the page is long, measure with script evaluation:
  bounding boxes, text content, `scrollWidth`.

Evidence: a viewed screenshot per viewport, visible text, element state,
measurements, network status.

## HTTP API

- Call the endpoint directly with `curl` or `httpie`, sending
  `Accept: application/json`.
- Cover:
  - a valid request;
  - each validation failure;
  - missing or invalid auth;
  - not found and conflict states;
  - rate limits, when the endpoint has them.
- Assert the status, the body shape, and side effects: a DB row, a queued job,
  a mail log entry.
- When a browser calls the endpoint from another origin, send a CORS preflight
  (`OPTIONS` with `Origin` and `Access-Control-Request-Method`) and check the
  allow headers.

Evidence: status line and the relevant body fields.

## CLI, script, or job

- Run it with representative arguments, then with invalid ones.
- Check the exit code, stdout and stderr, and the files or rows it changes.
- For queued jobs, dispatch one, then watch the worker output or the logs until
  it finishes or fails.

Evidence: exit code and output excerpts.

## Data and migrations

- On a local database, migrate up, inspect the schema, migrate down, then
  migrate up again.
- Check that the defaults, indexes, and constraints match the spec.

Evidence: schema dumps or describe-table output.

## Email and notifications

- Capture outgoing mail with the local mail catcher or log driver, such as
  Mailpit, Herd mail, or the `log` mailer.
- Trigger the action, then check the recipient, subject, rendered body, and
  every link.

Evidence: the captured message headers and the resolved links.

## Library or pure logic

- Run the existing tests that cover it.
- If none exist, call it from a REPL or from a throwaway script in the
  scratchpad, covering normal and boundary inputs. Delete the script
  afterwards.

Evidence: inputs paired with outputs.
