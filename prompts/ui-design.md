Build a visually stunning, highly interactive web UI for a project called:

"Viral Script Debugging Engine"

This is NOT a dashboard.
This is a **live AI storytelling interface** that shows how a multi-agent RL system learns to improve content.

The UI must feel like a **Meta internal AI tool**:

* clean, light theme
* premium, minimal, fast
* subtle blue accents (#1877F2 style)
* soft shadows, rounded 2xl cards
* extremely smooth animations (Framer Motion)

---

# 🧠 CORE IDEA

The UI must communicate ONE thing clearly:

👉 "This AI is learning how to think, not just generate text."

Everything should reinforce:

* decision-making
* trade-offs
* learning over time
* comparison (before vs after, A vs B, trained vs untrained)

---

# ⚙️ TECH STACK

* Next.js (App Router)
* React
* Tailwind CSS
* Framer Motion (critical)
* Recharts
* shadcn/ui

---

# 🧩 MAIN PAGES

---

## 🏠 1. LANDING / DASHBOARD

Hero:

* Title: Viral Script Debugging Engine
* Subtitle: "Watch AI learn to optimize content like a strategist"
* Animated gradient background (very subtle)

Cards (hover animated):

* ▶ Run Episode
* ⚔ A/B Battle Mode
* 📈 Retention Intelligence
* 🧠 Creator Memory

Each card:

* scale + shadow + glow on hover
* click → navigate

---

## 🎬 2. EPISODE PLAYER (MOST IMPORTANT PAGE)

This is your MAIN demo.

Design like a **movie / story flow**, not a dashboard.

Add:
👉 "Play Episode" button (auto-animates steps)

---

### ACT 1 — RAW SCRIPT

* Large clean card with script
* Metadata chips: platform, region, niche
* Fade-in animation

---

### ACT 2 — CRITIC ATTACK

* Claims appear ONE BY ONE (timed animation)
* Color-coded:

  * red = high
  * yellow = medium
* Each claim = card

Make it feel like:
👉 system is analyzing

---

### ACT 3 — DEFENDER RESPONSE

* Highlight:
  "WHAT MUST BE PRESERVED"
* Glow effect around core_strength
* Warning icons for flagged claims

Slide-in animation from right

---

### ACT 4 — ARBITRATOR THINKING (CENTERPIECE)

THIS IS THE MOST IMPORTANT VISUAL.

Split into 2:

LEFT → Untrained model
RIGHT → Trained model

Each shows:

1. Priority assessment
2. Conflict check
3. Defender consideration

Then action

---

### KEY FEATURE:

👉 Highlight reasoning differences

Example:

* trained = structured, aware of trade-offs
* untrained = generic

Animate:

* reasoning appears line by line

---

### ACT 5 — REWRITE + IMPACT

#### 1. Script Diff

* green = added
* red = removed
* smooth transition

#### 2. Reward Bars (R1–R10 + process)

* animated fill
* hover tooltip for explanation

#### 3. BIG IMPACT METRIC

Show:

* total reward before → after
* % improvement (animated counter)

---

## 🔁 ADD: LEARNING TOGGLE (CRITICAL)

Top toggle:
👉 "Before Training" vs "After Training"

Switching should:

* update reasoning
* update rewards
* update actions

This shows:
👉 the AI improved

---

## ⚔ 3. A/B BATTLE MODE (PHASE 10)

Make this feel like a COMPETITION.

Layout:
LEFT = Trajectory A (Critic-first)
RIGHT = Trajectory B (Defender-first)

---

### Features:

* Step-by-step progression
* Reward updates live
* Highlight current leader

---

### BIG VISUAL:

👉 Center "VS" indicator

---

### At end:

* Winner card (animated)
* Delta graph
* "Lesson learned" box:

Example:
"Preserving cultural voice first led to better retention"

---

## 📈 4. RETENTION INTELLIGENCE (PHASE 12)

This must be your WOW factor.

---

### Graph:

* X: time (0–60s)
* Y: retention %

Two curves:

* before
* after

---

### Add:

1. Animated curve transition
2. Highlight drop-off points
3. Tooltip at drop:
   "Weak hook caused 30% drop"

---

### Show:

* AUC improvement (big number)
* Drop-off shift:
  "6s → 20s"

---

### CRITICAL:

👉 Connect changes to outcomes

Example:
"Hook rewrite improved early retention by +22%"

---

## 🧠 5. CREATOR MEMORY (PHASE 11)

Timeline UI:

* last 5 sessions
* cards per session
* trend graph

---

### Show:

* recurring weak points
* strengths
* improvement trend

---

### Add:

Voice stability meter (animated)

---

## 📊 6. LEARNING PROGRESSION PAGE (NEW — IMPORTANT)

This page shows:

👉 "The model is getting better over time"

---

### Graphs:

* reward over episodes
* retention improvement
* success rate

---

### Compare:

Baseline vs Trained

---

# 🎬 ANIMATIONS (VERY IMPORTANT)

Use Framer Motion for:

* sequential reveal (critic → defender → arbitrator)
* reward bar filling
* graph transitions
* hover interactions
* page transitions

Everything must feel:
👉 smooth, fast, premium

---

# 🧱 COMPONENT STRUCTURE

components/

* ScriptPanel.tsx
* CriticPanel.tsx
* DefenderPanel.tsx
* ArbitratorReasoning.tsx
* RewardBars.tsx
* RetentionChart.tsx
* ABBattle.tsx
* CreatorMemory.tsx
* LearningGraph.tsx

app/

* page.tsx
* episode/page.tsx
* ab/page.tsx
* retention/page.tsx
* memory/page.tsx
* learning/page.tsx

---

# 📦 DATA

Use mock data for now:

* sample script
* reward values
* retention curves
* agent outputs

Structure so backend can plug in later.

---

# 🎯 GOAL

This UI must:

* explain complex RL visually
* show decision-making clearly
* highlight improvement instantly
* impress judges in 30 seconds

---

# ❌ DO NOT

* build a boring analytics dashboard
* overload with text
* skip animations
* hide reasoning

---

# ✅ BUILD THIS LIKE

* an interactive story
* a thinking machine
* a product demo, not a dev tool