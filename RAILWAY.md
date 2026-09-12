# 🚆 Hosting HarmoniX on Railway

This guide walks you through deploying **HarmoniX** (Discord Bot + Lavalink v4 audio server) to [Railway](https://railway.com) in **under 5 minutes**.

Thanks to the unified multi-stage container, **both Lavalink v4 (Java 21) and the Discord Bot (Python 3.11) run together in a single Railway service**, communicating over `localhost` with zero networking latency and minimal resource consumption.

---

## 📋 Prerequisites

1. Your repository pushed to GitHub: `https://github.com/PR4NKS/HarmoniX`
2. An account on [Railway](https://railway.com)
3. Your **Discord Bot Token** from the [Discord Developer Portal](https://discord.com/developers/applications)

---

## 🚀 Step-by-Step Deployment

### Step 1: Create a New Project on Railway
1. Log in to [Railway](https://railway.com).
2. Click **+ New Project** (or **Dashboard** → **Create Project**).
3. Select **Deploy from GitHub repo**.
4. Choose `PR4NKS/HarmoniX` (or your repository name).
5. Click **Deploy Now**.

---

### Step 2: Configure Environment Variables
1. Click on the newly created **HarmoniX** service box in your Railway canvas.
2. Navigate to the **Variables** tab.
3. Click **+ New Variable** and add:

| Variable Name | Required | Default / Example Value | Description |
| :--- | :---: | :--- | :--- |
| `DISCORD_TOKEN` | **YES** | `MTE...your_discord_token` | Token from Discord Developer Portal |
| `DEFAULT_SEARCH_SOURCE` | No | `scsearch` | Default search platform (`scsearch` recommended for instant playback) |
| `SPOTIFY_CLIENT_ID` | No | `your_spotify_client_id` | Enables Spotify tracks, albums & playlists resolution |
| `SPOTIFY_CLIENT_SECRET` | No | `your_spotify_client_secret` | Spotify Application Secret |
| `GENIUS_API_TOKEN` | No | `your_genius_token` | Enables rich lyrics search via Genius |
| `DATABASE_PATH` | No | `data/bot_database.sqlite3` | SQLite database file location |
| `LOG_FILE` | No | `logs/bot.log` | Path for runtime logs |

> [!NOTE]
> `LAVALINK_URI` and `LAVALINK_PASSWORD` are pre-configured to `http://127.0.0.1:2333` and `youshallnotpass` automatically inside the container. You do **not** need to set them unless connecting to an external node!

---

### Step 3: (Recommended) Add a Persistent Volume
To ensure your playlists, server DJ roles, and favorites persist across bot redeployments and updates:
1. In the service dashboard, switch to the **Settings** or **Volumes** tab.
2. Under **Volumes**, click **+ Add Volume**.
3. Set the **Mount Path** to:
   ```text
   /app/data
   ```
4. Click **Add Volume**.

---

### Step 4: Verify Deployment Logs
1. Click the **Deployments** tab.
2. Select the active deployment and view the build and runtime logs.
3. You will see:
   ```text
   ==========================================================
       HarmoniX Discord Music Bot - Railway Launchpad       
   ==========================================================
   [1/2] Starting Lavalink v4 Audio Server...
   Waiting for Lavalink to be ready on port 2333...
   [SUCCESS] Lavalink v4 is ready! (Version: 4.x.x)
   [2/2] Starting HarmoniX Discord Bot...
   [HarmoniX] Connected to Discord Gateway as HarmoniX#0000
   [HarmoniX] Connected to Lavalink node: Default-Node
   [HarmoniX] Application commands synced successfully across guilds.
   ```

---

## ⚙️ Discord Bot Privileged Intents Check

If the bot connects but does not respond to commands:
1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. Select your Application → Click **Bot** on the left sidebar.
3. Under **Privileged Gateway Intents**, enable:
   - ✅ **Server Members Intent**
   - ✅ **Message Content Intent**
4. Save Changes.

---

## ❓ FAQ & Troubleshooting

### Do I need to generate a public domain on Railway?
**No.** Discord bots communicate via an outbound WebSocket gateway to Discord's servers, so no public incoming port is required. If you choose to click "Generate Domain", the bot provides an automatic HTTP `200 OK` health status endpoint on the assigned `$PORT`.

### Can I reduce memory usage?
Yes. If you are on a tight memory limit, add the environment variable:
```env
JAVA_OPTS=-Xmx384M -XX:+UseG1GC
```
This restricts Lavalink's Java heap to 384MB.
