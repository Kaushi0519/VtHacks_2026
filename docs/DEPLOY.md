# Deploy: localhost → lattice.luxe

Two hosts. Frontend on **Vercel**, backend on **Railway** (Vercel can't run our backend — it needs a
persistent process for SSE + in-memory state + the sweeper). The `Dockerfile` at the repo root makes
the backend build reproducible and bundles `simulator/fixtures/world.yaml` (which the backend reads).

**Easiest path = 2 services** (frontend + backend); drive the demo from your laptop CLI.
**Optional 3rd service** (the simulator) if you want the on-screen demo-bar buttons to work live.

---

## 1. Backend → Railway
1. railway.app → **New Project → Deploy from GitHub repo** → pick this repo.
2. Settings → **Root Directory = `/`** (leave at repo root — the Dockerfile needs it). Railway
   auto-detects the `Dockerfile`.
3. **Variables** (Railway → Variables):
   ```
   GEMINI_MODE=real
   GEMINI_API_KEY=<shared key>
   GEMINI_MODEL=gemini-flash-lite-latest
   ANS_MODE=mock
   ALLOW_BACKFILL=true
   CORS_ORIGINS=["https://lattice.luxe","https://www.lattice.luxe"]
   ```
   `CORS_ORIGINS` must be a JSON array exactly like that. (Add your Vercel preview URL too if needed.)
4. Deploy → Settings → **Generate Domain** to get a public HTTPS URL (e.g. `xxx.up.railway.app`).
   Check `https://<that>/api/agents` returns JSON.

## 2. Frontend → Vercel
1. vercel.com → **Add New → Project** → import this repo → **Root Directory = `frontend`**.
2. **Environment Variables:**
   ```
   NEXT_PUBLIC_API_URL=https://api.lattice.luxe        (or the railway.app URL for now)
   NEXT_PUBLIC_SIM_URL=https://sim.lattice.luxe        (or the backend URL if you skip the sim)
   ```
3. Deploy.

## 3. Domain: lattice.luxe (GoDaddy DNS)
- **Vercel** → project → Domains → add `lattice.luxe`. It shows the exact records.
- **GoDaddy** → DNS for lattice.luxe → add the apex A record (`@ → 76.76.21.21`) and the `www`
  CNAME Vercel gives you.
- For `api.lattice.luxe`: **Railway** → your service → Settings → Custom Domain → add
  `api.lattice.luxe`; it gives a CNAME target → add that CNAME in GoDaddy. (Same for `sim` if used.)
- DNS propagation takes minutes–hours. **Do this early.** Until it resolves, use the raw
  `railway.app` / `vercel.app` URLs in the env vars above.

## 4. (Optional) Simulator → Railway
Only needed for the live demo-bar buttons. Railway → same project → **New Service → same repo**,
Root Directory = `simulator`, Start command `uvicorn sentinel_sim.server:app --host 0.0.0.0 --port
$PORT`, Variable `SENTINEL_URL=https://api.lattice.luxe`. Then set `NEXT_PUBLIC_SIM_URL` (Vercel) to
this service's domain.

## Driving the demo (deployed)
Run it from your laptop against the live backend — it plays out on lattice.luxe for everyone:
```bash
cd simulator && SENTINEL_URL=https://api.lattice.luxe uv run python -m sentinel_sim tenant --pace 1.3
# seed the accountability page:
SENTINEL_URL=https://api.lattice.luxe uv run python -m sentinel_sim run history_backfill
```

## Making changes while deployed
Both hosts **auto-deploy on every push to `main`** (~1–2 min for Vercel). Teammates keep working
normally; Vercel also builds preview URLs per branch. Caveats: a broken push breaks the live site
(test locally first), and **freeze `main` near demo time**.

## Notes / gotchas
- **HTTPS everywhere:** a `http://` backend URL is blocked by the `https://` frontend. Railway URLs
  are HTTPS by default — good.
- **SSE:** verify the mesh updates live after deploy (Railway supports SSE; just confirm).
- **Security:** admin routes (reset/quarantine/grant) are open by default. For a public URL you can
  set `OPERATOR_TOKEN`, but that disables the frontend's admin buttons (a browser can't hold the
  token) — for a short demo window, leaving it open is the common call.
- **Keep localhost as the fallback** for the real demo. Deploy is a bonus, not the only path.
