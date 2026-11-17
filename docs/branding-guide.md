# Branding Guide: Change the Logo, Icon and Title

You can give the dashboard your own look in three ways:

| What | Where you see it | File to add |
|---|---|---|
| **Logo** | Login page and top-left corner | `branding/logo.svg` |
| **Browser tab icon** (favicon) | The small icon on the browser tab | `branding/favicon.png` |
| **Title** | Login page heading and browser tab name | `branding/text.env` |

You do not need to change any code. Put your files in the `branding` folder, then restart.

---

## How it works

1. The dashboard comes with a default look (the HEARTS360 logo and title).
2. Each time it starts, it checks the `branding` folder.
3. If it finds your files, it uses them. If a file is missing or invalid, it uses the default.
4. Remove a file and restart, and that item goes back to the default.

---

## Step by step

### 1. Logo
- Save your logo as **`logo.svg`** (it must be an SVG file, not PNG or JPG).
- A square logo, around 370 x 370, works best.
- Put it in the `branding` folder.

### 2. Browser tab icon
- Save your icon as **`favicon.png`** (it must be a real PNG file, 32 x 32 pixels works best).
- Put it in the `branding` folder.
- Renaming a JPG to `.png` will not work.

### 3. Title
- Open (or create) **`branding/text.env`**.
- Write one line, with no spaces around the `=`:

```
LOGIN_TITLE=My Organisation Dashboard
```

Title rules:
- At least 3 characters and at most 80. Anything outside that falls back to the default.
- These characters are removed automatically: `" ' \ < > $` and the backtick.
- Put comments on their own line starting with `#`. Do not add them after the title.

### 4. Restart
Restart the dashboard so it picks up your changes:

```
docker compose restart
```

Then refresh the browser with **Ctrl + F5** (Cmd + Shift + R on Mac). The browser often remembers the old logo and icon.

---

## Folder example

```
branding/
  logo.svg        <- your logo
  favicon.png     <- your browser tab icon
  text.env        <- LOGIN_TITLE=My Organisation Dashboard
```

You can add just one, two or all three. The rest keep the default.

---

## Something not changing?

| Problem | Fix |
|---|---|
| Nothing changed | Restart the dashboard, then press Ctrl + F5. |
| Old logo or icon still showing | Clear the browser cache or open a private window. |
| Title still the default | Check there are no spaces around `=` and the title has at least 3 characters. |
| Logo still the default | Make sure the file is named exactly `logo.svg` and is a real SVG. |
| Icon still the default | Make sure the file is named exactly `favicon.png` and is a real PNG. |

To see what was applied, check the startup log line that begins with `Branding applied:`.

```
docker compose logs grafana | grep "Branding applied"
```

To go back to the default look, delete the files in `branding` and restart.
